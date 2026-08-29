"""Recompute storefront prices from active supplier offers after markup changes."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.models.catalog import Product, StoreSettings
from apps.api.services.favorite_alerts import FavoriteWatch, notify_favorite_watchers, watches_for_update
from apps.api.services.pricing import resolve_markup, storefront_price


def synced_storefront_quote(
    *,
    brand: str | None,
    attributes: dict | None,
    offer_prices: list[Decimal],
    default_markup: float | Decimal,
    rules: list[dict] | None,
    round_to: int,
) -> tuple[Decimal, Decimal, float] | None:
    if not offer_prices:
        return None
    attrs = attributes if isinstance(attributes, dict) else {}
    kind = str(attrs.get("kind") or "") or None
    category = str(attrs.get("device_category") or "") or None
    markup_pct = resolve_markup(
        default_markup,
        rules,
        brand=brand,
        category=category,
        kind=kind,
    )
    cost, price = storefront_price(offer_prices, markup_percent=markup_pct, round_to=round_to)
    if cost is None or price is None:
        return None
    return cost, price, markup_pct


def apply_quote(
    *,
    product_id: UUID,
    title: str,
    old_price: Decimal | None,
    old_cost: Decimal | None,
    old_markup: Decimal | None,
    quote: tuple[Decimal, Decimal, float],
) -> tuple[Decimal, Decimal, Decimal, list[FavoriteWatch]] | None:
    cost, price, markup_pct = quote
    markup_dec = Decimal(str(markup_pct)).quantize(Decimal("0.01"))

    def _q(value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.01"))

    if _q(old_price) == _q(price) and _q(old_cost) == _q(cost) and _q(old_markup) == markup_dec:
        return None
    events = watches_for_update(
        product_id=product_id,
        title=title,
        was_published=True,
        old_price=Decimal(str(old_price)) if old_price is not None else None,
        new_price=price,
    )
    return cost, price, markup_dec, events


async def reprice_synced_products(db: AsyncSession, settings: StoreSettings) -> int:
    result = await db.execute(
        select(Product)
        .where(Product.is_manual.is_(False))
        .options(selectinload(Product.offers))
    )
    products = list(result.scalars().all())
    rules = list(settings.markup_rules or [])
    default_markup = float(settings.default_markup_percent)
    round_to = int(settings.price_round_to)
    changed = 0
    events: list[FavoriteWatch] = []
    for product in products:
        prices = [
            Decimal(str(offer.raw_price))
            for offer in product.offers
            if offer.is_active
        ]
        quote = synced_storefront_quote(
            brand=product.brand,
            attributes=product.attributes,
            offer_prices=prices,
            default_markup=default_markup,
            rules=rules,
            round_to=round_to,
        )
        if quote is None:
            continue
        applied = apply_quote(
            product_id=product.id,
            title=product.title,
            old_price=product.price,
            old_cost=product.cost_median,
            old_markup=product.markup_percent,
            quote=quote,
        )
        if applied is None:
            continue
        cost, price, markup_dec, watches = applied
        product.cost_median = cost
        product.price = price
        product.markup_percent = markup_dec
        events.extend(watches)
        changed += 1
    await notify_favorite_watchers(db, events)
    return changed
