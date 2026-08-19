"""Interactive Telegram MTProto login → local session file.

Usage (from repo root):
  PYTHONPATH=. .venv/bin/python -m apps.worker.login

You will be asked for phone number and the code from Telegram.
If 2FA is enabled, also enter your cloud password.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

from telethon import TelegramClient
from telethon.network.connection.tcpfull import ConnectionTcpFull

from apps.worker.config import get_worker_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("tg-login")


def build_proxy(proxy_url: str | None):
    if not proxy_url:
        return None
    parsed = urlparse(proxy_url)
    if not parsed.hostname or not parsed.port:
        raise SystemExit(f"Invalid TELEGRAM_PROXY: {proxy_url}")

    scheme = (parsed.scheme or "socks5").lower()
    # Telethon: (proxy_type, host, port) or (type, host, port, rdns, user, pass)
    proxy_type = scheme.replace("socks5h", "socks5")
    if parsed.username:
        return (
            proxy_type,
            parsed.hostname,
            parsed.port,
            True,
            parsed.username,
            parsed.password or "",
        )
    return (proxy_type, parsed.hostname, parsed.port)


async def main() -> None:
    settings = get_worker_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise SystemExit("TELEGRAM_API_ID / TELEGRAM_API_HASH are missing in .env")

    session_path = Path(settings.telegram_session_path)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    proxy = build_proxy(settings.telegram_proxy)
    if proxy:
        logger.info("Using proxy %s:%s", proxy[1], proxy[2])

    client = TelegramClient(
        str(session_path.with_suffix("")),  # Telethon adds .session
        settings.telegram_api_id,
        settings.telegram_api_hash,
        proxy=proxy,
        connection=ConnectionTcpFull,
    )

    await client.start()
    me = await client.get_me()
    logger.info(
        "Logged in as %s (id=%s). Session saved to %s",
        getattr(me, "username", None) or me.first_name,
        me.id,
        session_path,
    )
    dialogs = await client.get_dialogs(limit=5)
    logger.info("Sample dialogs (%s):", len(dialogs))
    for d in dialogs:
        logger.info("  - %s", d.name)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
