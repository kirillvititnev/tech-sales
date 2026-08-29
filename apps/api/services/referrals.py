from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.account import BonusLedger, UserNotification
from apps.api.models.catalog import StoreSettings
from apps.api.models.order import Order
from apps.api.models.user import User


def round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def referral_credits(
    total: Decimal,
    percents: tuple[Decimal, Decimal, Decimal],
    ancestor_ids: list[UUID],
) -> list[tuple[UUID, int, Decimal]]:
    """Return (user_id, level 1-3, amount) for a paid order. Level 1 is the direct referrer."""
    out: list[tuple[UUID, int, Decimal]] = []
    for index, user_id in enumerate(ancestor_ids[:3], start=1):
        pct = percents[index - 1]
        if pct <= 0:
            continue
        amount = round_money(total * pct / Decimal("100"))
        if amount > 0:
            out.append((user_id, index, amount))
    return out


async def ancestor_ids(db: AsyncSession, user_id: UUID, *, depth: int = 3) -> list[UUID]:
    ids: list[UUID] = []
    current = user_id
    seen: set[UUID] = {user_id}
    for _ in range(depth):
        result = await db.execute(select(User.referred_by_id).where(User.id == current))
        parent = result.scalar_one_or_none()
        if not parent or parent in seen:
            break
        ids.append(parent)
        seen.add(parent)
        current = parent
    return ids


async def credit_paid_order(db: AsyncSession, order: Order, settings: StoreSettings) -> None:
    if order.user_id is None:
        return
    existing = await db.execute(
        select(BonusLedger.id)
        .where(BonusLedger.order_id == order.id, BonusLedger.level >= 1)
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return
    percents = (
        settings.referral_percent_l1,
        settings.referral_percent_l2,
        settings.referral_percent_l3,
    )
    chain = await ancestor_ids(db, order.user_id)
    for user_id, level, amount in referral_credits(order.total_amount, percents, chain):
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            continue
        db.add(
            BonusLedger(
                user_id=user_id,
                order_id=order.id,
                level=level,
                amount=amount,
            )
        )
        user.bonus_balance = Decimal(str(user.bonus_balance)) + amount
        db.add(
            UserNotification(
                user_id=user_id,
                kind="bonus",
                title="Начисление бонусов",
                body=f"Уровень {level}: +{amount} ₽ за заказ {order.number}",
            )
        )
