"""Telegram channel parser (MTProto via Telethon).

Parses text price lists from supplier channels on a schedule.
PDF/Excel extraction hooks are prepared; OCR is out of MVP scope.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from apps.worker.offer_identity import should_prepend_section

logger = logging.getLogger(__name__)

# Examples:
# 17 Pro Max 256GB Blue 🇯🇵 (E-Sim) - 102800
# 🇮🇳 17e 256GB Black    - 56 800
# Ray-Ban Wayfarer ... - 39.000₽
PRICE_LINE_RE = re.compile(
    r"^(?P<title>.+?)\s*[-–—/|:]\s*(?P<price>\d[\d\s.]{0,20}?)\s*(?:₽|руб\.?|р\.?)?\s*$",
    re.IGNORECASE,
)

HEADER_RE = re.compile(r"^(?:📦|📱|🎧|⌚️|💻)?\s*(?P<header>[A-Za-zА-Яа-я0-9].{2,80})$")


@dataclass
class ParsedLine:
    title: str
    price: Decimal
    raw: str
    section: str | None = None


def normalize_title(title: str) -> str:
    """Normalize product title for cross-supplier matching (legacy / slug helper)."""
    text = unicodedata.normalize("NFKC", title)
    cleaned = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("So") or cat.startswith("Sk"):
            continue
        cleaned.append(ch)
    text = "".join(cleaned)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def parse_price_token(raw: str) -> Decimal | None:
    token = raw.strip().replace(" ", "").replace("\u00a0", "")
    if not token:
        return None
    # phone numbers / chat ids
    if re.fullmatch(r"[78]\d{10}", token) or len(re.sub(r"\D", "", token)) > 8:
        return None
    # 39.000 / 39.500 → thousands separator when groups of 3
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", token):
        token = token.replace(".", "")
    elif token.count(".") == 1 and token.split(".")[1].isdigit() and len(token.split(".")[1]) == 3:
        token = token.replace(".", "")
    try:
        price = Decimal(token)
    except InvalidOperation:
        return None
    # Retail tech bounds (RUB) — hard floor applied later via settings
    if price < 500 or price > Decimal("5000000"):
        return None
    return price


def parse_price_text(text: str) -> list[ParsedLine]:
    results: list[ParsedLine] = []
    section: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or set(line) <= {"-", "—", "–", "=", "_", "•"}:
            continue

        match = PRICE_LINE_RE.match(line)
        if match:
            title = match.group("title").strip()
            title = re.sub(r"^[^\wА-Яа-я]+", "", title).strip()
            price = parse_price_token(match.group("price"))
            if price is None or not title:
                continue
            if re.match(r"^(от\s+)?\d+\s*шт", title, re.I):
                continue
            full_title = title
            if should_prepend_section(section, title):
                full_title = f"{section} {title}"
            results.append(ParsedLine(title=full_title, price=price, raw=line, section=section))
            continue

        # Section header without price (e.g. "📦 iPhone 17 Pro Max")
        if not re.search(r"\d{3,}", line):
            header = HEADER_RE.match(line)
            if header:
                section = re.sub(r"^[^\wА-Яа-я]+", "", header.group("header")).strip()
    return results


def _parse_proxy(proxy_url: str | None):
    if not proxy_url:
        return None

    parsed = urlparse(proxy_url)
    if not parsed.hostname or not parsed.port:
        logger.warning("Invalid TELEGRAM_PROXY, ignoring")
        return None
    scheme = (parsed.scheme or "socks5").lower().replace("socks5h", "socks5")
    logger.info("Proxy configured for Telegram: %s:%s", parsed.hostname, parsed.port)
    if parsed.username:
        return (
            scheme,
            parsed.hostname,
            parsed.port,
            True,
            parsed.username,
            parsed.password or "",
        )
    return (scheme, parsed.hostname, parsed.port)
