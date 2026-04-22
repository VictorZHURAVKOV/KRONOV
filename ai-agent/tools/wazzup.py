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


async def send_message(
    channel_id: str,
    chat_id: str,
    text: str,
    chat_type: Optional[ChatType] = None,
) -> dict:
    """Отправить текстовое сообщение клиенту через Wazzup.

    Args:
        channel_id: UUID канала в Wazzup (разный для WA/TG/Viber).
        chat_id: идентификатор чата — телефон для WA/Viber, user_id для Telegram.
        text: текст сообщения.
        chat_type: тип чата, опционально (Wazzup определит сам по channelId).
    """
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
        except httpx.HTTPStatusError as e:
            log.error(
                "Wazzup send_message failed %s: %s",
                r.status_code,
                r.text[:300],
            )
            return {"ok": False, "status": r.status_code, "error": r.text}
        return {"ok": True, "result": r.json()}


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
