from decimal import Decimal

from apps.api.config import get_settings
from apps.api.services.admin_catalog import slugify_manual


def test_slugify_manual_stable() -> None:
    a = slugify_manual("iPhone 17 Pro")
    b = slugify_manual("iPhone 17 Pro")
    assert a == b
    assert "iphone" in a


def test_slugify_manual_differs_by_title() -> None:
    assert slugify_manual("A") != slugify_manual("B")


def test_env_markup_defaults() -> None:
    get_settings.cache_clear()
    s = get_settings()
    assert Decimal(str(s.default_markup_percent)) >= 0
    assert s.price_round_to >= 1
