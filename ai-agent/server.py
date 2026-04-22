"""FastAPI-сервер. Принимает сообщения из виджета сайта, Telegram, WhatsApp, Viber.

Endpoints:
  POST /chat               — текстовое сообщение, SSE-стриминг ответа
  GET  /chat/session       — создать новый session_id
  POST /webhook/telegram   — Telegram webhook (если используется)
  POST /webhook/whatsapp   — WhatsApp Business (заглушка-интерфейс)
  POST /webhook/viber      — Viber Bot (заглушка-интерфейс)
  GET  /kp/<filename>      — раздача PDF-КП и договоров
  GET  /healthz            — проверка живости
"""
import json
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from config import CORS_ORIGINS, HOST, PORT, KP_DIR, STATIC_DIR
from db import init_db
from agent import run_turn


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="КРОНОВЪ AI-агент", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if "*" not in CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Раздача статики виджета (если кладём рядом) и PDF
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# === Модели запросов ===
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    channel: str = "site"
    context: Optional[str] = None  # информация из формы сайта, если есть
    external_user_id: Optional[str] = None


# === /chat — SSE streaming ===
@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    async def event_stream():
        # Сначала отдаём session_id — виджет его сохранит
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
        except Exception as e:
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


# === Telegram webhook ===
@app.post("/webhook/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    msg = data.get("message") or data.get("edited_message")
    if not msg:
        return {"ok": True}

    chat_id = str(msg["chat"]["id"])
    text = msg.get("text") or msg.get("caption") or ""
    if not text:
        return {"ok": True, "reason": "non-text"}

    session_id = f"tg-{chat_id}"
    parts = []
    async for ev in run_turn(session_id=session_id, channel="telegram", user_text=text, external_user_id=chat_id):
        if ev["type"] == "text_delta":
            parts.append(ev["text"])

    final = "".join(parts).strip()
    if final:
        # Отправляем ответ в Telegram
        from config import TELEGRAM_BOT_TOKEN
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": final, "parse_mode": "HTML", "disable_web_page_preview": True},
            )
    return {"ok": True}


# === Wazzup24 единый webhook для WhatsApp / Telegram Personal / Viber ===
# На номере +375 29 688-86-29 через Wazzup подключены 3 канала. Все входящие
# приходят сюда — мы идентифицируем канал по chat_type и chat_id, прогоняем
# через агента и отвечаем обратно через Wazzup API.
from tools.wazzup import parse_incoming_webhook, send_message as wazzup_send


@app.post("/webhook/wazzup")
async def wazzup_webhook(req: Request):
    data = await req.json()
    messages = parse_incoming_webhook(data)
    if not messages:
        return {"ok": True, "processed": 0}

    for m in messages:
        # Session ID — уникальный в пределах канала: "<тип>-<chat_id>"
        session_id = f"{m['chat_type']}-{m['chat_id']}"

        # Контекст — имя клиента если есть, чтобы Андрей сразу обратился
        initial_context = None
        if m["author_name"]:
            initial_context = f"Имя клиента в {m['chat_type']}: {m['author_name']}"

        parts = []
        async for ev in run_turn(
            session_id=session_id,
            channel=m["chat_type"],
            user_text=m["text"],
            external_user_id=m["chat_id"],
            initial_context=initial_context,
        ):
            if ev["type"] == "text_delta":
                parts.append(ev["text"])
        final = "".join(parts).strip()

        if not final:
            continue

        # Отправка обратно клиенту через Wazzup
        try:
            res = await wazzup_send(
                channel_id=m["channel_id"],
                chat_id=m["chat_id"],
                text=final,
                chat_type=m["chat_type"],
            )
            if not res.get("ok"):
                print(f"[WAZZUP SEND FAIL {m['chat_type']} → {m['chat_id']}]: {res}")
        except Exception as e:
            print(f"[WAZZUP SEND ERROR]: {e}")

    return {"ok": True, "processed": len(messages)}


# === Раздача PDF ===
@app.get("/kp/{filename}")
async def serve_kp(filename: str):
    # Безопасность: не пускаем path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(404)
    path = Path(KP_DIR) / filename
    if not path.exists() or not path.suffix.lower() == ".pdf":
        raise HTTPException(404)
    return FileResponse(path, media_type="application/pdf", filename=filename)


# === Виджет-сниппет для встраивания на сайт ===
@app.get("/widget.js")
async def widget_js():
    path = STATIC_DIR / "widget.js"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="application/javascript")


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "kronov-ai-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
