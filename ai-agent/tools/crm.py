"""CRM = Telegram-канал Алёны.

Агент логирует каждое значимое событие, Алёна видит прогресс в реальном
времени. Никакой внешней CRM-системы не используется.
"""
import json
import httpx
from typing import Optional

from config import (
    TELEGRAM_BOT_TOKEN,
    ALENA_TELEGRAM_CHAT_ID,
    ALENA_NAME,
    ALENA_PHONE,
)
from db import update_conversation, add_event, get_or_create_conversation


async def _tg_send(chat_id: str, text: str) -> dict:
    """Отправить текст в Telegram. Тихий фейл, если токен не настроен."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return {"ok": False, "reason": "TELEGRAM_BOT_TOKEN or chat_id not configured"}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })
        return r.json()


async def save_contact(
    session_id: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    city: Optional[str] = None,
    notes: Optional[str] = None,
    size: Optional[str] = None,
    model: Optional[str] = None,
    price_byn: Optional[float] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Сохранить/обновить контакт клиента. Возвращает текущее состояние лида."""
    await get_or_create_conversation(session_id, channel="unknown")

    update_fields = {}
    if name:
        update_fields["name"] = name
    if phone:
        update_fields["phone"] = phone
    if city:
        update_fields["city"] = city
    if notes:
        update_fields["notes"] = notes

    extra_json = None
    if size or model or price_byn is not None or extra:
        payload = {"size": size, "model": model, "price_byn": price_byn}
        if extra:
            payload.update(extra)
        extra_json = json.dumps(payload, ensure_ascii=False)
        update_fields["extra_json"] = extra_json

    await update_conversation(session_id, **update_fields)
    await add_event(session_id, "contact_saved", update_fields)

    return {
        "saved": True,
        "session_id": session_id,
        "fields_updated": list(update_fields.keys()),
    }


async def log_to_crm(
    session_id: str,
    event_type: str,
    content: str,
    silent: bool = False,
) -> dict:
    """Отметка события в Telegram-канале Алёны.

    event_type: price_quoted | model_suggested | question | kp_sent | contract_sent | etc.
    silent: если True, пишем только в БД без уведомления TG.
    """
    await add_event(session_id, event_type, {"content": content})

    if silent:
        return {"logged": True, "notified": False}

    icon = {
        "price_quoted": "💰",
        "model_suggested": "🏠",
        "kp_sent": "📄",
        "contract_sent": "📝",
        "question": "❓",
        "objection": "⚠️",
        "positive": "✅",
        "negative": "❌",
    }.get(event_type, "•")

    text = f"{icon} <b>{event_type}</b> [{session_id[:8]}]\n{content}"
    res = await _tg_send(ALENA_TELEGRAM_CHAT_ID, text)

    return {"logged": True, "notified": res.get("ok", False)}


async def handoff_to_alena(
    session_id: str,
    summary: str,
    urgency: str = "morning",
    client_name: Optional[str] = None,
    client_phone: Optional[str] = None,
    client_city: Optional[str] = None,
) -> dict:
    """Передать горячего лида Алёне в Telegram.

    urgency:
      - now: в рабочие часы в течение часа
      - morning: с утра
      - scheduled: по окну клиента (в summary)
    """
    await update_conversation(session_id, status="handed_off")
    await add_event(session_id, "handoff", {
        "summary": summary, "urgency": urgency,
    })

    urgency_label = {
        "now": "🔥 <b>СРОЧНО</b> — перезвонить в ближайший час",
        "morning": "☀️ С утра — в начале рабочего дня",
        "scheduled": "🕐 По окну клиента (см. саммари)",
    }.get(urgency, "")

    lines = [
        f"🚨 <b>НОВЫЙ ГОРЯЧИЙ ЛИД</b>",
        urgency_label,
        "",
    ]
    if client_name:
        lines.append(f"👤 <b>Клиент:</b> {client_name}")
    if client_phone:
        lines.append(f"📞 <b>Телефон:</b> {client_phone}")
    if client_city:
        lines.append(f"📍 <b>Город:</b> {client_city}")
    lines.extend([
        f"💬 <b>Session:</b> {session_id}",
        "",
        "<b>Саммари:</b>",
        summary,
        "",
        f"<i>Алёна ({ALENA_PHONE}), диалог в базе, вся история доступна.</i>",
    ])
    text = "\n".join(lines)

    res = await _tg_send(ALENA_TELEGRAM_CHAT_ID, text)

    return {
        "handed_off": True,
        "notified": res.get("ok", False),
        "urgency": urgency,
        "alena_name": ALENA_NAME,
        "alena_phone": ALENA_PHONE,
    }
