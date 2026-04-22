"""Telegram-канал для агента — long-poll режим.

Используется когда нет публичного HTTPS-домена для webhook (актуально при
запуске на локальной машине / VPS без TLS). Если есть HTTPS — лучше
прописать webhook на /webhook/telegram (см. server.py).

Запуск: python tg_bot.py (рядом с уже запущенным server.py не обязательно —
этот файл работает автономно, разделяет только БД и модель).
"""
import asyncio
import logging
import os
import tempfile
from typing import Optional

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
from db import init_db
from agent import run_turn

# --- OpenAI клиент для транскрибации голоса ---
_openai = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("tg_bot")


async def transcribe_voice(file_bytes: bytes, suffix: str = ".ogg") -> str:
    """Транскрибируем голосовое через OpenAI gpt-4o-transcribe."""
    if not _openai:
        raise RuntimeError("OPENAI_API_KEY не задан в .env")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            result = _openai.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=f,
                language="ru",
                response_format="text",
            )
        return str(result).strip()
    finally:
        os.unlink(tmp_path)


async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Здравствуйте. КРОНОВЪ на связи. Чем помочь?"
    )


async def on_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Обработка голосовых и аудио-сообщений через gpt-4o-transcribe."""
    msg = update.effective_message
    if not msg or not msg.from_user:
        return

    await ctx.bot.send_chat_action(chat_id=msg.chat.id, action="typing")

    voice = msg.voice or msg.audio
    if not voice:
        return

    try:
        tg_file = await voice.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        text = await transcribe_voice(bytes(file_bytes))
    except Exception as e:
        log.error("Ошибка транскрибации: %s", e)
        await msg.reply_text("Не смог распознать голосовое — попробуйте написать текстом.")
        return

    if not text:
        await msg.reply_text("Не услышал слов. Попробуйте ещё раз или напишите текстом.")
        return

    log.info("Транскрибировано [%s]: %s", msg.from_user.id, text[:120])
    # Показываем что расслышали, потом обрабатываем как обычный текст
    await msg.reply_text(f"🎙 «{text}»")

    # Передаём расшифровку в агента (такая же логика как on_message)
    await _process_text(msg, ctx, text)


async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.from_user:
        return

    text = msg.text or msg.caption
    if not text:
        await msg.reply_text("Я работаю с текстом и голосовыми — напишите или запишите голосовое.")
        return

    await _process_text(msg, ctx, text)


async def _process_text(msg, ctx, text: str):

    chat_id = msg.chat.id
    session_id = f"tg-{chat_id}"
    user_id = str(msg.from_user.id)
    user_name = msg.from_user.first_name or ""
    initial_context: Optional[str] = None
    if user_name:
        initial_context = f"Telegram-имя пользователя: {user_name}"

    # Показываем "печатает..."
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")

    parts = []
    async for ev in run_turn(
        session_id=session_id,
        channel="telegram",
        user_text=text,
        external_user_id=user_id,
        initial_context=initial_context,
    ):
        if ev["type"] == "text_delta":
            parts.append(ev["text"])
        elif ev["type"] == "error":
            log.error("agent error: %s", ev["message"])

    answer = "".join(parts).strip() or "Сейчас не получилось ответить — передам Алёне, она с вами свяжется."
    # Telegram limit ~4096 символов
    for chunk in [answer[i : i + 3500] for i in range(0, len(answer), 3500)]:
        await msg.reply_text(chunk, disable_web_page_preview=True)


async def main_async():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан в .env")
    await init_db()


def main():
    asyncio.get_event_loop().run_until_complete(main_async())
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    log.info("Telegram-бот Андрей запущен (long polling). Жду сообщения. STT: gpt-4o-transcribe")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
