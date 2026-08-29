from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.account import BonusLedger, UserNotification
from apps.api.models.user import User
from apps.api.services.referrals import round_money
from apps.api.services.sessions import revoke_all_sessions

MAX_ABS_DELTA = Decimal("1000000")


async def apply_admin_bonus(
    db: AsyncSession,
    user: User,
    *,
    delta: Decimal,
    note: str | None,
) -> User:
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
    db.add(
        UserNotification(
            user_id=user.id,
            kind="bonus",
            title="Бонусный счёт",
            body=f"Админ: {sign}{amount} ₽" + (f". {cleaned}" if cleaned else ""),
        )
    )
    return user


async def set_user_active(db: AsyncSession, user: User, *, is_active: bool) -> User:
    user.is_active = is_active
    if not is_active:
        await revoke_all_sessions(db, user)
    return user
