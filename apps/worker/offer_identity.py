"""Canonical offer identity: model / storage / color / SIM (no region)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

SimType = Literal["eSIM", "Sim+eSIM", "2Sim"]


class OfferKind(StrEnum):
    iphone = "iphone"
    apple_other = "apple_other"
    unknown = "unknown"


# Apple Support 118569 — iPhone 17 family eSIM-only purchase markets
ESIM_ONLY_17_REGIONS = frozenset(
    {
        "us",
        "usa",
        "united states",
        "usvi",
        "united states virgin islands",
        "ca",
        "canada",
        "mx",
        "mexico",
        "jp",
        "japan",
        "gu",
        "guam",
        "ae",
        "uae",
        "united arab emirates",
        "sa",
        "saudi",
        "saudi arabia",
        "bh",
        "bahrain",
        "kw",
        "kuwait",
        "qa",
        "qatar",
        "om",
        "oman",
    }
)

FLAG_TO_REGION: dict[str, str] = {
    "🇺🇸": "us",
    "🇨🇦": "ca",
    "🇲🇽": "mx",
    "🇯🇵": "jp",
    "🇬🇺": "gu",
    "🇦🇪": "ae",
    "🇸🇦": "sa",
    "🇧🇭": "bh",
    "🇰🇼": "kw",
    "🇶🇦": "qa",
    "🇴🇲": "om",
    "🇨🇳": "cn",
    "🇭🇰": "hk",
    "🇲🇴": "mo",
    "🇩🇪": "de",
    "🇪🇺": "eu",
    "🇮🇳": "in",
    "🇬🇧": "gb",
    "🇰🇷": "kr",
    "🇸🇬": "sg",
    "🇦🇺": "au",
}

REGION_TOKEN_RE = re.compile(
    r"\b(usa|usvi|us|canada|ca|mexico|mx|japan|jp|guam|gu|"
    r"uae|ae|saudi(?:\s+arabia)?|sa|bahrain|bh|kuwait|kw|qatar|qa|oman|om|"
    r"china|cn|hk|hong\s*kong|macao|macau|mo|eu|de|germany|uk|gb|in|india|"
    r"kr|korea|sg|singapore|au|australia)\b",
    re.I,
)

SIM_PATTERNS: list[tuple[re.Pattern[str], SimType]] = [
    (re.compile(r"\b(sim\s*\+\s*e[-\s]?sim|sim\s*\+\s*esim|nano\s*\+\s*e?sim)\b", re.I), "Sim+eSIM"),
    (re.compile(r"\b(dual\s*nano|2\s*[x×]?\s*sim|2sim|dual\s*sim|физическ|физ\.?\s*sim|physical[-\s]?only)\b", re.I), "2Sim"),
    (re.compile(r"\b(e[-\s]?sim|esim)\b", re.I), "eSIM"),
]

STORAGE_RE = re.compile(r"\b(\d+)\s*(tb|gb)\b", re.I)
COLOR_ALIASES = {
    "чёрный": "black",
    "черный": "black",
    "белый": "white",
    "синий": "blue",
    "голубой": "blue",
    "титан": "titanium",
    "натуральный": "natural",
    "desert": "desert",
    "space black": "space black",
    "space gray": "space gray",
    "space grey": "space gray",
}

IPHONE_MODEL_RE = re.compile(
    r"\b(?:iphone\s*)?(?P<body>"
    r"air|"
    r"1[4-7]\s*pro\s*max|"
    r"1[4-7]\s*pro|"
    r"1[4-7]\s*plus|"
    r"1[4-7]e|"
    r"1[4-7]"
    r")\b",
    re.I,
)

APPLE_OTHER_RE = re.compile(
    r"\b(ipad|macbook|imac|airpods|apple\s*watch|watch\s*ultra|pencil|airtag|"
    r"mac\s*mini|mac\s*studio|vision|magic\s*keyboard|magic\s*mouse)\b",
    re.I,
)

CONTINUATION_START_RE = re.compile(
    r"^(?:\d+\s*(?:gb|tb)\b|\(|e-?sim|sim\+|black|white|blue|titanium|natural)",
    re.I,
)

MARKETING_RE = re.compile(
    r"(акция|прайс\s+на|только\s+сегодня|whats?\s*app|telegram\s*@|доставка\s+по|"
    r"напишите\s+менеджер|курс\s+валют|наличие\s+уточн)",
    re.I,
)


@dataclass(frozen=True)
class OfferIdentity:
    kind: OfferKind
    model: str
    storage: str
    color: str
    sim: SimType | None
    region: str | None
    display_title: str
    identity_key: str
    publish: bool
    reject_reason: str | None = None


def _nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def strip_emoji(text: str) -> str:
    cleaned: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("So") or cat.startswith("Sk"):
            continue
        cleaned.append(ch)
    return "".join(cleaned)


def extract_region(title: str) -> str | None:
    for flag, region in FLAG_TO_REGION.items():
        if flag in title:
            return region
    match = REGION_TOKEN_RE.search(title)
    if not match:
        return None
    token = re.sub(r"\s+", " ", match.group(1).lower())
    aliases = {
        "usa": "us",
        "united states": "us",
        "usvi": "us",
        "canada": "ca",
        "mexico": "mx",
        "japan": "jp",
        "guam": "gu",
        "uae": "ae",
        "united arab emirates": "ae",
        "saudi": "sa",
        "saudi arabia": "sa",
        "bahrain": "bh",
        "kuwait": "kw",
        "qatar": "qa",
        "oman": "om",
        "china": "cn",
        "hong kong": "hk",
        "hongkong": "hk",
        "macao": "mo",
        "macau": "mo",
        "germany": "de",
        "uk": "gb",
        "india": "in",
        "korea": "kr",
        "singapore": "sg",
        "australia": "au",
    }
    return aliases.get(token, token)


def extract_sim_text(title: str) -> SimType | None:
    for pattern, sim in SIM_PATTERNS:
        if pattern.search(title):
            return sim
    return None


def extract_storage(title: str) -> str:
    match = STORAGE_RE.search(title)
    if not match:
        return ""
    return f"{match.group(1)}{match.group(2).upper()}"


def extract_color(title: str) -> str:
    lower = title.lower()
    for alias, canon in COLOR_ALIASES.items():
        if alias in lower:
            return canon
    # common latin color tokens near end
    m = re.search(
        r"\b(black|white|blue|natural|titanium|gold|silver|purple|green|pink|"
        r"yellow|ultramarine|sage|mist|cloud|starlight|midnight|desert)\b",
        lower,
    )
    return m.group(1) if m else ""


def normalize_iphone_model(title: str) -> str | None:
    m = IPHONE_MODEL_RE.search(title)
    if not m:
        return None
    body = re.sub(r"\s+", " ", m.group("body").strip().lower())
    body = body.replace("pro max", "pro max")
    if body == "air" or body.endswith(" air"):
        return "iphone air"
    if not body.startswith("iphone"):
        body = f"iphone {body}"
    return body


def should_prepend_section(section: str | None, title: str) -> bool:
    if not section:
        return False
    if section.lower() in title.lower():
        return False
    if IPHONE_MODEL_RE.search(title) or APPLE_OTHER_RE.search(title):
        return False
    return bool(CONTINUATION_START_RE.search(title.strip()) or not IPHONE_MODEL_RE.search(title))


def is_marketing_noise(title: str) -> bool:
    return bool(MARKETING_RE.search(title))


def _generation(model: str) -> int | None:
    m = re.search(r"iphone\s+(\d{2})", model)
    return int(m.group(1)) if m else None


def infer_sim(model: str, region: str | None, sim_text: SimType | None) -> SimType | None:
    if sim_text:
        return sim_text
    if model == "iphone air":
        return "eSIM"
    if region is None:
        return None

    region_l = region.lower()
    gen = _generation(model)
    is_17_family = gen == 17 or model.startswith("iphone 17")

    if region_l in {"cn", "china"}:
        if "17e" in model or model == "iphone air":
            return "eSIM"
        return "2Sim"

    if region_l in {"hk", "mo", "hong kong", "macao", "macau"}:
        if gen in {14, 15, 16, 17} or is_17_family:
            return "2Sim"

    if is_17_family or gen == 17:
        if region_l in ESIM_ONLY_17_REGIONS:
            return "eSIM"
        return "Sim+eSIM"

    if gen in {14, 15, 16}:
        if region_l in {"us", "usa", "usvi"}:
            return "eSIM"
        return "Sim+eSIM"

    return None


def build_display_title(model: str, storage: str, color: str, sim: SimType | None) -> str:
    parts = [model.title().replace("Iphone", "iPhone")]
    if storage:
        parts.append(storage)
    if color:
        parts.append(color.title())
    if sim:
        parts.append(sim)
    return " ".join(parts)


def identity_key(model: str, storage: str, color: str, sim: SimType | None) -> str:
    raw = "|".join([model.lower(), storage.lower(), color.lower(), (sim or "").lower()])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def classify_offer(title: str, *, section: str | None = None) -> OfferIdentity:
    working = title.strip()
    if should_prepend_section(section, working):
        working = f"{section} {working}".strip()

    region = extract_region(working)
    sim_text = extract_sim_text(working)
    storage = extract_storage(working)
    color = extract_color(working)

    iphone_model = normalize_iphone_model(working)
    if iphone_model:
        kind = OfferKind.iphone
        model = iphone_model
    else:
        other = APPLE_OTHER_RE.search(working)
        if other:
            kind = OfferKind.apple_other
            model = re.sub(r"\s+", " ", other.group(0).lower())
            cleaned = strip_emoji(_nfkc(working)).lower()
            cleaned = REGION_TOKEN_RE.sub(" ", cleaned)
            for pattern, _ in SIM_PATTERNS:
                cleaned = pattern.sub(" ", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            model = cleaned[:80] or model
        else:
            kind = OfferKind.unknown
            model = re.sub(r"\s+", " ", strip_emoji(_nfkc(working)).lower())[:80]

    if is_marketing_noise(working) or kind == OfferKind.unknown:
        return OfferIdentity(
            kind=kind,
            model=model,
            storage=storage,
            color=color,
            sim=None,
            region=region,
            display_title=working,
            identity_key="",
            publish=False,
            reject_reason="noise_or_unrecognized",
        )

    sim = infer_sim(model, region, sim_text) if kind == OfferKind.iphone else None
    if kind == OfferKind.iphone and sim is None:
        return OfferIdentity(
            kind=kind,
            model=model,
            storage=storage,
            color=color,
            sim=None,
            region=region,
            display_title=build_display_title(model, storage, color, None),
            identity_key="",
            publish=False,
            reject_reason="iphone_missing_sim",
        )

    display = build_display_title(model, storage, color, sim)
    key = identity_key(model, storage, color, sim)
    return OfferIdentity(
        kind=kind,
        model=model,
        storage=storage,
        color=color,
        sim=sim,
        region=region,
        display_title=display,
        identity_key=key,
        publish=True,
    )
