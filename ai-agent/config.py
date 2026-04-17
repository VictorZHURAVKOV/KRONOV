"""Конфигурация AI-агента КРОНОВЪ. Читает .env."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env", override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALENA_TELEGRAM_CHAT_ID = os.getenv("ALENA_TELEGRAM_CHAT_ID", "")
ALENA_PHONE = os.getenv("ALENA_PHONE", "+375296888629")
ALENA_NAME = os.getenv("ALENA_NAME", "Алёна")

SITE_URL = os.getenv("SITE_URL", "https://zastroyka.by")
SITE_ORIGIN = os.getenv("SITE_ORIGIN", "https://zastroyka.by")

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
