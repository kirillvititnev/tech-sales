from decimal import Decimal

from apps.api.services.admin_alerts import format_ops_alert, is_price_jump


def test_price_jump_requires_ratio_and_rubles() -> None:
    assert is_price_jump(Decimal("100000"), Decimal("130000"))
    assert is_price_jump(Decimal("100000"), Decimal("70000"))
    assert not is_price_jump(Decimal("100000"), Decimal("110000"))
    assert not is_price_jump(Decimal("500"), Decimal("800"))
    assert not is_price_jump(None, Decimal("100000"))
    assert not is_price_jump(Decimal("0"), Decimal("100000"))


def test_ops_alert_empty_is_none() -> None:
    assert format_ops_alert(folder="Apple", errors=[], jumps=[]) is None


def test_ops_alert_escapes_html_and_caps_lines() -> None:
    text = format_ops_alert(
        folder="Apple <x>",
        errors=[("Top <ch>", "fail <script>")],
        jumps=[("iPhone 16", Decimal("100000"), Decimal("130000"))],
    )
    assert text is not None
    assert "Apple &lt;x&gt;" in text
    assert "Top &lt;ch&gt;" in text
    assert "fail &lt;script&gt;" in text
    assert "100 000 ₽" in text
    assert "130 000 ₽" in text
    assert "<script>" not in text
