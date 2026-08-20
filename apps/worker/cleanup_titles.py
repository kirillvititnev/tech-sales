"""One-shot: reclassify published products from active offers; unpublish rejects."""

from __future__ import annotations

import asyncio
import re
from collections import Counter

from sqlalchemy import select

from apps.api.db import SessionLocal
from apps.api.models.catalog import Product, ProductOffer
from apps.worker.offer_identity import classify_offer


async def main() -> None:
    stats: Counter[str] = Counter()
    async with SessionLocal() as session:
        products = (
            await session.execute(select(Product).where(Product.is_published.is_(True)))
        ).scalars().all()
        for product in products:
            offer = (
                await session.execute(
                    select(ProductOffer)
                    .where(
                        ProductOffer.product_id == product.id,
                        ProductOffer.is_active.is_(True),
                    )
                    .order_by(ProductOffer.parsed_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if not offer:
                product.is_published = False
                stats["unpublish_no_offer"] += 1
                continue

            section = (offer.raw_payload or {}).get("section")
            # Prefer raw line without glued price when available
            raw = (offer.raw_payload or {}).get("raw") or offer.raw_title
            line = str(raw)
            line = re.sub(r"\s*[-–—]\s*\d[\d\s.]*\s*(?:₽|р|rub)?\s*$", "", line, flags=re.I)
            line = re.sub(r"\b\d{1,3}(?:[.\s]\d{3}){1,2}\b\s*(?:₽|р)?\s*$", "", line, flags=re.I)
            line = line.strip()
            identity = classify_offer(line, section=section if isinstance(section, str) else None)

            if not identity.publish:
                product.is_published = False
                stats[f"unpublish:{identity.reject_reason or 'reject'}"] += 1
                continue

            product.title = identity.display_title
            product.brand = identity.brand or product.brand
            attrs = dict(product.attributes or {})
            attrs.update(
                {
                    "kind": identity.kind.value if identity.kind else attrs.get("kind"),
                    "device_name": identity.device_name,
                    "device_category": identity.device_category,
                    "config": identity.config,
                    "model": identity.model,
                    "color": identity.color,
                    "storage": identity.storage,
                    "ram": identity.ram,
                    "norm_key": identity.identity_key,
                    "folder": attrs.get("folder"),
                }
            )
            product.attributes = attrs
            stats["updated"] += 1

        await session.commit()

    print("cleanup done:")
    for key, count in sorted(stats.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {key}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
