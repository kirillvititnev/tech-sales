"""Telegram channel parser (MTProto via Telethon).

Parses text price lists from supplier channels on a schedule.
PDF/Excel attachments are converted to text in attachments.py, then this parser.
OCR of photos is out of MVP scope.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from apps.worker.offer_identity import is_junk_section, should_prepend_section

logger = logging.getLogger(__name__)

# Examples:
# 17 Pro Max 256GB Blue 🇯🇵 (E-Sim) - 102800
# 🇮🇳 17e 256GB Black    - 56 800
# Ray-Ban Wayfarer ... - 39.000₽
# Trailing region flag after price is common in Bests re:sale:
#   S23 Plus 8/512GB Black — 42.800 🇦🇪
_REGION_FLAG = r"[\U0001F1E6-\U0001F1FF]{2}"
PRICE_LINE_RE = re.compile(
    r"^(?P<title>.+?)\s*[-–—/|:]\s*(?P<price>\d[\d\s.]{0,20}?)\s*"
    r"(?:₽|руб\.?|р\.?)?\s*"
    rf"(?P<flag>{_REGION_FLAG})?\s*"
    r"(?:[xх×]\s*\d+)?\s*$",
    re.IGNORECASE,
)
# Global Market: "17 Pro Max 1TB Blue🇭🇰 148000" (flag glued to title, no dash)
PRICE_LINE_FLAG_SPACE_RE = re.compile(
    r"^(?P<title>.+?\d+\s*(?:GB|TB).*?)"
    rf"(?P<flag>{_REGION_FLAG}(?:{_REGION_FLAG})?)\s+"
    r"(?P<price>\d[\d\s.]{2,12})\s*"
    r"(?:₽|руб\.?|р\.?)?\s*$",
    re.IGNORECASE,
)

HEADER_RE = re.compile(
    r"^[^\wА-Яа-я]*?(?P<header>[A-Za-zА-Яа-я0-9].{1,80})$"
)
_YEAR_TOKEN_RE = re.compile(r"\b20\d{2}\b")
_FAMILY_SECTION_RE = re.compile(r"(?i)\b(iphone|ipad|macbook|airpods|apple\s*watch|watch)\b")
_SERIES_FRAGMENT_RE = re.compile(r"(?i)^(neo|air|pro|mini|max|ultra)$")


def _is_section_header_line(line: str) -> bool:
    """Allow product years and trailing colons (Global Market: `iPad 11 2025 Wi-Fi:`)."""
    if line.endswith(":"):
        return True
    without_years = _YEAR_TOKEN_RE.sub("", line)
    return not re.search(r"\d{3,}", without_years)


def _merge_section(previous: str | None, candidate: str) -> str:
    """`MacBook` + `Neo:` → `MacBook Neo` so RAM/color continuations still classify."""
    frag = re.sub(r"[:.\s]+$", "", candidate).strip()
    if previous and _SERIES_FRAGMENT_RE.fullmatch(frag):
        prev_clean = previous.rstrip(" :")
        if _FAMILY_SECTION_RE.search(prev_clean) and frag.lower() not in prev_clean.lower():
            return f"{prev_clean} {frag.title()}"
    return candidate


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

        match = PRICE_LINE_RE.match(line) or PRICE_LINE_FLAG_SPACE_RE.match(line)
        if match:
            title = match.group("title").strip()
            # Keep leading region flags (🇺🇸); only strip bullets / junk symbols
            title = re.sub(
                r"^(?:[^\wА-Яа-я\U0001F1E6-\U0001F1FF]+)+",
                "",
                title,
            ).strip()
            # Drop leading "Прайс" glued into the price line itself
            title = re.sub(r"(?i)^\s*прайс\s+", "", title).strip()
            # Bests-style flag after price → keep on title for region/SIM
            flag = match.group("flag")
            if flag and not re.search(r"[\U0001F1E6-\U0001F1FF]", title):
                title = f"{title} {flag}".strip()
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
        if _is_section_header_line(line):
            header = HEADER_RE.match(line)
            if header:
                candidate = re.sub(r"^[^\wА-Яа-я]+", "", header.group("header")).strip()
                # Never treat logistics / "Прайс …" banners as product sections
                if candidate and not is_junk_section(candidate):
                    section = _merge_section(section, candidate)
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
