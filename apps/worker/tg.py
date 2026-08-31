from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from telethon import TelegramClient

from apps.worker.config import get_worker_settings
from apps.worker.parser import _parse_proxy

logger = logging.getLogger(__name__)


def session_base_path(path: str) -> str:
    p = Path(path)
    # Telethon appends .session itself
    return str(p.with_suffix("")) if p.suffix == ".session" else str(p)


def _tune_sqlite_session(client: TelegramClient) -> None:
    """Reduce 'database is locked' on Docker Desktop bind-mounted session files."""
    session = getattr(client, "session", None)
    conn = getattr(session, "_conn", None)
    if conn is None:
        return
    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.commit()
    except sqlite3.Error as exc:
        logger.warning("Could not tune Telegram session SQLite: %s", exc)


def make_telegram_client() -> TelegramClient:
    settings = get_worker_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("TELEGRAM_API_ID / TELEGRAM_API_HASH missing")
    client = TelegramClient(
        session_base_path(settings.telegram_session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        proxy=_parse_proxy(settings.telegram_proxy),
    )
    _tune_sqlite_session(client)
    return client
