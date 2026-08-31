"""Storefront pricing: median of supplier offers + markup + rounding."""

from __future__ import annotations

from dataclasses import dataclass
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


# Modified z-score cutoff (Iglewicz/Hoaglin). Relative fallback when MAD is 0.
_OUTLIER_Z = Decimal("3.5")
_RELATIVE_CAP = Decimal("0.5")
PRICE_RECEIPT_KEY = "price_receipt"


@dataclass(frozen=True)
class StorefrontQuote:
    cost_median: Decimal | None
    price: Decimal | None
    accepted: tuple[Decimal, ...]
    quarantined: tuple[tuple[Decimal, str], ...]


def quarantine_outliers(
    prices: list[Decimal | float | int],
) -> tuple[list[Decimal], list[tuple[Decimal, str]]]:
    """Drop statistical outliers. Keep the whole cohort if it would become empty."""
    values = [Decimal(str(p)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for p in prices]
    if len(values) < 3:
        return values, []
    mid = compute_median_cost(values)
    if mid is None or mid <= 0:
        return values, []
    deviations = [abs(v - mid) for v in values]
    mad = compute_median_cost(deviations) or Decimal("0")
    kept: list[Decimal] = []
    dropped: list[tuple[Decimal, str]] = []
    for value in values:
        if mad == 0:
            far = abs(value - mid) / mid > _RELATIVE_CAP
        else:
            z = (Decimal("0.6745") * abs(value - mid)) / mad
            far = z > _OUTLIER_Z
        if far:
            dropped.append((value, "outlier"))
        else:
            kept.append(value)
    if not kept:
        return values, []
    return kept, dropped


def quote_storefront(
    supplier_prices: list[Decimal | float | int],
    markup_percent: float,
    round_to: int = 100,
) -> StorefrontQuote:
    kept, dropped = quarantine_outliers(supplier_prices)
    cost = compute_median_cost(kept)
    if cost is None:
        return StorefrontQuote(None, None, tuple(kept), tuple(dropped))
    priced = apply_markup(cost, markup_percent)
    return StorefrontQuote(
        cost,
        round_price(priced, round_to),
        tuple(kept),
        tuple(dropped),
    )


def receipt_payload(quote: StorefrontQuote, markup_percent: float, round_to: int) -> dict:
    return {
        "accepted_n": len(quote.accepted),
        "quarantined_n": len(quote.quarantined),
        "quarantined": [f"{price} ({reason})" for price, reason in quote.quarantined[:20]],
        "markup_percent": markup_percent,
        "round_to": round_to,
    }


def with_price_receipt(attrs: dict | None, receipt: dict) -> dict:
    out = dict(attrs or {})
    out[PRICE_RECEIPT_KEY] = receipt
    return out


def storefront_price(
    supplier_prices: list[Decimal | float | int],
    markup_percent: float,
    round_to: int = 100,
) -> tuple[Decimal | None, Decimal | None]:
    """Return (cost_median, storefront_price) after outlier quarantine."""
    quote = quote_storefront(supplier_prices, markup_percent, round_to)
    return quote.cost_median, quote.price
