"""Telegram-канал для агента — long-poll режим.

Используется когда нет публичного HTTPS-домена для webhook (актуально при
запуске на локальной машине / VPS без TLS). Если есть HTTPS — лучше
прописать webhook на /webhook/telegram (см. server.py).

Запуск: python tg_bot.py (рядом с уже запущенным server.py не обязательно —
этот файл работает автономно, разделяет только БД и модель).
"""
import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from db import init_db
from agent import run_turn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("tg_bot")


async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Здравствуйте. Я Андрей из Кронова — подбираю беседки и считаю стоимость. "
        "Расскажите, что вас интересует?"
    )


async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.from_user:
        return

    text = msg.text or msg.caption
    if not text:
        await msg.reply_text("Я работаю с текстом — напишите словами, что нужно.")
        return

    chat_id = msg.chat.id
    session_id = f"tg-{chat_id}"
    user_id = str(msg.from_user.id)
    user_name = msg.from_user.first_name or ""
    initial_context: Optional[str] = None
    if user_name and msg.text and "/start" not in msg.text:
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    log.info("Telegram-бот Андрей запущен (long polling). Жду сообщения.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
