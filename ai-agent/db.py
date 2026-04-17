"""Асинхронная SQLite — хранит диалоги, контакты, лиды.

В MVP этого хватает. Если пойдёт нагрузка — менять на Postgres не нужно,
нужно переносить БД в отдельный файл.
"""
import json
import aiosqlite
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from config import DB_PATH

MINSK = timezone(timedelta(hours=3))


def now_iso() -> str:
    return datetime.now(MINSK).isoformat(timespec="seconds")


async def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL UNIQUE,
            channel TEXT NOT NULL,           -- site | telegram | whatsapp | viber
            external_user_id TEXT,
            name TEXT,
            phone TEXT,
            city TEXT,
            status TEXT DEFAULT 'new',       -- new | qualifying | kp_sent | contract_sent | handed_off | won | lost
            notes TEXT,
            extra_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,              -- user | assistant | tool
            content_json TEXT NOT NULL,      -- Anthropic content block(s) as JSON
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES conversations(session_id)
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            event_type TEXT NOT NULL,        -- kp_sent | contract_sent | handoff | price_quoted | model_suggested
            payload_json TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
        """)
        await db.commit()


async def get_or_create_conversation(session_id: str, channel: str, external_user_id: Optional[str] = None) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM conversations WHERE session_id = ?", (session_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        now = now_iso()
        await db.execute(
            "INSERT INTO conversations(session_id, channel, external_user_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'new', ?, ?)",
            (session_id, channel, external_user_id, now, now),
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM conversations WHERE session_id = ?", (session_id,))
        return dict(await cur.fetchone())


async def update_conversation(session_id: str, **fields):
    if not fields:
        return
    fields["updated_at"] = now_iso()
    cols = ", ".join(f"{k} = ?" for k in fields)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE conversations SET {cols} WHERE session_id = ?", (*fields.values(), session_id))
        await db.commit()


async def add_message(session_id: str, role: str, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages(session_id, role, content_json, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, json.dumps(content, ensure_ascii=False), now_iso()),
        )
        await db.execute(
            "UPDATE conversations SET updated_at = ? WHERE session_id = ?",
            (now_iso(), session_id),
        )
        await db.commit()


async def get_history(session_id: str, limit: int = 50) -> list[dict]:
    """История для подачи в API Claude. Возвращает список {role, content}."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT role, content_json FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        )
        rows = await cur.fetchall()
        result = []
        for r in rows:
            content = json.loads(r["content_json"])
            # Anthropic API принимает только "user" и "assistant"; "tool" это user-role с tool_result
            if r["role"] == "tool":
                result.append({"role": "user", "content": content})
            else:
                result.append({"role": r["role"], "content": content})
        return result


async def add_event(session_id: Optional[str], event_type: str, payload: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO events(session_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (session_id, event_type, json.dumps(payload, ensure_ascii=False), now_iso()),
        )
        await db.commit()
