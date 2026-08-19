"""Admin helpers: store settings singleton and slug for manual products."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import get_settings
from apps.api.models.catalog import StoreSettings


async def get_or_create_store_settings(db: AsyncSession) -> StoreSettings:
    result = await db.execute(select(StoreSettings).where(StoreSettings.id == 1))
    row = result.scalar_one_or_none()
    if row:
        return row
    env = get_settings()
    row = StoreSettings(
        id=1,
        default_markup_percent=Decimal(str(env.default_markup_percent)),
        price_round_to=env.price_round_to,
    )
    db.add(row)
    await db.flush()
    return row


def slugify_manual(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title.lower())
    ascii_part = normalized.encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_part).strip("-")[:50] or "manual"
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"
