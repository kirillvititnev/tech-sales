from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.account import BonusLedger
from apps.api.models.order import Order
from apps.api.models.user import User
from apps.api.security import new_order_access_token

REDACTED_NAME = "Удалённый аккаунт"
REDACTED_PHONE = "00000000000"


def redact_order(order: Order) -> None:
    order.customer_name = REDACTED_NAME
    order.customer_phone = REDACTED_PHONE
    order.customer_telegram = None
    order.delivery_address = None
    order.comment = None
    order.access_token = new_order_access_token()


async def erase_account_personal_data(db: AsyncSession, user: User) -> None:
    """Art. 17 / 152-ФЗ: drop identifiers while keeping anonymous order rows."""
    result = await db.execute(select(Order).where(Order.user_id == user.id))
    for order in result.scalars().all():
        redact_order(order)
    await db.execute(update(BonusLedger).where(BonusLedger.user_id == user.id).values(note=None))
