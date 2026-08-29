"""Storefront pricing: median of supplier offers + markup + rounding."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from statistics import median


def compute_median_cost(prices: list[Decimal | float | int]) -> Decimal | None:
    if not prices:
        return None
    values = [float(p) for p in prices]
    return Decimal(str(median(values))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply_markup(cost: Decimal, markup_percent: float) -> Decimal:
    multiplier = Decimal("1") + (Decimal(str(markup_percent)) / Decimal("100"))
    return (cost * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _norm(value: str | None) -> str:
    return (value or "").casefold().strip()


def resolve_markup(
    default_percent: Decimal | float | int,
    rules: list[dict] | None,
    *,
    brand: str | None = None,
    category: str | None = None,
    kind: str | None = None,
) -> float:
    """First matching rule wins: brand, category (device_category), or offer kind."""
    hay = {
        "brand": _norm(brand),
        "category": _norm(category),
        "kind": _norm(kind),
    }
    for rule in rules or []:
        match = _norm(str(rule.get("match") or ""))
        needle = _norm(str(rule.get("value") or ""))
        if match not in hay or not needle or hay[match] != needle:
            continue
        try:
            return float(rule["percent"])
        except (KeyError, TypeError, ValueError):
            continue
    return float(default_percent)


def round_price(price: Decimal, round_to: int = 100) -> Decimal:
    if round_to <= 1:
        return price.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    step = Decimal(round_to)
    # Round to nearest step (e.g. 100)
    return (price / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step


def storefront_price(
    supplier_prices: list[Decimal | float | int],
    markup_percent: float,
    round_to: int = 100,
) -> tuple[Decimal | None, Decimal | None]:
    """Return (cost_median, storefront_price)."""
    cost = compute_median_cost(supplier_prices)
    if cost is None:
        return None, None
    priced = apply_markup(cost, markup_percent)
    return cost, round_price(priced, round_to)
