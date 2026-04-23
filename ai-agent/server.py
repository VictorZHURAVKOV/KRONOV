"""FastAPI-сервер. Принимает сообщения из виджета сайта, Telegram, WhatsApp, Viber.

Endpoints:
  POST /chat               — текстовое сообщение, SSE-стриминг ответа (rate-limited)
  POST /webhook/telegram   — Telegram webhook (если используется)
  POST /webhook/wazzup     — Wazzup24 единый webhook (WA/TG-personal/Viber), token-verified
  GET  /kp/<filename>      — раздача PDF-КП и договоров
  GET  /widget.js          — виджет для встраивания на сайт
  GET  /healthz            — проверка живости (БД, API-ключ, критичные env)
"""
import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from collections import deque
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import (
    CORS_ORIGINS, HOST, PORT, KP_DIR, STATIC_DIR,
    ANTHROPIC_API_KEY, WAZZUP_WEBHOOK_TOKEN,
    CHAT_RATE_LIMIT, CHAT_RATE_WINDOW,
    DB_PATH,
)
from db import init_db
from agent import run_turn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("server")


# ==================== Rate-limit (in-memory, sliding-window) ====================
# Простой по IP: если больше CHAT_RATE_LIMIT запросов за CHAT_RATE_WINDOW сек — 429.
# На одном инстансе — достаточно. Для multi-instance перевести на Redis.
_rate_buckets: dict[str, deque] = {}
_rate_lock = asyncio.Lock()


async def _rate_check(ip: str) -> tuple[bool, int]:
    """Вернёт (ok, retry_after_sec). ok=False если превысил лимит."""
    now = time.time()
    async with _rate_lock:
        q = _rate_buckets.setdefault(ip, deque())
        # убираем старые события
        while q and now - q[0] > CHAT_RATE_WINDOW:
            q.popleft()
        if len(q) >= CHAT_RATE_LIMIT:
            retry = int(CHAT_RATE_WINDOW - (now - q[0])) + 1
            return False, retry
        q.append(now)
        return True, 0


def _client_ip(req: Request) -> str:
    # За nginx — смотрим X-Forwarded-For (первое значение), иначе client.host
    xff = req.headers.get("x-forwarded-for") or req.headers.get("x-real-ip")
    if xff:
        return xff.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


# ==================== Lifespan ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Предупреждения о критичной конфигурации
    if not ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY не задан — /chat будет отваливаться на первом запросе")
    if not WAZZUP_WEBHOOK_TOKEN:
        log.warning("WAZZUP_WEBHOOK_TOKEN не задан — /webhook/wazzup принимает ЛЮБЫЕ запросы. "
                    "Для прода обязательно задать секрет и прописать его в кабинете Wazzup.")
    log.info("KRONOV agent started on %s:%s (rate=%d/%ds)", HOST, PORT, CHAT_RATE_LIMIT, CHAT_RATE_WINDOW)
    yield


app = FastAPI(title="КРОНОВЪ AI-агент", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if "*" not in CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ==================== Модели запросов ====================
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=4000)
    channel: str = "site"
    context: Optional[str] = Field(default=None, max_length=2000)
    external_user_id: Optional[str] = None


# ==================== /chat — SSE streaming ====================
@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    ip = _client_ip(request)
    ok, retry = await _rate_check(ip)
    if not ok:
        log.info("rate-limit hit: %s (retry after %ds)", ip, retry)
        return JSONResponse(
            {"error": "Слишком много запросов — подождите немного."},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry)},
        )

    session_id = req.session_id or str(uuid.uuid4())

    async def event_stream():
        # Первым событием — session_id, виджет его сохранит
        yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"
        try:
            async for ev in run_turn(
                session_id=session_id,
                channel=req.channel,
                user_text=req.message,
                external_user_id=req.external_user_id,
                initial_context=req.context,
            ):
                payload = json.dumps(ev, ensure_ascii=False)
                yield f"event: {ev['type']}\ndata: {payload}\n\n"
        except asyncio.CancelledError:
            # Клиент закрыл соединение — это нормально для SSE
            log.info("SSE cancelled for session %s", session_id)
            raise
        except Exception as e:
            log.exception("SSE stream crashed for session %s", session_id)
            err = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ==================== Telegram webhook ====================
@app.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(400, "bad json")

    msg = data.get("message") or data.get("edited_message")
    if not msg:
        return {"ok": True}

    chat_id = str(msg["chat"]["id"])
    text = msg.get("text") or msg.get("caption") or ""
    if not text:
        return {"ok": True, "reason": "non-text"}

    session_id = f"tg-{chat_id}"
    parts = []
    try:
        async for ev in run_turn(session_id=session_id, channel="telegram",
                                 user_text=text, external_user_id=chat_id):
            if ev["type"] == "text_delta":
                parts.append(ev["text"])
    except Exception:
        log.exception("telegram webhook: run_turn crashed for %s", session_id)

    final = "".join(parts).strip()
    if not final:
        return {"ok": True, "reason": "empty_response"}

    from config import TELEGRAM_BOT_TOKEN
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Telegram лимит 4096 — чанкуем на 3500
            for chunk in _split_text(final, 3500):
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": chunk,
                          "disable_web_page_preview": True},
                )
    except Exception:
        log.exception("telegram sendMessage failed for %s", chat_id)
    return {"ok": True}


