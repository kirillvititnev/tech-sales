"""CLI: sync Telegram folder into catalog.

  PYTHONPATH=. .venv/bin/python -m apps.worker.run_sync
  PYTHONPATH=. .venv/bin/python -m apps.worker.run_sync --folder Apple
  PYTHONPATH=. .venv/bin/python -m apps.worker.run_sync --channel "Top re:sale" --messages 200
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from apps.worker.sync import sync_folder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Telegram folder → White Shop catalog")
    parser.add_argument("--folder", default="Apple", help="Telegram folder name")
    parser.add_argument("--messages", type=int, default=100, help="Messages per channel")
    parser.add_argument("--category", default="apple", help="Category slug")
    parser.add_argument(
        "--channel",
        default=None,
        help="Only sync channels whose title contains this substring (e.g. 'Top re:sale')",
    )
    parser.add_argument(
        "--telegram-id",
        default=None,
        help="Only sync this Telegram channel id",
    )
    args = parser.parse_args()

    stats = asyncio.run(
        sync_folder(
            args.folder,
            messages_per_channel=args.messages,
            category_slug=args.category,
            channel_title=args.channel,
            telegram_id=args.telegram_id,
        )
    )
    print(stats)


if __name__ == "__main__":
    main()
