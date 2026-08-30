from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.account import BonusLedger, UserNotification
from apps.api.models.order import Order
from apps.api.models.user import User
from apps.api.services.referrals import round_money
from apps.api.services.sessions import revoke_all_sessions

MAX_ABS_DELTA = Decimal("1000000")
CHECKOUT_SPEND_LEVEL = -1


def resolve_bonus_spend(
    requested: Decimal | None,
    *,
    balance: Decimal,
    goods_total: Decimal,
) -> Decimal:
    amount = round_money(Decimal(str(requested or 0)))
    if amount <= 0:
        return Decimal("0.00")
    goods = round_money(goods_total)
    available = round_money(balance)
    if amount > available:
        raise ValueError("Недостаточно бонусов")
    if amount > goods:
        raise ValueError("Нельзя списать больше стоимости заказа")
    return amount


async def apply_checkout_spend(
    db: AsyncSession,
    user: User,
    order: Order,
    spend: Decimal,
) -> UserNotification | None:
    amount = round_money(spend)
    if amount <= 0:
        return None
    current = round_money(Decimal(str(user.bonus_balance or 0)))
    if amount > current:
        raise ValueError("Недостаточно бонусов")
    user.bonus_balance = round_money(current - amount)
    db.add(
        BonusLedger(
            user_id=user.id,
            order_id=order.id,
            level=CHECKOUT_SPEND_LEVEL,
            amount=-amount,
            note="Списание при заказе",
        )
    )
    notice = UserNotification(
        user_id=user.id,
        kind="bonus",
        title="Списание бонусов",
        body=f"−{amount} ₽ за заказ {order.number}",
    )
    db.add(notice)
    return notice


async def apply_admin_bonus(
    db: AsyncSession,
    user: User,
    *,
    delta: Decimal,
    note: str | None,
) -> tuple[User, UserNotification]:
    amount = round_money(delta)
    if amount == 0:
        raise ValueError("Сумма не должна быть нулевой")
    if abs(amount) > MAX_ABS_DELTA:
        raise ValueError("Слишком большая сумма")
    current = Decimal(str(user.bonus_balance or 0))
    next_balance = round_money(current + amount)
    if next_balance < 0:
        raise ValueError("Баланс не может стать отрицательным")
    user.bonus_balance = next_balance
    cleaned = (note or "").strip() or None
    db.add(
        BonusLedger(
            user_id=user.id,
            order_id=None,
            level=0,
            amount=amount,
            note=cleaned,
        )
    )
    sign = "+" if amount > 0 else ""
    notice = UserNotification(
        user_id=user.id,
        kind="bonus",
        title="Бонусный счёт",
        body=f"Админ: {sign}{amount} ₽" + (f". {cleaned}" if cleaned else ""),
    )
    db.add(notice)
    return user, notice


async def set_user_active(db: AsyncSession, user: User, *, is_active: bool) -> User:
    user.is_active = is_active
    if not is_active:
        await revoke_all_sessions(db, user)
    return user
