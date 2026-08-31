from decimal import Decimal

import pytest
from pydantic import ValidationError

from apps.api.schemas.catalog import ChannelStatusUpdate, MarkupRule, StoreSettingsUpdate, admin_product_out
from apps.api.services.pricing import apply_markup, compute_median_cost, resolve_markup, round_price, storefront_price


def test_median_odd():
    assert compute_median_cost([100, 200, 300]) == Decimal("200.00")


def test_median_even():
    assert compute_median_cost([100, 200]) == Decimal("150.00")


def test_markup_and_round():
    cost, price = storefront_price([98000, 100000, 99000], markup_percent=10, round_to=100)
    assert cost == Decimal("99000.00")
    assert apply_markup(Decimal("99000"), 10) == Decimal("108900.00")
    assert price == Decimal("108900")


def test_round_to_100():
    assert round_price(Decimal("108940"), 100) == Decimal("108900")
    assert round_price(Decimal("108960"), 100) == Decimal("109000")


def test_parse_spaced_and_dotted_prices():
    from apps.worker.parser import parse_price_text

    lines = parse_price_text(
        "🇮🇳 17e 256GB Black    - 56 800\n"
        "Ray-Ban Wayfarer Gen2 - 39.000₽\n"
        "AirPods 4 - 9 600\n"
    )
    prices = {line.title: line.price for line in lines}
    assert any(p == Decimal("56800") for p in prices.values())
    assert any(p == Decimal("39000") for p in prices.values())
    assert any(p == Decimal("9600") for p in prices.values())


def test_resolve_markup_first_match_wins() -> None:
    rules = [
        {"match": "brand", "value": "Apple", "percent": 5},
        {"match": "kind", "value": "iphone", "percent": 12},
    ]
    assert resolve_markup(0, rules, brand="apple", kind="iphone") == 5.0
    assert resolve_markup(0, rules, brand="Samsung", kind="iphone") == 12.0
    assert resolve_markup(3, rules, brand="Dyson", kind="dyson") == 3.0


def test_resolve_markup_category_and_bad_percent() -> None:
    rules = [
        {"match": "category", "value": "Смартфоны ASIS", "percent": "nope"},
        {"match": "category", "value": "Смартфоны ASIS", "percent": 8},
    ]
    assert resolve_markup(0, rules, category="смартфоны asis") == 8.0


def test_markup_rule_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        MarkupRule.model_validate(
            {"match": "brand", "value": "Apple", "percent": 1, "role": "admin"}
        )


def test_settings_update_forbids_extra_and_caps_rules() -> None:
    with pytest.raises(ValidationError):
        StoreSettingsUpdate.model_validate({"default_markup_percent": 0, "is_active": True})
    with pytest.raises(ValidationError):
        StoreSettingsUpdate.model_validate({"last_sync_stats": {"channels": 1}})
    too_many = [{"match": "brand", "value": str(i), "percent": 1} for i in range(51)]
    with pytest.raises(ValidationError):
        StoreSettingsUpdate.model_validate({"markup_rules": too_many})
    StoreSettingsUpdate.model_validate(
        {"markup_rules": [{"match": "kind", "value": "iphone", "percent": 0}]}
    )


def test_channel_status_forbids_extra() -> None:
    ChannelStatusUpdate.model_validate({"status": "active", "counts_toward_price": False})
    with pytest.raises(ValidationError):
        ChannelStatusUpdate.model_validate({"status": "active", "role": "admin"})


def test_outlier_does_not_move_median() -> None:
    from apps.api.services.pricing import quarantine_outliers, quote_storefront

    kept, dropped = quarantine_outliers([100000, 101000, 99000, 999000])
    assert Decimal("999000.00") in {p for p, _ in dropped}
    assert Decimal("999000.00") not in kept
    quote = quote_storefront([100000, 101000, 99000, 999000], markup_percent=0, round_to=100)
    assert quote.cost_median == Decimal("100000.00")
    assert quote.price == Decimal("100000")


def test_receipt_includes_price_and_channel() -> None:
    from apps.api.services.pricing import SupplierBid, quote_storefront, receipt_payload

    quote = quote_storefront(
        [
            SupplierBid(Decimal("100000"), "Big Sale"),
            SupplierBid(Decimal("101000"), "TECHNOV"),
            SupplierBid(Decimal("99000"), "Unisale"),
            SupplierBid(Decimal("999000"), "Spam Channel"),
        ],
        markup_percent=5,
        round_to=100,
    )
    receipt = receipt_payload(quote, markup_percent=5, round_to=100)
    assert receipt["accepted_n"] == 3
    assert receipt["quarantined_n"] == 1
    assert "100000.00 · Big Sale" in receipt["accepted"]
    assert "101000.00 · TECHNOV" in receipt["accepted"]
    assert "99000.00 · Unisale" in receipt["accepted"]
    assert any("999000.00 · Spam Channel" in line and "outlier" in line for line in receipt["quarantined"])
    # Bare prices still work (channel unknown)
    bare = receipt_payload(
        quote_storefront([100000, 101000, 99000], markup_percent=0, round_to=100),
        0,
        100,
    )
    assert bare["accepted"] == ["100000.00 · ?", "101000.00 · ?", "99000.00 · ?"]


def test_two_prices_skip_quarantine() -> None:
    from apps.api.services.pricing import quarantine_outliers

    kept, dropped = quarantine_outliers([100000, 500000])
    assert dropped == []
    assert len(kept) == 2


def test_admin_product_out_maps_receipt() -> None:
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from uuid import uuid4

    product = SimpleNamespace(
        id=uuid4(),
        slug="iphone-air",
        title="iPhone Air",
        brand="Apple",
        price=Decimal("100000"),
        cost_median=Decimal("100000.00"),
        markup_percent=Decimal("0.00"),
        is_hot=False,
        is_published=True,
        is_manual=False,
        image_url=None,
        updated_at=datetime.now(timezone.utc),
        attributes={
            "price_receipt": {
                "accepted_n": 3,
                "quarantined_n": 1,
                "accepted": ["100000.00 · Big Sale", "101000.00 · TECHNOV", "99000.00 · Unisale"],
                "quarantined": ["999000.00 · Spam (outlier)"],
                "markup_percent": 0,
                "round_to": 100,
            }
        },
    )
    out = admin_product_out(product)
    assert out.price_receipt is not None
    assert out.price_receipt.accepted_n == 3
    assert out.price_receipt.accepted[0] == "100000.00 · Big Sale"
    assert out.price_receipt.quarantined == ["999000.00 · Spam (outlier)"]
