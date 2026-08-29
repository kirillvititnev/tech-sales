from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.api.models.account import BonusLedger, UserNotification
from apps.api.services.bonuses import apply_admin_bonus


class _Db:
    def __init__(self) -> None:
        self.items: list[object] = []

    def add(self, item: object) -> None:
        self.items.append(item)


@pytest.mark.asyncio
async def test_admin_bonus_credit_and_ledger() -> None:
    db = _Db()
    user = SimpleNamespace(id=uuid4(), bonus_balance=Decimal("10.00"))
    await apply_admin_bonus(db, user, delta=Decimal("25"), note="  акция  ")
    assert user.bonus_balance == Decimal("35.00")
    ledger = next(item for item in db.items if isinstance(item, BonusLedger))
    note = next(item for item in db.items if isinstance(item, UserNotification))
    assert ledger.order_id is None
    assert ledger.level == 0
    assert ledger.amount == Decimal("25.00")
    assert ledger.note == "акция"
    assert "25.00" in note.body


@pytest.mark.asyncio
async def test_admin_bonus_rejects_zero_and_overdraft() -> None:
    db = _Db()
    user = SimpleNamespace(id=uuid4(), bonus_balance=Decimal("10.00"))
    with pytest.raises(ValueError, match="нулевой"):
        await apply_admin_bonus(db, user, delta=Decimal("0"), note=None)
    with pytest.raises(ValueError, match="отрицательным"):
        await apply_admin_bonus(db, user, delta=Decimal("-20"), note=None)
    with pytest.raises(ValueError, match="большая"):
        await apply_admin_bonus(db, user, delta=Decimal("1000001"), note=None)
