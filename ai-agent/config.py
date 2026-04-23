"""Конфигурация AI-агента КРОНОВЪ. Читает .env."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env", override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
# Если агент развёрнут в санкционной стране (BY/RU/...), Anthropic API вернёт
# 403 forbidden. Обход — прокси через Cloudflare Worker (см. deploy/cloudflare-worker.js).
# ANTHROPIC_BASE_URL: https://kronov-claude.<accountId>.workers.dev
# ANTHROPIC_PROXY_SECRET: тот же, что прописан в PROXY_SECRET Worker-а.
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "").rstrip("/")
ANTHROPIC_PROXY_SECRET = os.getenv("ANTHROPIC_PROXY_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALENA_TELEGRAM_CHAT_ID = os.getenv("ALENA_TELEGRAM_CHAT_ID", "")
ALENA_PHONE = os.getenv("ALENA_PHONE", "+375296888629")
ALENA_NAME = os.getenv("ALENA_NAME", "Алёна")

SITE_URL = os.getenv("SITE_URL", "https://kronov.by")
SITE_ORIGIN = os.getenv("SITE_ORIGIN", "https://kronov.by")

WAZZUP_ACCOUNT_ID = os.getenv("WAZZUP_ACCOUNT_ID", "")
WAZZUP_API_KEY = os.getenv("WAZZUP_API_KEY", "")
# Shared-secret для проверки входящих webhook-ов от Wazzup. Если задан — сравниваем
# с заголовком Authorization (или X-Wazzup-Token). Если пусто — проверка отключена,
# но при старте печатаем WARN. На проде ставить ОБЯЗАТЕЛЬНО.
WAZZUP_WEBHOOK_TOKEN = os.getenv("WAZZUP_WEBHOOK_TOKEN", "")

# Простейший rate-limit на /chat по IP.
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "20"))     # запросов
CHAT_RATE_WINDOW = int(os.getenv("CHAT_RATE_WINDOW", "60"))   # секунд

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
]

DB_PATH = BASE_DIR / "data" / "conversations.sqlite"
KP_DIR = BASE_DIR / "data" / "kp"
KP_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS_DIR = BASE_DIR / "prompts"
STATIC_DIR = BASE_DIR / "static"
