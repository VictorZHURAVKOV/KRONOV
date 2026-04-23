"""Ядро AI-менеджера КРОНОВЪ.

Один агентный цикл: Claude видит инструменты, вызывает их, получает
результаты, продолжает до текстового ответа. История сохраняется в БД.

- Реальный токен-стриминг через `client.messages.stream()` — UX печатающего.
- Prompt caching на системный промпт (5-мин TTL) — стоимость ~3× ниже.
- Retry с экспоненциальным backoff на транзиентные ошибки Anthropic API.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import AsyncIterator, Optional

import anthropic
import httpx
from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, PROMPTS_DIR
from db import add_message, get_history, get_or_create_conversation
from tools import (
    calculate_price,
    get_model_info,
    suggest_model,
    save_contact,
    log_to_crm,
    handoff_to_alena,
    generate_kp_pdf,
    generate_contract_pdf,
)

log = logging.getLogger(__name__)


# === Схема инструментов для Claude ===
TOOLS_SCHEMA = [
    {
        "name": "calculate_price",
        "description": (
            "Рассчитать точную стоимость беседки под ключ в BYN. "
            "Вызывай каждый раз перед тем как назвать клиенту цифру. "
            "Для нестандартных размеров (не из {2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6}) "
            "передавай nonstandard=true — цена автоматически увеличится на 20%."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "length": {"type": "number", "description": "Длина в метрах (2..10)"},
                "width": {"type": "number", "description": "Ширина в метрах (2..10)"},
                "roof": {"type": "string", "enum": ["none", "односкатная", "двускатная", "шатровая"], "default": "двускатная"},
                "stain": {"type": "string", "enum": ["none", "aquatex", "belinka"], "default": "aquatex"},
                "foundation": {"type": "boolean", "default": True},
                "piles": {"type": "integer", "default": 6, "description": "Количество свай (обычно 4-8)"},
                "delivery_km": {"type": "number", "default": 0, "description": "Расстояние до участка в одну сторону"},
                "install": {"type": "boolean", "default": True, "description": "Включать ли монтаж (почти всегда true)"},
                "accessories": {"type": "object", "description": "Словарь {ключ_допа: количество}. Необязательно."},
                "nonstandard": {"type": "boolean", "description": "Явно указать нестандарт (иначе определяется автоматически)"},
            },
            "required": ["length", "width"],
        },
    },
    {
        "name": "suggest_model",
        "description": "Подсказать 1-2 модели беседки из каталога под портрет клиента. Опциональный tool — можешь выбрать модель сам.",
        "input_schema": {
            "type": "object",
            "properties": {
                "for_what": {"type": "string", "description": "Зачем беседка — чаи/мангал/компания/дети/уединение"},
                "style": {"type": "string", "description": "Стиль — классика/современный/брутальный"},
                "size_hint": {"type": "string", "description": "Маленький/средний/большой участок"},
                "budget_byn": {"type": "number", "description": "Бюджет в BYN, если клиент назвал"},
            },
        },
    },
    {
        "name": "get_model_info",
        "description": "Детальная информация по конкретной модели. Передай артикул (КР-001 ... КР-011).",
        "input_schema": {
            "type": "object",
            "properties": {"article": {"type": "string"}},
            "required": ["article"],
        },
    },
    {
        "name": "save_contact",
        "description": (
            "Сохранить или обновить контакт клиента в CRM. "
            "Вызывай как только узнал имя, телефон, город, или другие значимые параметры."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "phone": {"type": "string"},
                "city": {"type": "string"},
                "notes": {"type": "string"},
                "size": {"type": "string"},
                "model": {"type": "string", "description": "Артикул КР-00X"},
                "price_byn": {"type": "number"},
                "extra": {"type": "object"},
            },
        },
    },
    {
        "name": "log_to_crm",
        "description": (
            "Отметить событие в Telegram-канале Алёны. Вызывай когда клиент: назвал цену-ок, "
            "получил КП, задал важный вопрос, возразил, проявил покупательский сигнал. "
            "event_type: price_quoted | model_suggested | kp_sent | contract_sent | question | objection | positive | negative"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {"type": "string"},
                "content": {"type": "string", "description": "Краткое описание события для Алёны"},
                "silent": {"type": "boolean", "default": False, "description": "Если true — не пушить в Telegram, только в БД"},
            },
            "required": ["event_type", "content"],
        },
    },
    {
        "name": "generate_kp_pdf",
        "description": (
            "Сформировать PDF коммерческого предложения с разбивкой цен и фирменным оформлением. "
            "Вызывай когда клиент согласился на расчёт и нужно отправить документ."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "client_city": {"type": "string"},
                "model_article": {"type": "string"},
                "model_name": {"type": "string"},
                "size": {"type": "string"},
                "breakdown": {"type": "object", "description": "Объект из calculate_price.breakdown"},
                "total_byn": {"type": "integer"},
                "roof_type": {"type": "string"},
                "stain_type": {"type": "string"},
                "delivery_km": {"type": "number"},
                "accessories": {"type": "array"},
                "nonstandard_uplift_byn": {"type": "integer", "default": 0},
                "notes": {"type": "string"},
            },
            "required": ["client_name", "model_article", "model_name", "size", "breakdown", "total_byn"],
        },
    },
    {
        "name": "generate_contract_pdf",
        "description": (
            "Сформировать PDF договора-заявки. Вызывай только когда клиент явно готов и предоставил "
            "все паспортные данные. Предоплата 50% на счёт, эквайринга нет, электронной подписи нет."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_full_name": {"type": "string"},
                "passport_series": {"type": "string"},
                "passport_number": {"type": "string"},
                "passport_issued_by": {"type": "string"},
                "passport_issued_date": {"type": "string"},
                "client_address": {"type": "string"},
                "client_phone": {"type": "string"},
                "delivery_address": {"type": "string"},
                "model_article": {"type": "string"},
                "model_name": {"type": "string"},
                "size": {"type": "string"},
                "total_byn": {"type": "integer"},
                "prepayment_byn": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": [
                "client_full_name", "passport_series", "passport_number",
                "passport_issued_by", "passport_issued_date",
                "client_address", "client_phone", "delivery_address",
                "model_article", "model_name", "size",
                "total_byn", "prepayment_byn",
            ],
        },
    },
    {
        "name": "handoff_to_alena",
        "description": (
            "Передать горячего лида Алёне в Telegram. Вызывай когда клиент готов подписать, "
            "просит звонка, назвал конкретные параметры для договора, или задал вопрос на который "
            "у тебя нет ответа. ПОСЛЕ вызова ответь клиенту что передал — и дождись."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Саммари диалога для Алёны (что обсудили, на чём остановились, что важно знать)"},
                "urgency": {"type": "string", "enum": ["now", "morning", "scheduled"], "default": "morning"},
                "client_name": {"type": "string"},
                "client_phone": {"type": "string"},
                "client_city": {"type": "string"},
            },
            "required": ["summary"],
        },
    },
]


# === Маппинг tool_name → async функция ===
async def _invoke_tool(session_id: str, name: str, args: dict) -> dict:
    try:
        if name == "calculate_price":
            return calculate_price(**args)
        if name == "suggest_model":
            return suggest_model(**args)
        if name == "get_model_info":
            return get_model_info(**args)
        if name == "save_contact":
            return await save_contact(session_id=session_id, **args)
        if name == "log_to_crm":
            return await log_to_crm(session_id=session_id, **args)
        if name == "generate_kp_pdf":
            return await generate_kp_pdf(session_id=session_id, **args)
        if name == "generate_contract_pdf":
            return await generate_contract_pdf(session_id=session_id, **args)
        if name == "handoff_to_alena":
            return await handoff_to_alena(session_id=session_id, **args)
        return {"error": f"unknown tool: {name}"}
    except TypeError as e:
        log.warning("Bad arguments for tool %s: %s", name, e)
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:
        log.exception("Tool %s failed", name)
        return {"error": f"{name} failed: {e}"}


# === Сериализация блоков ответа ===
def _serialize_block(block) -> dict:
    """Превратить TextBlock/ToolUseBlock в JSON для БД и re-подачи в API.

    Важно: не полагаемся на model_dump(), т.к. он может включать неинспектируемые
    SDK-поля (`parsed_output` при стриминге) — Anthropic API их не принимает.
    """
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name,
                "input": dict(block.input) if block.input is not None else {}}
    # thinking и прочие — оставляем как есть через model_dump
    return block.model_dump()


# === Системный промпт ===
_SYSTEM_PROMPT_CACHE: Optional[str] = None

def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        _SYSTEM_PROMPT_CACHE = (Path(PROMPTS_DIR) / "system.md").read_text(encoding="utf-8")
    return _SYSTEM_PROMPT_CACHE


# === Клиент Anthropic ===
_client: Optional[AsyncAnthropic] = None

def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY не задан. Заполните .env")
        # Сеть BY→US нестабильная и медленная (до 10 сек на TLS-handshake).
        # httpx-дефолт connect=5 сек стабильно обрывает нас → поднимаем до 30.
        # read=180 позволяет длинным стрим-ответам (до 2048 токенов) дойти до конца.
        # Свой retry берёт поверх — max_retries=0 у SDK.
        timeout = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
        _client = AsyncAnthropic(
            api_key=ANTHROPIC_API_KEY,
            max_retries=0,
            timeout=timeout,
        )
    return _client


# === Retry на транзиентные ошибки ===
# Anthropic SDK сам ретраит часть, но при сетевых дропах в стриме мы хотим
# управляемый backoff на уровне нашего цикла. Параметры подобраны под SLA
# ответа агенту в чате (≤ 8 сек до первого токена в нормальном режиме).
RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)
MAX_API_ATTEMPTS = 4


async def _stream_once(client: AsyncAnthropic, system_prompt: str, history: list[dict]):
    """Один вызов API в режиме стриминга. Возвращает финальный Message."""
    async with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        tools=TOOLS_SCHEMA,
        messages=history,
    ) as stream:
        async for event in stream:
            if event.type == "content_block_delta" and getattr(event.delta, "type", "") == "text_delta":
                yield ("delta", event.delta.text)
        final = await stream.get_final_message()
        yield ("final", final)


# === Основной цикл ===
async def run_turn(
    session_id: str,
    channel: str,
    user_text: str,
    external_user_id: Optional[str] = None,
    initial_context: Optional[str] = None,
) -> AsyncIterator[dict]:
    """Один оборот: пользователь написал — агент отвечает (может вызвать tools).

    Yields events:
      - {"type": "text_delta", "text": "..."} — токен/чанк текста для стриминга
      - {"type": "tool_use", "name": "...", "input": {...}, "id": "..."}
      - {"type": "tool_result", "name": "...", "result": {...}, "id": "..."}
      - {"type": "done", "final_text": "...", "stop_reason": "..."}
      - {"type": "error", "message": "..."}
    """
    await get_or_create_conversation(session_id, channel, external_user_id)

    user_content = user_text
    if initial_context:
        user_content = f"[СИСТЕМНЫЙ КОНТЕКСТ: {initial_context}]\n\n{user_text}"
    await add_message(session_id, "user", user_content)

    client = _get_client()
    system_prompt = _load_system_prompt()

    max_iterations = 6
    final_text_parts: list[str] = []

    for _iter in range(max_iterations):
        history = await get_history(session_id, limit=60)

        # --- Вызов API с retry на транзиентные ошибки
        resp = None
        for attempt in range(1, MAX_API_ATTEMPTS + 1):
            try:
                async for kind, payload in _stream_once(client, system_prompt, history):
                    if kind == "delta":
                        yield {"type": "text_delta", "text": payload}
                    else:  # final
                        resp = payload
                break
            except RETRYABLE as e:
                if attempt == MAX_API_ATTEMPTS:
                    log.error("Anthropic API exhausted retries: %s", e)
                    yield {"type": "error", "message": f"Claude API недоступен: {e}"}
                    return
                # экспоненциальный backoff с jitter: 0.5, 1, 2, 4 + 0..0.5
                delay = 0.5 * (2 ** (attempt - 1)) + random.random() * 0.5
                log.warning("Anthropic API transient error (attempt %d): %s — retry in %.1fs",
                            attempt, e, delay)
                await asyncio.sleep(delay)
            except anthropic.BadRequestError as e:
                log.error("Anthropic API bad request: %s", e)
                yield {"type": "error", "message": "Внутренняя ошибка диалога — Алёна перезвонит."}
                return
            except Exception as e:
                log.exception("Unexpected error from Anthropic API")
                yield {"type": "error", "message": f"Сбой соединения: {e}"}
                return

        if resp is None:
            return  # уже yield'ули error выше

        # --- Сериализуем блоки для БД так, чтобы их можно было подать обратно в API.
        # При стриминге SDK добавляет в TextBlock поле `parsed_output`, которое
        # Anthropic API не принимает обратно ("Extra inputs are not permitted").
        # Оставляем только канонические поля.
        assistant_blocks = [_serialize_block(b) for b in resp.content]
        await add_message(session_id, "assistant", assistant_blocks)

        # --- Разбираем блоки
        tool_uses = []
        text_buf = []
        for block in resp.content:
            if block.type == "text":
                text_buf.append(block.text)
                # text_delta уже отдан выше — здесь не дублируем
            elif block.type == "tool_use":
                tool_uses.append(block)
                yield {"type": "tool_use", "name": block.name, "input": dict(block.input), "id": block.id}

        if text_buf:
            final_text_parts.append("".join(text_buf))

        # --- Если есть tool-use — выполняем и продолжаем
        if resp.stop_reason == "tool_use" and tool_uses:
            tool_results = []
            for tu in tool_uses:
                result = await _invoke_tool(session_id, tu.name, dict(tu.input))
                yield {"type": "tool_result", "name": tu.name, "result": result, "id": tu.id}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            await add_message(session_id, "tool", tool_results)
            continue

        # --- end_turn (или другое) — завершаем
        yield {
            "type": "done",
            "final_text": "".join(final_text_parts),
            "stop_reason": resp.stop_reason,
        }
        return

    # max_iterations исчерпаны — мягкий fallback с handoff в логе
    log.warning("Agent reached max_iterations for session %s", session_id)
    yield {
        "type": "done",
        "final_text": "".join(final_text_parts) or "Извините, не получилось ответить сразу — передам Алёне, она свяжется.",
        "stop_reason": "max_iterations",
    }


async def run_turn_collect(session_id: str, channel: str, user_text: str, **kwargs) -> str:
    """Удобная обёртка — собрать финальный текст без стриминга (для TG/Wazzup)."""
    parts = []
    async for ev in run_turn(session_id, channel, user_text, **kwargs):
        if ev["type"] == "text_delta":
            parts.append(ev["text"])
        elif ev["type"] == "error":
            log.error("run_turn_collect error: %s", ev["message"])
            return parts and "".join(parts) or "Сейчас не получилось ответить — передам Алёне, она свяжется."
    return "".join(parts).strip()
