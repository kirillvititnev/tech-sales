from __future__ import annotations

from pathlib import Path

from telethon import TelegramClient

from apps.worker.config import get_worker_settings
from apps.worker.parser import _parse_proxy


def session_base_path(path: str) -> str:
    p = Path(path)
    # Telethon appends .session itself
    return str(p.with_suffix("")) if p.suffix == ".session" else str(p)


def make_telegram_client() -> TelegramClient:
    settings = get_worker_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("TELEGRAM_API_ID / TELEGRAM_API_HASH missing")
    return TelegramClient(
        session_base_path(settings.telegram_session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        proxy=_parse_proxy(settings.telegram_proxy),
    )
