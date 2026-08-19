"""CLI: sync Telegram folder into catalog.

  PYTHONPATH=. .venv/bin/python -m apps.worker.run_sync
  PYTHONPATH=. .venv/bin/python -m apps.worker.run_sync --folder Apple
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
    parser.add_argument("--messages", type=int, default=40, help="Messages per channel")
    parser.add_argument("--category", default="apple", help="Category slug")
    args = parser.parse_args()

    stats = asyncio.run(
        sync_folder(
            args.folder,
            messages_per_channel=args.messages,
            category_slug=args.category,
        )
    )
    print(stats)


if __name__ == "__main__":
    main()
