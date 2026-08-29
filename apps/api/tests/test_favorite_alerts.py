from decimal import Decimal
from uuid import uuid4

from apps.api.services.favorite_alerts import (
    KIND_BACK_IN_STOCK,
    KIND_PRICE_DROP,
    build_favorite_notices,
    format_rub,
    notice_for,
    watches_for_update,
)


def test_format_rub() -> None:
    assert format_rub(Decimal("99900")) == "99 900 ₽"


def test_watches_price_drop_only_when_lower() -> None:
    pid = uuid4()
    assert watches_for_update(
        product_id=pid,
        title="iPhone 16",
        was_published=True,
        old_price=Decimal("100000"),
        new_price=Decimal("100000"),
    ) == []
    assert watches_for_update(
        product_id=pid,
        title="iPhone 16",
        was_published=True,
        old_price=None,
        new_price=Decimal("90000"),
    ) == []
    events = watches_for_update(
        product_id=pid,
        title="iPhone 16",
        was_published=True,
        old_price=Decimal("100000"),
        new_price=Decimal("90000"),
    )
    assert len(events) == 1
    assert events[0].kind == KIND_PRICE_DROP


def test_watches_back_in_stock_and_cheaper() -> None:
    pid = uuid4()
    events = watches_for_update(
        product_id=pid,
        title="iPhone 16",
        was_published=False,
        old_price=Decimal("100000"),
        new_price=Decimal("90000"),
    )
    kinds = {event.kind for event in events}
    assert kinds == {KIND_BACK_IN_STOCK, KIND_PRICE_DROP}


def test_build_notices_one_per_user_kind() -> None:
    product_id = uuid4()
    user_a = uuid4()
    user_b = uuid4()
    events = watches_for_update(
        product_id=product_id,
        title="iPhone 16 128GB",
        was_published=True,
        old_price=Decimal("100000"),
        new_price=Decimal("90000"),
    )
    notices = build_favorite_notices(events, {product_id: [user_a, user_b, user_a]})
    assert len(notices) == 2
    assert {n.user_id for n in notices} == {user_a, user_b}
    assert all(n.kind == KIND_PRICE_DROP for n in notices)
    assert "90 000 ₽" in notices[0].body


def test_notice_copy() -> None:
    user_id = uuid4()
    drop = notice_for(
        user_id,
        watches_for_update(
            product_id=uuid4(),
            title="iPhone 16",
            was_published=True,
            old_price=Decimal("100000"),
            new_price=Decimal("90000"),
        )[0],
    )
    assert drop.title == "Цена снизилась"
    restock = notice_for(
        user_id,
        watches_for_update(
            product_id=uuid4(),
            title="iPhone 16",
            was_published=False,
            old_price=None,
            new_price=Decimal("90000"),
        )[0],
    )
    assert restock.kind == KIND_BACK_IN_STOCK
    assert restock.title == "Снова в каталоге"
