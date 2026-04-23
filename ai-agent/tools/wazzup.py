"""Интеграция с Wazzup24 — единая прослойка для WhatsApp, Telegram Personal, Viber.

Документация API: https://wazzup24.com/help/api-en/

На нашем номере +375 29 688-86-29 подключены каналы WhatsApp, Telegram
Personal, Viber. Wazzup шлёт все входящие сообщения на единый webhook
(`/webhook/wazzup`), мы отвечаем через POST /v3/message.
"""
import logging
from typing import Optional, Literal

import httpx

from config import WAZZUP_API_KEY

log = logging.getLogger(__name__)

WAZZUP_BASE_URL = "https://api.wazzup24.com"

ChatType = Literal["whatsapp", "telegram", "tgapi", "viber", "instagram", "vk"]

# Каналы на номере +375 29 688-86-29 (получены из GET /v3/channels 2026-04-22).
# transport у Telegram Personal — "tgapi" (подтверждено API).
CHANNELS = {
    "whatsapp": "32c18412-6eca-46ed-b920-86ba2b87cd35",
    "viber": "40f4c872-5cf8-4bf3-8197-afc0e7128515",
    "telegram": "935779f0-28da-4791-ae5e-7f8f077a4102",
    "tgapi": "935779f0-28da-4791-ae5e-7f8f077a4102",  # алиас
}


def _headers() -> dict:
    if not WAZZUP_API_KEY:
        raise RuntimeError("WAZZUP_API_KEY не задан в .env")
    return {
        "Authorization": f"Bearer {WAZZUP_API_KEY}",
        "Content-Type": "application/json",
    }


# Лимиты по каналам (символы). WhatsApp ~4096, Viber ~7000, Telegram ~4096.
# Берём консервативно 3500 — оставляем зазор на расшифровку UTF-8 и форматирование.
CHUNK_LIMIT = 3500


def _split_for_messenger(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Разбить длинный ответ на чанки по границам абзаца/предложения, без обрезки слов."""
    text = text.strip()
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    rest = text
    while len(rest) > limit:
        # Ищем последний разрыв абзаца, потом предложения, потом пробел до limit
        cut = rest.rfind("\n\n", 0, limit)
        if cut < limit // 2:
            cut = rest.rfind(". ", 0, limit)
            if cut > 0:
                cut += 1  # включить точку
        if cut < limit // 2:
            cut = rest.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        chunks.append(rest)
    return chunks


async def _post_one(channel_id: str, chat_id: str, text: str, chat_type: Optional[ChatType]) -> dict:
    payload = {"channelId": channel_id, "chatId": chat_id, "text": text}
    if chat_type:
        payload["chatType"] = chat_type
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{WAZZUP_BASE_URL}/v3/message",
            json=payload,
            headers=_headers(),
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            log.error("Wazzup send failed %s: %s", r.status_code, r.text[:300])
            return {"ok": False, "status": r.status_code, "error": r.text}
        return {"ok": True, "result": r.json()}


async def send_message(
    channel_id: str,
    chat_id: str,
    text: str,
    chat_type: Optional[ChatType] = None,
) -> dict:
    """Отправить текстовое сообщение через Wazzup. Длинный текст автоматически
    разбивается на части ≤3500 символов и шлётся последовательно.

    Args:
        channel_id: UUID канала в Wazzup (разный для WA/TG/Viber).
        chat_id: идентификатор чата — телефон для WA/Viber, user_id для Telegram.
        text: текст сообщения.
        chat_type: тип чата, опционально (Wazzup определит сам по channelId).
    """
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty text"}

    chunks = _split_for_messenger(text)
    if len(chunks) == 1:
        return await _post_one(channel_id, chat_id, chunks[0], chat_type)

    log.info("Wazzup: разбиваю ответ на %d чанк(ов) для %s/%s", len(chunks), chat_type, chat_id)
    last = {"ok": True, "result": None}
    for i, chunk in enumerate(chunks, 1):
        res = await _post_one(channel_id, chat_id, chunk, chat_type)
        if not res.get("ok"):
            return {"ok": False, "status": res.get("status"), "error": res.get("error"),
                    "sent_chunks": i - 1, "total_chunks": len(chunks)}
        last = res
    return {"ok": True, "result": last.get("result"), "sent_chunks": len(chunks)}


def parse_incoming_webhook(body: dict) -> list[dict]:
    """Распарсить тело Wazzup webhook в список нормализованных сообщений.

    Wazzup шлёт разные события одним POST-запросом. Входящие сообщения —
    в ключе `messages`. Каждое сообщение имеет channelId (откуда), chatId
    (от кого), chatType (какой канал), text, authorName.

    Пропускаем:
    - isEcho=true (наши собственные сообщения)
    - сообщения без text (стикеры/аудио/фото — TODO расширить)
    """
    messages = body.get("messages") or []
    result = []
    for m in messages:
        if m.get("isEcho"):
            continue
        text = m.get("text") or ""
        if not text:
            continue
        result.append({
            "message_id": m.get("messageId"),
            "channel_id": m.get("channelId"),
            "chat_id": m.get("chatId"),
            "chat_type": m.get("chatType", "whatsapp"),  # default
            "text": text,
            "author_name": m.get("authorName") or "",
            "contact": m.get("contact") or {},
        })
    return result
