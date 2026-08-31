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
_RECEIPT_LINE_CAP = 40


@dataclass(frozen=True)
class SupplierBid:
    """One supplier price that may enter the storefront median."""

    price: Decimal
    channel: str = ""


@dataclass(frozen=True)
class StorefrontQuote:
    cost_median: Decimal | None
    price: Decimal | None
    accepted: tuple[Decimal, ...]
    quarantined: tuple[tuple[Decimal, str], ...]
    accepted_bids: tuple[SupplierBid, ...] = ()
    quarantined_bids: tuple[tuple[SupplierBid, str], ...] = ()


def _as_bid(item: SupplierBid | Decimal | float | int) -> SupplierBid:
    if isinstance(item, SupplierBid):
        price = Decimal(str(item.price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return SupplierBid(price, (item.channel or "").strip())
    price = Decimal(str(item)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return SupplierBid(price, "")


def quarantine_outliers(
    prices: list[Decimal | float | int] | list[SupplierBid],
) -> tuple[list[Decimal], list[tuple[Decimal, str]]]:
    """Drop statistical outliers. Keep the whole cohort if it would become empty.

    Accepts bare prices or SupplierBid; returns bare Decimal lists for callers
    that only need the numbers (tests / storefront_price).
    """
    kept_bids, dropped_bids = quarantine_bids(prices)
    return (
        [b.price for b in kept_bids],
        [(b.price, reason) for b, reason in dropped_bids],
    )


def quarantine_bids(
    prices: list[Decimal | float | int] | list[SupplierBid],
) -> tuple[list[SupplierBid], list[tuple[SupplierBid, str]]]:
    """Drop statistical outliers while preserving channel labels."""
    bids = [_as_bid(p) for p in prices]
    if len(bids) < 3:
        return bids, []
    values = [b.price for b in bids]
    mid = compute_median_cost(values)
    if mid is None or mid <= 0:
        return bids, []
    deviations = [abs(v - mid) for v in values]
    mad = compute_median_cost(deviations) or Decimal("0")
    kept: list[SupplierBid] = []
    dropped: list[tuple[SupplierBid, str]] = []
    for bid in bids:
        if mad == 0:
            far = abs(bid.price - mid) / mid > _RELATIVE_CAP
        else:
            z = (Decimal("0.6745") * abs(bid.price - mid)) / mad
            far = z > _OUTLIER_Z
        if far:
            dropped.append((bid, "outlier"))
        else:
            kept.append(bid)
    if not kept:
        return bids, []
    return kept, dropped


def quote_storefront(
    supplier_prices: list[Decimal | float | int] | list[SupplierBid],
    markup_percent: float,
    round_to: int = 100,
) -> StorefrontQuote:
    kept_bids, dropped_bids = quarantine_bids(supplier_prices)
    kept = tuple(b.price for b in kept_bids)
    dropped = tuple((b.price, reason) for b, reason in dropped_bids)
    cost = compute_median_cost(list(kept))
    if cost is None:
        return StorefrontQuote(
            None,
            None,
            kept,
            dropped,
            tuple(kept_bids),
            tuple(dropped_bids),
        )
    priced = apply_markup(cost, markup_percent)
    return StorefrontQuote(
        cost,
        round_price(priced, round_to),
        kept,
        dropped,
        tuple(kept_bids),
        tuple(dropped_bids),
    )


def _fmt_bid_line(bid: SupplierBid) -> str:
    channel = bid.channel or "?"
    return f"{bid.price} · {channel}"


def receipt_payload(quote: StorefrontQuote, markup_percent: float, round_to: int) -> dict:
    accepted_bids = quote.accepted_bids or tuple(SupplierBid(p, "") for p in quote.accepted)
    quarantined_bids = quote.quarantined_bids or tuple(
        (SupplierBid(price, ""), reason) for price, reason in quote.quarantined
    )
    return {
        "accepted_n": len(accepted_bids),
        "quarantined_n": len(quarantined_bids),
        "accepted": [_fmt_bid_line(b) for b in accepted_bids[:_RECEIPT_LINE_CAP]],
        "quarantined": [
            f"{_fmt_bid_line(bid)} ({reason})"
            for bid, reason in quarantined_bids[:_RECEIPT_LINE_CAP]
        ],
        "markup_percent": markup_percent,
        "round_to": round_to,
    }


def with_price_receipt(attrs: dict | None, receipt: dict) -> dict:
    out = dict(attrs or {})
    out[PRICE_RECEIPT_KEY] = receipt
    return out


def storefront_price(
    supplier_prices: list[Decimal | float | int] | list[SupplierBid],
    markup_percent: float,
    round_to: int = 100,
) -> tuple[Decimal | None, Decimal | None]:
    """Return (cost_median, storefront_price) after outlier quarantine."""
    quote = quote_storefront(supplier_prices, markup_percent, round_to)
    return quote.cost_median, quote.price
