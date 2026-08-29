from decimal import Decimal
from uuid import uuid4

from apps.api.services.pricing import storefront_price
from apps.api.services.reprice import apply_quote, synced_storefront_quote


def test_quote_uses_brand_rule_not_kind() -> None:
    quote = synced_storefront_quote(
        brand="Apple",
        attributes={"kind": "iphone", "device_category": "Смартфоны"},
        offer_prices=[Decimal("100000")],
        default_markup=0,
        rules=[
            {"match": "brand", "value": "Apple", "percent": 10},
            {"match": "kind", "value": "iphone", "percent": 50},
        ],
        round_to=100,
    )
    assert quote is not None
    cost, price, pct = quote
    assert cost == Decimal("100000.00")
    assert pct == 10.0
    assert price == storefront_price([100000], markup_percent=10, round_to=100)[1]


def test_quote_skips_empty_offers() -> None:
    assert (
        synced_storefront_quote(
            brand="Apple",
            attributes={},
            offer_prices=[],
            default_markup=10,
            rules=None,
            round_to=100,
        )
        is None
    )


def test_apply_quote_noop_when_unchanged() -> None:
    pid = uuid4()
    quote = (Decimal("100000.00"), Decimal("100000"), 0.0)
    assert (
        apply_quote(
            product_id=pid,
            title="iPhone 16",
            old_price=Decimal("100000"),
            old_cost=Decimal("100000.00"),
            old_markup=Decimal("0.00"),
            quote=quote,
        )
        is None
    )


def test_apply_quote_emits_price_drop() -> None:
    pid = uuid4()
    quote = (Decimal("90000.00"), Decimal("90000"), 0.0)
    applied = apply_quote(
        product_id=pid,
        title="iPhone 16",
        old_price=Decimal("100000"),
        old_cost=Decimal("100000.00"),
        old_markup=Decimal("0.00"),
        quote=quote,
    )
    assert applied is not None
    _cost, price, markup, events = applied
    assert price == Decimal("90000")
    assert markup == Decimal("0.00")
    assert len(events) == 1
    assert events[0].kind == "price_drop"
