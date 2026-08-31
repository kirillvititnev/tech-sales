from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.api.models.account import BonusLedger, UserNotification
from apps.api.services.bonuses import apply_admin_bonus, apply_checkout_spend, resolve_bonus_spend


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


def test_resolve_bonus_spend_ok_and_rejects() -> None:
    assert resolve_bonus_spend(None, balance=Decimal("20"), goods_total=Decimal("50")) == Decimal("0.00")
    assert resolve_bonus_spend(Decimal("0"), balance=Decimal("20"), goods_total=Decimal("50")) == Decimal(
        "0.00"
    )
    assert resolve_bonus_spend(
        Decimal("10.4"),
        balance=Decimal("20"),
        goods_total=Decimal("50"),
    ) == Decimal("10.40")
    with pytest.raises(ValueError, match="Недостаточно"):
        resolve_bonus_spend(Decimal("30"), balance=Decimal("20"), goods_total=Decimal("50"))
    with pytest.raises(ValueError, match="больше стоимости"):
        resolve_bonus_spend(Decimal("40"), balance=Decimal("100"), goods_total=Decimal("30"))


@pytest.mark.asyncio
async def test_checkout_spend_debits_and_ledger() -> None:
    db = _Db()
    user = SimpleNamespace(id=uuid4(), bonus_balance=Decimal("50.00"))
    order = SimpleNamespace(id=uuid4(), number="WS-1")
    await apply_checkout_spend(db, user, order, Decimal("20"))
    assert user.bonus_balance == Decimal("30.00")
    ledger = next(item for item in db.items if isinstance(item, BonusLedger))
    note = next(item for item in db.items if isinstance(item, UserNotification))
    assert ledger.order_id == order.id
    assert ledger.level == -1
    assert ledger.amount == Decimal("-20.00")
    assert "WS-1" in note.body


@pytest.mark.asyncio
async def test_checkout_spend_rejects_overdraft() -> None:
    db = _Db()
    user = SimpleNamespace(id=uuid4(), bonus_balance=Decimal("10.00"))
    order = SimpleNamespace(id=uuid4(), number="WS-1")
    with pytest.raises(ValueError, match="Недостаточно"):
        await apply_checkout_spend(db, user, order, Decimal("20"))
