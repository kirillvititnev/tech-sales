from decimal import Decimal

from apps.api.services.pricing import apply_markup, compute_median_cost, round_price, storefront_price


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