def _split_text(text: str, limit: int) -> list[str]:
    """Безопасно разбить текст по границам абзаца/пробела."""
    if len(text) <= limit:
        return [text]
    out = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n\n", 0, limit)
        if cut < limit // 2:
            cut = rest.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        out.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        out.append(rest)
    return out


# ==================== Wazzup24: единый webhook для WA / TG-personal / Viber ====================
from tools.wazzup import parse_incoming_webhook, send_message as wazzup_send


async def _process_wazzup_payload(req: Request):
    """Общий обработчик webhook-а Wazzup (вызывается из обоих маршрутов)."""
    try:
        data = await req.json()
    except Exception:
        # Wazzup при добавлении webhook делает verify-POST с пустым телом.
        # Возвращаем 200 чтобы они приняли URL.
        log.info("[WAZZUP] verify-ping (empty/non-json body)")
        return {"ok": True}

    log.info("[WAZZUP RAW] keys=%s | messages=%d | statuses=%d",
             list(data.keys()),
             len(data.get("messages") or []),
             len(data.get("statuses") or []))

    messages = parse_incoming_webhook(data)
    if not messages:
        return {"ok": True, "processed": 0}

    for m in messages:
        log.info("[WAZZUP IN  %s ← %s] %s", m["chat_type"], m["chat_id"], m["text"][:100])
        session_id = f"{m['chat_type']}-{m['chat_id']}"

        initial_context = None
        if m["author_name"]:
            initial_context = f"Имя клиента в {m['chat_type']}: {m['author_name']}"

        parts = []
        try:
            async for ev in run_turn(
                session_id=session_id,
                channel=m["chat_type"],
                user_text=m["text"],
                external_user_id=m["chat_id"],
                initial_context=initial_context,
            ):
                if ev["type"] == "text_delta":
                    parts.append(ev["text"])
        except Exception:
            log.exception("wazzup: run_turn crashed for %s", session_id)

        final = "".join(parts).strip()
        if not final:
            log.info("[WAZZUP] empty reply for %s — skip", session_id)
            continue

        log.info("[WAZZUP OUT %s → %s] %s", m["chat_type"], m["chat_id"], final[:120])
        try:
            res = await wazzup_send(
                channel_id=m["channel_id"],
                chat_id=m["chat_id"],
                text=final,
                chat_type=m["chat_type"],
            )
            if res.get("ok"):
                sent = res.get("sent_chunks") or 1
                log.info("[WAZZUP OK] sent %d chunk(s) to %s", sent, m["chat_id"])
            else:
                log.error("[WAZZUP SEND FAIL %s → %s] status=%s err=%s",
                          m["chat_type"], m["chat_id"],
                          res.get("status"), str(res.get("error"))[:300])
        except Exception:
            log.exception("wazzup send exception")

    return {"ok": True, "processed": len(messages)}


# Старый маршрут с проверкой Authorization header (на случай ручных тестов).
@app.post("/webhook/wazzup")
async def wazzup_webhook_authed(req: Request):
    if WAZZUP_WEBHOOK_TOKEN:
        auth = req.headers.get("authorization") or req.headers.get("x-wazzup-token") or ""
        if auth.lower().startswith("bearer "):
            auth = auth[7:].strip()
        if auth != WAZZUP_WEBHOOK_TOKEN:
            log.warning("Wazzup webhook (header): invalid token from %s", _client_ip(req))
            raise HTTPException(401, "invalid webhook token")
    return await _process_wazzup_payload(req)


# Новый маршрут с токеном в URL — Wazzup легко принимает (verify-POST доходит).
@app.post("/webhook/wazzup/{token}")
async def wazzup_webhook_url_token(token: str, req: Request):
    if WAZZUP_WEBHOOK_TOKEN and token != WAZZUP_WEBHOOK_TOKEN:
        log.warning("Wazzup webhook (url): invalid token from %s", _client_ip(req))
        raise HTTPException(404)  # 404 чтобы скрыть существование маршрута
    return await _process_wazzup_payload(req)


# ==================== Раздача PDF ====================
@app.get("/kp/{filename}")
async def serve_kp(filename: str):
    # path traversal guard
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(404)
    path = Path(KP_DIR) / filename
    if not path.exists() or not path.suffix.lower() == ".pdf":
        raise HTTPException(404)
    return FileResponse(path, media_type="application/pdf", filename=filename)


# ==================== Виджет ====================
@app.get("/widget.js")
async def widget_js():
    path = STATIC_DIR / "widget.js"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


# ==================== Healthz ====================
@app.get("/healthz")
async def healthz():
    """Глубокая проверка: БД открывается, критичные env заданы."""
    import aiosqlite
    checks = {
        "anthropic_key": bool(ANTHROPIC_API_KEY),
        "wazzup_token": bool(WAZZUP_WEBHOOK_TOKEN),
    }
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("SELECT 1")
        checks["db"] = True
    except Exception as e:
        checks["db"] = False
        checks["db_error"] = str(e)

    ok = checks["db"] and checks["anthropic_key"]
    return JSONResponse(
        {"ok": ok, "service": "kronov-ai-agent", "checks": checks},
        status_code=200 if ok else 503,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
