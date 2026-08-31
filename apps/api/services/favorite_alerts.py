"""Cabinet notices when a favorited product drops in price or returns to the catalog."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.account import Favorite, UserNotification

KIND_PRICE_DROP = "price_drop"
KIND_BACK_IN_STOCK = "back_in_stock"


@dataclass(frozen=True)
class FavoriteWatch:
    kind: str
    product_id: UUID
    title: str
    old_price: Decimal | None = None
    new_price: Decimal | None = None


def format_rub(amount: Decimal) -> str:
    n = int(Decimal(str(amount)).quantize(Decimal("1")))
    return f"{n:,} ₽".replace(",", " ")


def _clip(text: str, limit: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def watches_for_update(
    *,
    product_id: UUID,
    title: str,
    was_published: bool,
    old_price: Decimal | None,
    new_price: Decimal | None,
) -> list[FavoriteWatch]:
    events: list[FavoriteWatch] = []
    if not was_published:
        events.append(
            FavoriteWatch(kind=KIND_BACK_IN_STOCK, product_id=product_id, title=title)
        )
    if old_price is not None and new_price is not None and new_price < old_price:
        events.append(
            FavoriteWatch(
                kind=KIND_PRICE_DROP,
                product_id=product_id,
                title=title,
                old_price=old_price,
                new_price=new_price,
            )
        )
    return events


def notice_for(user_id: UUID, watch: FavoriteWatch) -> UserNotification:
    title = _clip(watch.title, 180)
    if watch.kind == KIND_PRICE_DROP and watch.old_price is not None and watch.new_price is not None:
        return UserNotification(
            user_id=user_id,
            kind=KIND_PRICE_DROP,
            title="Цена снизилась",
            body=f"{title}: было {format_rub(watch.old_price)}, стало {format_rub(watch.new_price)}",
        )
    return UserNotification(
        user_id=user_id,
        kind=KIND_BACK_IN_STOCK,
        title="Снова в каталоге",
        body=f"{title} снова появился в каталоге.",
    )


def build_favorite_notices(
    events: list[FavoriteWatch],
    watchers: dict[UUID, list[UUID]],
) -> list[UserNotification]:
    notices: list[UserNotification] = []
    seen: set[tuple[UUID, UUID, str]] = set()
    for event in events:
        for user_id in watchers.get(event.product_id, []):
            key = (user_id, event.product_id, event.kind)
            if key in seen:
                continue
            seen.add(key)
            notices.append(notice_for(user_id, event))
    return notices


async def notify_favorite_watchers(session: AsyncSession, events: list[FavoriteWatch]) -> list[UserNotification]:
    if not events:
        return []
    product_ids = {event.product_id for event in events}
    result = await session.execute(
        select(Favorite.user_id, Favorite.product_id).where(Favorite.product_id.in_(product_ids))
    )
    watchers: dict[UUID, list[UUID]] = defaultdict(list)
    for user_id, product_id in result.all():
        watchers[product_id].append(user_id)
    notices = build_favorite_notices(events, watchers)
    for notice in notices:
        session.add(notice)
    return notices
