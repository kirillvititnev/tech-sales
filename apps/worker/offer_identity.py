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
    samsung = "samsung"
    sony = "sony"
    insta360 = "insta360"
    android = "android"
    gaming = "gaming"
    dyson = "dyson"
    yandex = "yandex"
    meta = "meta"
    audio = "audio"
    camera = "camera"
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
    "🇹🇼": "tw",
    "🇩🇪": "de",
    "🇪🇺": "eu",
    "🇮🇳": "in",
    "🇬🇧": "gb",
    "🇰🇷": "kr",
    "🇸🇬": "sg",
    "🇦🇺": "au",
    "🇲🇾": "my",
    "🇻🇳": "vn",
    "🇨🇱": "cl",
    "🇷🇺": "ru",
    "🇮🇩": "id",
}

REGION_TOKEN_RE = re.compile(
    r"\b(usa|usvi|us|canada|ca|mexico|mx|japan|jp|guam|gu|"
    r"uae|ae|saudi(?:\s+arabia)?|sa|bahrain|bh|kuwait|kw|qatar|qa|oman|om|"
    r"china|cn|hk|hong\s*kong|macao|macau|mo|taiwan|tw|eu|de|germany|uk|gb|in|india|"
    r"kr|korea|sg|singapore|au|australia|my|malaysia|vn|vietnam|cl|chile|ru|russia)\b",
    re.I,
)

SIM_PATTERNS: list[tuple[re.Pattern[str], SimType]] = [
    (re.compile(r"\b(sim\s*\+\s*e[-\s]?sim|sim\s*\+\s*esim|1\s*sim\s*\+?\s*e[-\s]?sim|sim\s*-\s*e[-\s]?sim|nano\s*-?\s*sim\s*\+\s*e?sim)\b", re.I), "Sim+eSIM"),
    (re.compile(r"\b(dual\s*nano|2\s*[x×]?\s*sim|2sim|dual\s*sim|физическ|физ\.?\s*sim|physical[-\s]?only)\b", re.I), "2Sim"),
    (re.compile(r"\b(e[-\s]?sim|esim)\b", re.I), "eSIM"),
]

STORAGE_RE = re.compile(r"\b(\d+)\s*(tb|gb)\b", re.I)
# Top re:sale Samsung lines: "S25 Ultra 12/256 Black"
RAM_STORAGE_RE = re.compile(r"\b(\d{1,2})\s*/\s*(\d+)\s*(tb|gb)?\b", re.I)
# Leftover after partial RAM/storage strip: "16/" or "24/"
RAM_ORPHAN_SLASH_RE = re.compile(r"\b\d{1,2}\s*/\s*(?=\s|$|[A-Za-zА-Яа-я])")
# iMac / MacBook GPU tuples: (10/10/16/256) or 10c CPU/16c GPU/16/512
CPU_GPU_TUPLE_RE = re.compile(
    r"\(?\s*\d{1,2}\s*(?:c\s*)?(?:cpu)?\s*/\s*\d{1,2}\s*(?:c\s*)?(?:gpu)?\s*/\s*\d{1,2}\s*/\s*\d+\s*(?:tb|gb)?\s*\)?",
    re.I,
)
# Unisale multipart headers: "(часть 1/2)" / "часть 2/2"
PART_MARKER_RE = re.compile(r"\(?\s*часть\s*\d+\s*/\s*\d+\s*\)?", re.I)
# Marketing / noise tokens that must never stay in device_name
APPLE_NAME_JUNK_RE = re.compile(
    r"(?i)\b("
    r"новые|обменки|актив|оригинал(?:ьные|ьный|ые)?|кабел[ьяи]|кабель|"
    r"lightning|type[\s\-]?c|прайс|часть"
    r")\b",
)
# Supplier prices glued into the line without a dash: "MDVD4 133.000" / "103 000"
EMBEDDED_PRICE_RE = re.compile(r"\b\d{1,3}(?:[.\s]\d{3}){1,2}\b")

# Android / non-Apple phones — never classify as iPhone via bare "16" in "16/512"
NON_APPLE_PHONE_RE = re.compile(
    r"(?i)\b("
    r"samsung|galaxy|oneplus|one\s*plus|xiaomi|redmi|poco|honor|huawei|"
    r"nothing(?:\s*phone)?|pixel|realme|oppo|vivo|motorola|moto|iqoo|tecno|"
    r"infinix|asus|nokia|"
    r"z\s*fold|z\s*flip|tab\s*s\d+|galaxy\s*tab|\btab\b|sm-[a-z0-9]+"
    r")\b",
)

COLOR_ALIASES = {
    "чёрный": "Black",
    "черный": "Black",
    "белый": "White",
    "синий": "Blue",
    "голубой": "Blue",
    "зелёный": "Green",
    "зеленый": "Green",
    "розовый": "Pink",
    "фиолетовый": "Purple",
    "серый": "Gray",
    "лиловый": "Lilac",
    "оранжевый": "Orange",
    "малиновый": "Raspberry",
    "красный": "Red",
    "бежевый": "Beige",
    "коричневый": "Brown",
    "титан": "Titanium",
    "натуральный": "Natural",
    "бирюзовый": "Teal",
    "бирюза": "Teal",
    "desert": "Desert Titanium",
    "deep blue": "Deep Blue",
    "mist blue": "Mist Blue",
    "sky blue": "Sky Blue",
    "space black": "Space Black",
    "cloud white": "Cloud White",
    "light gold": "Light Gold",
    "space gray": "Space Gray",
    "space grey": "Space Gray",
    "icyblue": "Icy Blue",
    "icy blue": "Icy Blue",
    "titanium black": "Titanium Black",
    "titanium gray": "Titanium Gray",
    "titanium grey": "Titanium Gray",
    "black titanium": "Black Titanium",
    "natural titanium": "Natural Titanium",
    "white titanium": "White Titanium",
    "desert titanium": "Desert Titanium",
    "cobalt violet": "Cobalt Violet",
    "rose gold": "Rose Gold",
    "ultramarine": "Ultramarine",
    "starlight": "Starlight",
    "midnight": "Midnight",
    "grey": "Gray",
    "gray": "Gray",
    "blush": "Blush",
    "indigo": "Indigo",
    "citrus": "Citrus",
    "camo": "Camo",
    "cosmic orange": "Cosmic Orange",
    "soft pink": "Soft Pink",
    "sage": "Sage",
    "lavender": "Lavender",
    "lavander": "Lavender",
    "olive": "Olive",
    "graphite": "Graphite",
    "peach pink": "Peach Pink",
    "light gray": "Light Gray",
    "light grey": "Light Gray",
    "lightgray": "Light Gray",
    "lightgrey": "Light Gray",
    "golden white": "Golden White",
    "porcelain": "Porcelain",
    "terracotta": "Terracotta",
    "beige": "Beige",
    "brown": "Brown",
    "lilac": "Lilac",
    "charcoal": "Charcoal",
    "navy": "Navy",
    "graygreen": "Graygreen",
    "gray green": "Graygreen",
    "grey green": "Graygreen",
    # Samsung OEM finishes (Z Fold / Z Flip / S25 FE)
    "jetblack": "Jet Black",
    "jet black": "Jet Black",
    "pistachio": "Pistachio",
    # Huawei OEM (Nova 15 Max Lake Cyan; Pura 90s Pro Guava Soda)
    "lake cyan": "Lake Cyan",
    "guava soda": "Guava Soda",
    # Fujifilm Instax
    "chalk white": "Chalk White",
    # OnePlus 15 OEM (global: Sand Storm)
    "sand storm": "Sand Storm",
    "sandstorm": "Sand Storm",
    # OnePlus Buds Pro 3 OEM
    "lunar radiance": "Lunar Radiance",
    "midnight opus": "Midnight Opus",
    # Audio OEM / special editions (JBL, Beats, Bose)
    "sand": "Sand",
    "squad": "Squad",
    "funky": "Funky Black",
    "funky black": "Funky Black",
    "mustard": "Mustard",
    "quick sand": "Quick Sand",
    "sandstone": "Sandstone",
    "deep plum": "Deep Plum",
    "driftwood sand": "Driftwood Sand",
    "kim kardashian dune": "Kim Kardashian Dune",
    "kim kardashian moon": "Kim Kardashian Moon",
    "tan": "Tan",
    # Samsung A-series OEM
    "awesome lime": "Awesome Lime",
    "lime": "Lime",
    # Pixel 7a / Galaxy Tab OEM
    "coral": "Coral",
    "coralred": "Coral",
    "coraled": "Coral",
    "coral red": "Coral",
    "coral pink": "Coral",
    "coralpink": "Coral",
    # Bang & Olufsen / Bowers & Wilkins OEM finishes
    "chestnut": "Chestnut",
    "anthracite": "Anthracite",
    "dark forest": "Dark Forest",
    "royal burgundy": "Royal Burgundy",
    # OnePlus Buds 4 OEM
    "storm gray": "Storm Gray",
    "storm grey": "Storm Gray",
    "zen green": "Zen Green",
    # Realme / Huawei Unisale finishes
    "glacier blue": "Glacier Blue",
    "blaze purple": "Blaze Purple",
    "blush gold": "Blush Gold",
    "graphite black": "Graphite Black",
    "orange ocean": "Orange Ocean",
    "blueblack": "Blueblack",
    "blue black": "Blueblack",
    "iceblue": "Iceblue",
    "ice blue": "Iceblue",
    "whitesilver": "Whitesilver",
    "white silver": "Whitesilver",
    "bay": "Bay",
    "cyan": "Cyan",
}

# Multi-word colors first (Deep Blue must not collapse to Blue)
COLOR_MULTI_RE = re.compile(
    r"(?i)\b("
    r"deep\s+blue|mist\s+blue|sky\s+blue|icy\s+blue|"
    r"cosmic\s+orange|soft\s+pink|peach\s+pink|"
    r"cloud\s+white|light\s+gold|golden\s+white|chalk\s+white|"
    r"light\s+gr[ae]y|gr[ae]y\s+green|"
    r"space\s+black|space\s+gr[ae]y|jet\s+black|"
    r"rose\s+gold|cobalt\s+violet|"
    r"lake\s+cyan|guava\s+soda|sand\s+storm|"
    r"lunar\s+radiance|midnight\s+opus|"
    r"quick\s+sand|deep\s+plum|driftwood\s+sand|"
    r"kim\s+kardashian\s+dune|kim\s+kardashian\s+moon|"
    r"awesome\s+lime|dark\s+forest|royal\s+burgundy|"
    r"storm\s+gr[ae]y|zen\s+green|glacier\s+blue|"
    r"blaze\s+purple|blush\s+gold|graphite\s+black|orange\s+ocean|"
    r"blue\s*black|ice\s*blue|white\s*silver|"
    r"black\s+titanium|natural\s+titanium|white\s+titanium|desert\s+titanium|"
    r"blue\s+titanium|"
    r"titanium\s+black|titanium\s+gr[ae]y|"
    r"desert(?!\s+titanium)"  # bare Desert on Pro lines → Desert Titanium via alias
    r")\b",
)

COLOR_SINGLE_RE = re.compile(
    r"(?i)\b("
    r"black|white|blue|natural|titanium|gold|silver|purple|green|pink|red|"
    r"yellow|ultramarine|sage|mist|starlight|midnight|desert|mint|navy|"
    r"gray|grey|violet|lavender|teal|orange|cream|obsidian|blush|indigo|citrus|camo|"
    r"olive|graphite|porcelain|terracotta|beige|brown|lilac|charcoal|graygreen|"
    r"jetblack|pistachio|sandstorm|sand|squad|funky|mustard|sandstone|tan|"
    r"coral|chestnut|anthracite|lime|bay|cyan|blueblack|iceblue|whitesilver"
    r")\b",
)

ASIS_RE = re.compile(r"(?i)\basis\+?|\(\s*asis\+?\s*\)")


# Official-ish capacity matrices (reject impossible SKUs)
IPHONE_STORAGE_ALLOWED: dict[str, frozenset[str]] = {
    "iphone 12": frozenset({"64GB", "128GB", "256GB"}),
    "iphone 12 mini": frozenset({"64GB", "128GB", "256GB"}),
    "iphone 12 pro": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 12 pro max": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 13": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 13 mini": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 13 pro": frozenset({"128GB", "256GB", "512GB", "1TB"}),
    "iphone 13 pro max": frozenset({"128GB", "256GB", "512GB", "1TB"}),
    "iphone 14": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 14 plus": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 14 pro": frozenset({"128GB", "256GB", "512GB", "1TB"}),
    "iphone 14 pro max": frozenset({"128GB", "256GB", "512GB", "1TB"}),
    "iphone 15": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 15 plus": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 15 pro": frozenset({"128GB", "256GB", "512GB", "1TB"}),
    "iphone 15 pro max": frozenset({"128GB", "256GB", "512GB", "1TB"}),
    "iphone 16": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 16 plus": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 16e": frozenset({"128GB", "256GB", "512GB"}),
    "iphone 16 pro": frozenset({"128GB", "256GB", "512GB", "1TB"}),
    "iphone 16 pro max": frozenset({"128GB", "256GB", "512GB", "1TB"}),
    "iphone 17": frozenset({"256GB", "512GB"}),
    "iphone 17 plus": frozenset({"256GB", "512GB"}),
    "iphone 17e": frozenset({"256GB", "512GB"}),
    "iphone 17 pro": frozenset({"256GB", "512GB", "1TB", "2TB"}),
    "iphone 17 pro max": frozenset({"256GB", "512GB", "1TB", "2TB"}),
    "iphone air": frozenset({"256GB", "512GB", "1TB"}),
}


# Explicit "iPhone …" (incl. Air). Bare "Air" is NOT an iPhone (Fitbit Air, Power Bank Air…).
IPHONE_EXPLICIT_RE = re.compile(
    r"\biphone\s+(?P<body>"
    r"17\s*air|"
    r"air|"
    r"1[2-7]\s*pro\s*max|"
    r"1[2-7]\s*pro|"
    r"1[2-7]\s*plus|"
    r"1[2-7]\s*mini|"
    r"1[2-7]e|"
    r"1[2-7]"
    r")\b",
    re.I,
)

# Top re:sale shorthand: "16 Pro 256GB Black" / "17e 256GB" / "17 Air 1TB" — requires storage nearby.
# Never match clock times like "14:00". Bare "Air" alone is NOT an iPhone.
IPHONE_BARE_RE = re.compile(
    r"(?<![:\d])\b(?P<body>"
    r"17\s*air|"
    r"1[2-7]\s*pro\s*max|"
    r"1[2-7]\s*pro|"
    r"1[2-7]\s*plus|"
    r"1[2-7]\s*mini|"
    r"1[2-7]e|"
    r"1[2-7]"
    r")\b(?!\s*:)",
    re.I,
)

# Used for section-glue detection (keep permissive for "📦 iPhone 17 Pro Max" headers)
IPHONE_MODEL_RE = re.compile(
    r"\b(?:iphone\s+)?(?P<body>"
    r"17\s*air|"
    r"air|"
    r"1[2-7]\s*pro\s*max|"
    r"1[2-7]\s*pro|"
    r"1[2-7]\s*plus|"
    r"1[2-7]\s*mini|"
    r"1[2-7]e|"
    r"1[2-7]"
    r")\b",
    re.I,
)

# Adequacy floors (RUB, supplier cost before markup)
MIN_PRICE_IPHONE = 35000
MIN_PRICE_SAMSUNG = 8000
MIN_PRICE_APPLE_OTHER = 2500
MIN_PRICE_ANDROID = 8000
MIN_PRICE_GAMING = 5000
MIN_PRICE_DYSON = 8000
MIN_PRICE_YANDEX = 3000
MIN_PRICE_META = 5000
MIN_PRICE_AUDIO = 2000
MIN_PRICE_CAMERA = 8000


APPLE_OTHER_RE = re.compile(
    r"\b(ipad|macbook|imac|airpods|apple\s*watch|watch\s*ultra|pencil|airtag|"
    r"mac\s*mini|mac\s*studio|vision|magic\s*keyboard|magic\s*mouse|"
    r"magsafe|usb-?c\s*cable|power\s*adapter|apple\s*tv|"
    r"lightning\s*digital(?:\s*av)?\s*adapter)\b",
    re.I,
)

# Bests/Unisale: optional leading Apple order code; optional color between size and Mx
MACBOOK_BARE_RE = re.compile(
    r"(?i)\b(?:(?P<code>[A-Z0-9]{5})\s+)?"
    r"(?:macbook\s+)?(?P<series>pro|air)\s+(?P<size>1[3-6])\s+"
    r"(?:(?P<mid>(?:(?!m\d+\b)[A-Za-z][\w]*)(?:\s+(?!m\d+\b)[A-Za-z][\w]*)*)\s+)?"
    r"m(?P<chip>\d+)(?:\s+(?P<tier>pro|max|ultra))?\b|"
    r"\b(?:(?P<code_neo>[A-Z0-9]{5})\s+)?(?:macbook\s+)?neo\s+(?P<year>20\d{2})\b",
)

GALAXY_MODEL_RE = re.compile(
    r"(?i)\b(?:galaxy\s+)?(?P<body>"
    r"s(?:2[3-9]|3[0-9])(?:\s*(?:\+|plus|ultra|fe))?|"
    r"z\s*fold\s*\d+(?:\s*(?:ultra|plus))?|"
    r"z\s*flip\s*\d+(?:\s*(?:ultra|plus))?|"
    r"a(?:0[5-9]|[1-9]\d)(?:\s*5g)?"  # A05–A99 (A07 / A16 / A17 / A26 / A56…)
    r")(?!\w)",  # allow trailing '+' (S23+); \b breaks on '+'
)

# token → (brand, device_category_ru, name_prefix)
APPLE_OTHER_META: dict[str, tuple[str, str, str]] = {
    "ipad": ("Apple", "Планшеты", "iPad"),
    "macbook": ("Apple", "Ноутбуки", "MacBook"),
    "imac": ("Apple", "Компьютеры", "iMac"),
    "airpods": ("Apple", "Наушники", "AirPods"),
    "apple watch": ("Apple", "Часы", "Apple Watch"),
    "watch ultra": ("Apple", "Часы", "Apple Watch Ultra"),
    "pencil": ("Apple", "Аксессуары", "Apple Pencil"),
    "airtag": ("Apple", "Аксессуары", "AirTag"),
    "mac mini": ("Apple", "Компьютеры", "Mac mini"),
    "mac studio": ("Apple", "Компьютеры", "Mac Studio"),
    "vision": ("Apple", "XR", "Vision"),
    "magic keyboard": ("Apple", "Аксессуары", "Magic Keyboard"),
    "magic mouse": ("Apple", "Аксессуары", "Magic Mouse"),
    "magsafe": ("Apple", "Аксессуары", "MagSafe"),
    "usb-c cable": ("Apple", "Аксессуары", "USB-C Cable"),
    "usbc cable": ("Apple", "Аксессуары", "USB-C Cable"),
    "power adapter": ("Apple", "Аксессуары", "Power Adapter"),
    "apple tv": ("Apple", "ТВ", "Apple TV"),
    "lightning digital av adapter": ("Apple", "Аксессуары", "Lightning Digital AV Adapter"),
    "lightning digital adapter": ("Apple", "Аксессуары", "Lightning Digital AV Adapter"),
}


CONTINUATION_START_RE = re.compile(
    r"^(?:\d{1,2}\s*/\s*\d+\s*(?:gb|tb)\b|\d+\s*(?:gb|tb)\b|\(|e-?sim|sim\+|black|white|blue|titanium|natural)",
    re.I,
)

MARKETING_RE = re.compile(
    r"(акция|прайс\s+на|только\s+сегодня|whats?\s*app|telegram\s*@|доставка\s+по|"
    r"напишите\s+менеджер|курс\s+валют|наличие\s+уточн)",
    re.I,
)

# Lots, dummies, warranty blurbs, used-device footers — not sellable SKUs
JUNK_RE = re.compile(
    r"(?i)("
    r"\bлот\b|"
    r"\bмини\s*-?\s*лот\b|"
    r"\bмуляж|"
    r"\bdummy\b|"
    r"\bгарантия\b|"
    r"\bб/?у\b|"
    r"\bused\b|"
    r"\bвитрин|"
    r"\bуценк|"
    r"\bрассрочк|"
    r"\bпредзаказ\b|"
    r"\bпод\s*заказ\b|"
    r"\bfitbit\b"
    r")"
)

CENA_SUFFIX_RE = re.compile(r"(?i)\s*цена\s*$")

# Logistics / price-list banners that suppliers put as section headers (not product names).
# Gold sample channel: Top re:sale — sections are model lines like "IPhone 16:", never this junk.
SECTION_JUNK_RE = re.compile(
    r"(?i)^(?:"
    r"прайс\b|"
    r"выдача\b|"
    r"доставка\b|"
    r"самовывоз\b|"
    r"(?:в\s+)?наличи[еи]\b|"
    r"акция\b|"
    r"важно\b|"
    r"внимание\b|"
    r"условия\b|"
    r"оплата\b|"
    r"asis\+?|"
    r"non\s*active|"
    r"без\s*коробк|"
    r"уценк|"
    r"витрин"
    r")",
)

# Phrases glued into titles that must never reach the storefront
NOISE_PHRASE_RE = re.compile(
    r"(?i)(?:"
    r"выдача\s+в\s+день\s+заказа(?:\s+или\s+на\s+следующий\s+день)?(?:\s+до\s+\d{1,2}:\d{2})?[!\uFE0F️\s]*|"
    r"выдача\s+в\s+день(?:\s+заказа)?[!\uFE0F️\s]*|"
    r"на\s+следующий\s+день\s+до\s+\d{1,2}:\d{2}[!\uFE0F️\s]*|"
    r"^\s*в\s+наличии\s+|"
    r"^\s*прайс\s+(?:на\s+)?|"
    r"\bпрайс\s+(?=galaxy|samsung|iphone|apple|oneplus|honor|huawei|xiaomi|pixel)|"
    r"asis\+?\s*(?:non\s*active)?\s*(?:без\s*коробки)?\s*|"
    r"non\s*active\s*(?:без\s*коробки)?\s*|"
    r"\(\s*asis\+?\s*\)|"
    r"без\s*коробки\s*"
    r")",
)

# Model-like section headers worth gluing (Top re:sale style: "IPhone 16:", "AirPods")
MODEL_SECTION_RE = re.compile(
    r"(?i)\b("
    r"iphone|ipad|macbook|airpods|imac|watch|mac\s*mini|mac\s*studio|vision|"
    r"galaxy|samsung|\bs\d{2}|pixel|xiaomi|redmi|poco|honor|huawei|oneplus|"
    r"dyson|playstation|ps\s*[45]|ray-?ban|insta\s*360|insta360|"
    r"яндекс|yandex|xbox|nintendo|oculus|logitech|steam|"
    r"buds|airwrap|supersonic|airstrait|"
    r"hd\d+|hs\d+|galaxy\s*watch|watch\s*8|\bneo\b"
    r")\b",
)

@dataclass(frozen=True)
class OfferIdentity:
    kind: OfferKind
    brand: str
    device_category: str
    device_name: str
    model: str
    storage: str
    color: str
    sim: SimType | None
    region: str | None
    ram: str
    config: str
    display_title: str
    identity_key: str
    publish: bool
    band: str = ""
    model_code: str = ""
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
    ram, storage = _ram_and_storage(title)
    if storage:
        return storage
    match = STORAGE_RE.search(title)
    if not match:
        return ""
    return f"{match.group(1)}{match.group(2).upper()}"


def extract_ram(title: str) -> str:
    ram, _storage = _ram_and_storage(title)
    return ram


def _ram_and_storage(title: str) -> tuple[str, str]:
    """Phone-style 12/256 — not Mac GPU cores like 10/10 or 16/40."""
    ram_m = RAM_STORAGE_RE.search(title)
    if not ram_m:
        return "", ""
    ram_n = int(ram_m.group(1))
    size_n = int(ram_m.group(2))
    unit = (ram_m.group(3) or "GB").upper()
    if unit == "TB":
        size_n_gb = size_n * 1024
    else:
        size_n_gb = size_n
    if 4 <= ram_n <= 128 and size_n_gb >= 64:
        return f"{ram_n}GB", f"{size_n}{unit}"
    return "", ""


def extract_color(title: str) -> str:
    lower = title.lower()
    multi = COLOR_MULTI_RE.search(title)
    if multi:
        key = re.sub(r"\s+", " ", multi.group(1).lower())
        return COLOR_ALIASES.get(key, multi.group(1).title())
    for alias in sorted(COLOR_ALIASES.keys(), key=len, reverse=True):
        if " " in alias and alias in lower:
            return COLOR_ALIASES[alias]
    for alias in sorted(COLOR_ALIASES.keys(), key=len, reverse=True):
        if " " not in alias and re.search(rf"\b{re.escape(alias)}\b", lower):
            return COLOR_ALIASES[alias]
    single = COLOR_SINGLE_RE.search(title)
    if single:
        token = single.group(1).lower()
        return COLOR_ALIASES.get(token, token.title())
    return ""


def normalize_pro_titanium_color(model: str, color: str) -> str:
    """Pro / Pro Max finishes by generation.

    iPhone 17 Pro/Pro Max (aluminum): Silver, Cosmic Orange, Deep Blue.
    iPhone 14–16 Pro: * Titanium.
    """
    if not color:
        return color
    if "pro" not in model.lower():
        return color
    gen = _generation(model)
    key = re.sub(r"\s+", " ", color.lower()).strip()

    # Official iPhone 17 Pro / Pro Max — no Titanium finishes
    if gen == 17:
        mapping_17 = {
            "silver": "Silver",
            "white": "Silver",
            "white titanium": "Silver",
            "orange": "Cosmic Orange",
            "cosmic orange": "Cosmic Orange",
            "blue": "Deep Blue",
            "deep blue": "Deep Blue",
            "blue titanium": "Deep Blue",
        }
        if key in mapping_17:
            return mapping_17[key]
        # Legacy Pro colors that do not exist on 17 Pro
        if key in {
            "black",
            "black titanium",
            "natural",
            "natural titanium",
            "desert",
            "desert titanium",
        }:
            return ""
        return color

    if "titanium" in key:
        return color
    mapping = {
        "black": "Black Titanium",
        "white": "White Titanium",
        "natural": "Natural Titanium",
        "blue": "Blue Titanium",
        "desert": "Desert Titanium",
        "desert titanium": "Desert Titanium",
    }
    return mapping.get(key, color)


def normalize_air_color(model: str, color: str) -> str:
    """iPhone Air official: Sky Blue, Light Gold, Cloud White, Space Black."""
    if not color or model.lower() != "iphone air":
        return color
    key = re.sub(r"\s+", " ", color.lower()).strip()
    mapping = {
        "white": "Cloud White",
        "cloud white": "Cloud White",
        "cloud": "Cloud White",
        "gold": "Light Gold",
        "light gold": "Light Gold",
        "blue": "Sky Blue",
        "sky blue": "Sky Blue",
        "black": "Space Black",
        "space black": "Space Black",
    }
    if key in mapping:
        return mapping[key]
    return ""


def detect_asis(title: str) -> bool:
    return bool(ASIS_RE.search(title))


def asis_tier(title: str) -> str | None:
    """Return 'asis+' | 'asis' | None."""
    if re.search(r"(?i)asis\+", title):
        return "asis+"
    # iPro / suppliers: «запак» = ASIS+ (opened / reboxed)
    if re.search(r"(?i)\bзапак", title):
        return "asis+"
    if ASIS_RE.search(title):
        return "asis"
    return None


def category_for_phone(*, asis_tier_name: str | None) -> str:
    if asis_tier_name == "asis+":
        return "Смартфоны ASIS+"
    if asis_tier_name == "asis":
        return "Смартфоны ASIS"
    return "Смартфоны"


def category_for_headphones(*, asis_tier_name: str | None) -> str:
    if asis_tier_name == "asis+":
        return "Наушники ASIS+"
    if asis_tier_name == "asis":
        return "Наушники ASIS"
    return "Наушники"


def normalize_iphone_model(title: str) -> str | None:
    """Resolve iPhone model. Bare 'Air' / '14:00' / Android '16/512' must NEVER become iPhone."""
    if re.search(r"(?i)\bipad\b", title):
        return None
    if NON_APPLE_PHONE_RE.search(title) and not re.search(r"\biphone\b", title, re.I):
        return None

    scrubbed = re.sub(r"\b([01]?\d|2[0-3]):[0-5]\d\b", " ", title)

    explicit = IPHONE_EXPLICIT_RE.search(scrubbed)
    if explicit:
        return _iphone_body_to_model(explicit.group("body"))

    if not STORAGE_RE.search(scrubbed) and not RAM_STORAGE_RE.search(scrubbed):
        return None
    bare = IPHONE_BARE_RE.search(scrubbed)
    if not bare:
        return None
    body = bare.group("body").strip()
    # "16/512" / "16/1TB" — first number is RAM, not iPhone 16
    if re.fullmatch(r"1[2-7]", body) and re.search(rf"\b{body}\s*/\s*\d+", scrubbed):
        return None
    if re.fullmatch(r"1[2-7]", body) and not re.match(
        r"\s+\d+\s*(gb|tb)\b", scrubbed[bare.end() :], re.I
    ):
        return None
    return _iphone_body_to_model(body)


def _iphone_body_to_model(body: str) -> str:
    body = re.sub(r"\s+", " ", body.strip().lower())
    if body in {"air", "17 air", "17air"} or body.endswith(" air"):
        return "iphone air"
    if not body.startswith("iphone"):
        body = f"iphone {body}"
    return body


def is_allowed_iphone_storage(model: str, storage: str) -> bool:
    if not storage:
        return False
    allowed = IPHONE_STORAGE_ALLOWED.get(model.lower())
    if allowed is None:
        return storage in {"128GB", "256GB", "512GB", "1TB", "2TB"}
    return storage in allowed


def min_price_for_kind(kind: OfferKind) -> int:
    if kind == OfferKind.iphone:
        return MIN_PRICE_IPHONE
    if kind == OfferKind.samsung:
        return MIN_PRICE_SAMSUNG
    if kind == OfferKind.apple_other:
        return MIN_PRICE_APPLE_OTHER
    if kind == OfferKind.sony:
        return 2000
    if kind == OfferKind.insta360:
        return 5000
    if kind == OfferKind.android:
        return MIN_PRICE_ANDROID
    if kind == OfferKind.gaming:
        return MIN_PRICE_GAMING
    if kind == OfferKind.dyson:
        return MIN_PRICE_DYSON
    if kind == OfferKind.yandex:
        return MIN_PRICE_YANDEX
    if kind == OfferKind.meta:
        return MIN_PRICE_META
    if kind == OfferKind.audio:
        return MIN_PRICE_AUDIO
    if kind == OfferKind.camera:
        return MIN_PRICE_CAMERA
    return 6000


def normalize_galaxy_model(title: str) -> str | None:
    m = GALAXY_MODEL_RE.search(title)
    if not m:
        return None
    body = re.sub(r"\s+", " ", m.group("body").strip().lower())
    # S26+ / S26 plus → s26 plus (display: Galaxy S26 Plus)
    body = re.sub(r"(s\d+)\s*(?:\+|plus)(?!\w)", r"\1 plus", body)
    body = re.sub(r"\s+", " ", body).strip()
    body = re.sub(r"(s\d+)\s+ultra", r"\1 ultra", body)
    body = re.sub(r"(s\d+)\s+fe\b", r"\1 fe", body)
    # Unisale: "z fold8" / "z fold 8" → fold8 (display Galaxy Z Fold8)
    body = re.sub(r"\b(z)\s*(fold|flip)\s*(\d+)", r"\1 \2\3", body)
    # Galaxy A-series: don't confuse with iPad A16 / MacBook NEO A18; bare "A17" needs RAM/storage
    if re.fullmatch(r"a\d{2}(?:\s*5g)?", body):
        if re.search(r"(?i)\b(ipad|macbook|iphone|imac|airpods)\b", title):
            return None
        if not re.search(r"(?i)\bgalaxy\s+a\d{2}\b", title) and not RAM_STORAGE_RE.search(title):
            return None
    return f"galaxy {body}"


def format_device_name(model: str) -> str:
    name = model.strip()
    if name.startswith("iphone"):
        # title() turns 16e/17e into 16E/17E; Apple uses lowercase e
        formatted = name.title().replace("Iphone", "iPhone")
        return re.sub(r"(\d{2})E\b", r"\1e", formatted)
    if name.startswith("galaxy"):
        # galaxy s25 ultra → Galaxy S25 Ultra; galaxy a17 → Galaxy A17
        parts = name.split()
        out: list[str] = []
        for i, part in enumerate(parts):
            if i == 0:
                out.append("Galaxy")
            elif re.fullmatch(r"s\d+\+", part, re.I):
                out.append(f"{part[:-1].upper()} Plus")
            elif re.fullmatch(r"s\d+", part, re.I):
                out.append(part.upper())
            elif re.fullmatch(r"a\d{2}(?:5g)?", part, re.I):
                out.append(part.upper())
            elif part.lower() == "fe":
                out.append("FE")
            elif re.fullmatch(r"fold\d+", part, re.I):
                out.append(f"Fold{part[4:]}")
            elif re.fullmatch(r"flip\d+", part, re.I):
                out.append(f"Flip{part[4:]}")
            else:
                out.append(part.title())
        return " ".join(out)
    return name.title()


def normalize_galaxy_a_color(model: str, color: str) -> str:
    """Map supplier A-series shorthand to official-ish finishes."""
    if not color or not model.lower().startswith("galaxy a"):
        return color
    key = re.sub(r"\s+", " ", color.lower()).strip()
    if key == "grey":
        key = "gray"
    m = re.search(r"galaxy\s+(a\d{2})", model.lower())
    series = m.group(1) if m else ""

    if series == "a26":
        mapping = {
            "black": "Black",
            "white": "White",
            "mint": "Mint",
            "pink": "Peach Pink",
            "peach pink": "Peach Pink",
            "blue": "Blue",  # some regions / supplier listings
        }
        return mapping.get(key, color)

    if series == "a56":
        mapping = {
            "graphite": "Awesome Graphite",
            "awesome graphite": "Awesome Graphite",
            "gray": "Awesome Lightgray",
            "grey": "Awesome Lightgray",
            "light gray": "Awesome Lightgray",
            "light grey": "Awesome Lightgray",
            "lightgray": "Awesome Lightgray",
            "lightgrey": "Awesome Lightgray",
            "awesome lightgray": "Awesome Lightgray",
            "awesome lightgrey": "Awesome Lightgray",
            "awesome light gray": "Awesome Lightgray",
            "olive": "Awesome Olive",
            "awesome olive": "Awesome Olive",
            "pink": "Awesome Pink",
            "awesome pink": "Awesome Pink",
        }
        return mapping.get(key, "")

    if series == "a57":
        mapping = {
            "navy": "Awesome Navy",
            "awesome navy": "Awesome Navy",
            "gray": "Awesome Gray",
            "grey": "Awesome Gray",
            "awesome gray": "Awesome Gray",
            "awesome grey": "Awesome Gray",
            "icy blue": "Awesome Icyblue",
            "icyblue": "Awesome Icyblue",
            "awesome icyblue": "Awesome Icyblue",
            "awesome icy blue": "Awesome Icyblue",
            "blue": "Awesome Icyblue",
            "lilac": "Awesome Lilac",
            "awesome lilac": "Awesome Lilac",
            "pink": "Awesome Pink",
            "awesome pink": "Awesome Pink",
        }
        return mapping.get(key, "")

    if series == "a37":
        mapping = {
            "charcoal": "Awesome Charcoal",
            "awesome charcoal": "Awesome Charcoal",
            "black": "Awesome Charcoal",
            "lavender": "Awesome Lavender",
            "awesome lavender": "Awesome Lavender",
            "graygreen": "Awesome Graygreen",
            "gray green": "Awesome Graygreen",
            "grey green": "Awesome Graygreen",
            "awesome graygreen": "Awesome Graygreen",
            "green": "Awesome Graygreen",
            "white": "Awesome White",
            "awesome white": "Awesome White",
            "gray": "Awesome Graygreen",
            "grey": "Awesome Graygreen",
        }
        return mapping.get(key, "")

    if series == "a36":
        mapping = {
            "lime": "Awesome Lime",
            "awesome lime": "Awesome Lime",
            "black": "Awesome Black",
            "awesome black": "Awesome Black",
            "white": "Awesome White",
            "awesome white": "Awesome White",
            "gray": "Awesome Light Gray",
            "grey": "Awesome Light Gray",
            "light gray": "Awesome Light Gray",
            "awesome light gray": "Awesome Light Gray",
        }
        return mapping.get(key, color)

    if series in {"a17", "a16", "a07", "a06", "a05"}:
        mapping = {
            "black": "Black",
            "blue": "Blue",
            "gray": "Gray",
            "green": "Green",
            "light green": "Light Green",
            "violet": "Light Violet",
            "light violet": "Light Violet",
            "white": "White",
        }
        return mapping.get(key, color)

    return color


def normalize_17e_color(model: str, color: str) -> str:
    """iPhone 17e official: Black, White, Soft Pink."""
    if not color or model.lower() != "iphone 17e":
        return color
    key = re.sub(r"\s+", " ", color.lower()).strip()
    if key in {"pink", "soft pink"}:
        return "Soft Pink"
    if key in {"black", "white"}:
        return key.title()
    return ""


def normalize_starlight_white_color(model: str, color: str) -> str:
    """iPhone 13/14 (+ mini/Plus) and SE 3rd: official finish is Starlight, not White.

    Suppliers often list White for the same SKU — collapse to Starlight so
    storefront cards do not duplicate.
    """
    if not color:
        return color
    key = re.sub(r"\s+", " ", color.lower()).strip()
    if key != "white":
        return color
    m = model.lower().strip()
    gen = _generation(m)
    if gen in {13, 14} and "pro" not in m:
        return "Starlight"
    if m in {"iphone se", "iphone se 2022", "iphone se 3", "iphone se 3rd"}:
        return "Starlight"
    return color


def normalize_base_17_color(model: str, color: str) -> str:
    """iPhone 17 (non-Pro) official: Black, White, Mist Blue, Sage, Lavender."""
    if not color or model.lower() != "iphone 17":
        return color
    key = re.sub(r"\s+", " ", color.lower()).strip()
    mapping = {
        "black": "Black",
        "white": "White",
        "blue": "Mist Blue",
        "mist blue": "Mist Blue",
        "mist": "Mist Blue",
        "sage": "Sage",
        "lavender": "Lavender",
        "lavander": "Lavender",
    }
    return mapping.get(key, "")


# Global Market uses `S/M` / `M/L` without parentheses (Bests uses `(L/M)`).
_WATCH_FIT = r"(?:S\s*/\s*M|M\s*/\s*L|L\s*/\s*M|[SML])"

WATCH_BAND_RE = re.compile(
    r"(?i)(?P<band>"
    r"(?:(?:black|natural|white)\s*ti(?:tanium)?|black|white|natural|blue|silver|gold|"
    r"starlight|midnight|rose\s*gold|jet\s*black|space\s*gr[ae]y|gr[ae]y|anchor\s*blue|"
    r"charcoal|bright|black\s*/?\s*charcoal)?"
    r"\s*"
    r"(?:milanese\s*loop|trail\s*loop|alpine\s*loop|ocean\s*band|sport\s*band|"
    r"sport\s*loop|braided\s*solo\s*loop|solo\s*loop|nike\s*(?:sport\s*)?band|"
    r"link\s*bracelet|bright\s*loop|charcoal\s*loop)"
    r"(?:\s*\(?\s*" + _WATCH_FIT + r"\s*\)?)?"
    r")\s*$",
)

WATCH_FIT_ONLY_RE = re.compile(
    r"(?i)\s+\(?\s*(?P<fit>S\s*/\s*M|M\s*/\s*L|L\s*/\s*M)\s*\)?\s*$",
)

WATCH_ULTRA_RE = re.compile(r"(?i)\b(?:apple\s*watch\s+)?ultra\s*(?P<gen>[23])\b")


def expand_watch_ti(text: str) -> str:
    """Black Ti → Black Titanium (case & strap wording)."""
    t = text
    t = re.sub(r"(?i)\bblack\s*ti\b(?!\w)", "Black Titanium", t)
    t = re.sub(r"(?i)\bnatural\s*ti\b(?!\w)", "Natural Titanium", t)
    t = re.sub(r"(?i)\bwhite\s*ti\b(?!\w)", "White Titanium", t)
    t = re.sub(r"(?i)\brose\s*gold\b", "Rose Gold", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_milanese_band(band: str) -> str:
    """Apple Ultra Milanese is always '* Titanium Milanese Loop' (not bare Black/Natural)."""
    if not band:
        return band
    b = expand_watch_ti(band)
    if re.search(r"(?i)milanese", b):
        # Bare color before Milanese → Titanium (official Apple naming)
        b = re.sub(
            r"(?i)\b(black|natural|white)\s+(?=milanese)",
            lambda m: f"{m.group(1).title()} Titanium ",
            b,
        )
        b = re.sub(r"(?i)\btitanium\s+titanium\b", "Titanium", b)
    # Supplier shorthand: "Black Charcoal Loop" → official "Black/Charcoal Trail Loop"
    if re.search(r"(?i)charcoal\s*loop", b) and not re.search(r"(?i)trail", b):
        size = ""
        sm = re.search(r"\(([^)]+)\)\s*$", b)
        if sm:
            size = f" ({sm.group(1)})"
        b = f"Black Charcoal Trail Loop{size}"
    return re.sub(r"\s+", " ", b).strip()


def peel_series_case_from_band(case_color: str, band: str) -> tuple[str, str]:
    """Supplier shorthand: 'S11 46mm Silver Sport Band' → case Silver, band Sport Band.

    Unlike Ultra (White Ocean Band = band color), Series aluminum finishes
    (Silver, Starlight, …) before Sport Band/Loop are the case.
    """
    if case_color or not band:
        return case_color, band
    m = re.match(
        r"(?i)^(?P<case>rose\s*gold|jet\s*black|space\s*gr[ae]y|gr[ae]y|starlight|midnight|"
        r"silver|gold|pink|black|white)\s+"
        r"(?P<band>(?:nike\s*)?(?:sport\s*band|sport\s*loop)|braided\s*solo\s*loop|"
        r"solo\s*loop)(?P<size>\s*\([^)]+\))?$",
        band.strip(),
    )
    if not m:
        return case_color, band
    raw_case = re.sub(r"\s+", " ", m.group("case")).strip().lower()
    case = {
        "grey": "Space Gray",
        "gray": "Space Gray",
        "space grey": "Space Gray",
        "space gray": "Space Gray",
        "black": "Jet Black",
        "rose gold": "Rose Gold",
        "jet black": "Jet Black",
    }.get(raw_case, raw_case.title())
    band_name = re.sub(r"\s+", " ", m.group("band")).strip()
    band_name = " ".join(w.upper() if w.lower() == "nike" else w.title() for w in band_name.split())
    size = (m.group("size") or "").strip()
    return case, f"{band_name} {size}".strip() if size else band_name


def normalize_series_case_color(case_color: str) -> str:
    if not case_color:
        return case_color
    case_color = re.sub(r"\s+", " ", case_color).strip()
    low = case_color.lower()
    aliases = {
        "grey": "Space Gray",
        "gray": "Space Gray",
        "space grey": "Space Gray",
        "space gray": "Space Gray",
        "black": "Jet Black",
        "rose gold": "Rose Gold",
        "jet black": "Jet Black",
    }
    if low in aliases:
        return aliases[low]
    if "titanium" in low:
        return expand_watch_ti(case_color)
    return case_color.title()


def parse_apple_watch(title: str) -> tuple[str, str, str, str] | None:
    """Return (device_name, model_key, case_color, band) or None."""
    # Never claim Galaxy Watch Ultra / Samsung watches as Apple
    if re.search(r"(?i)\bgalaxy\b", title) and re.search(r"(?i)\bwatch\b", title):
        return None
    # Galaxy Tab S10 / Tab S9 must not become Apple Watch S10
    if re.search(r"(?i)\b(?:galaxy\s+)?tab\b|\bsm-x\d+", title):
        return None
    band = ""
    raw_title = title.strip()
    band_m = WATCH_BAND_RE.search(raw_title)
    head = raw_title[: band_m.start()].strip() if band_m else raw_title
    if band_m:
        band = normalize_milanese_band(
            expand_watch_ti(re.sub(r"\s+", " ", band_m.group("band")).strip())
        )
    else:
        fit_m = WATCH_FIT_ONLY_RE.search(raw_title)
        if fit_m:
            band = re.sub(r"\s+", "", fit_m.group("fit")).upper()
            head = raw_title[: fit_m.start()].strip()

    ultra = WATCH_ULTRA_RE.search(head)
    if ultra:
        gen = ultra.group("gen")
        device_name = f"Apple Watch Ultra {gen}"
        model_key = f"apple watch ultra {gen}"
        after = head[ultra.end() :]
        # Case only from head — band color (White Ocean Band) is not the case.
        # Official Ultra 2/3 cases: Natural Titanium, Black Titanium only.
        cm = re.search(
            r"(?i)\b((?:black|natural)\s*ti(?:tanium)?|black|natural)\b",
            after,
        )
        case_color = expand_watch_ti(cm.group(1)) if cm else ""
        if case_color and "titanium" not in case_color.lower():
            if case_color.lower() in {"black", "natural"}:
                case_color = f"{case_color.title()} Titanium"
        # clean_offer_title may collapse "BLACK Black Alpine…" → band eats the case word
        if not case_color and band:
            peel = re.match(
                r"(?i)^(black|natural)(?:\s*ti(?:tanium)?)?\s+(.+)$",
                band.strip(),
            )
            if peel:
                case_color = expand_watch_ti(peel.group(1))
                if "titanium" not in case_color.lower():
                    case_color = f"{case_color.title()} Titanium"
                band = peel.group(2).strip()
        return device_name, model_key, case_color, band

    sm = re.search(
        r"(?i)\b(?:apple\s*watch\s+)?(?P<gen>se\s*[23]|s(?:1[0-9]|[1-9]))\b"
        r"(?:\s*20\d{2})?"
        r"(?:\s*(?P<size>\d{2})\s*mm)?",
        head,
    )
    if sm:
        raw_gen = re.sub(r"\s+", "", sm.group("gen")).upper()
        size = sm.group("size")
        if raw_gen.startswith("SE"):
            se_n = raw_gen[2:]
            device_name = f"Apple Watch SE {se_n}" + (f" {size}mm" if size else "")
            model_key = f"apple watch se {se_n}" + (f" {size}mm" if size else "")
        else:
            device_name = f"Apple Watch {raw_gen}" + (f" {size}mm" if size else "")
            model_key = device_name.lower()
        after = head[sm.end() :]
        cm = re.search(
            r"(?i)\b(rose\s*gold|jet\s*black|space\s*gr[ae]y|gr[ae]y|"
            r"(?:black|natural|white)\s*ti(?:tanium)?|"
            r"black|natural|white|silver|gold|starlight|midnight|pink)\b",
            after,
        )
        case_color = expand_watch_ti(cm.group(1)) if cm else ""
        case_color = normalize_series_case_color(case_color)
        case_color, band = peel_series_case_from_band(case_color, band)
        # SE aluminum: dark finish is Midnight (not Jet Black)
        if raw_gen.startswith("SE") and case_color.lower() in {"jet black", "black"}:
            case_color = "Midnight"
        return device_name, model_key, case_color, band

    if re.search(r"(?i)\b(apple\s*watch|watch\s*ultra)\b", title):
        # Bare "Apple Watch · Starlight" without series/size — not a publishable SKU
        return None
    return None


def extract_apple_model_code(title: str) -> str:
    """Apple order/model codes like MHFJ4 (exactly 5 alnum, mixed letters+digits)."""
    for m in re.finditer(r"\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{5}\b", title, re.I):
        code = m.group(0).upper()
        if code.endswith(("GB", "TB")):
            continue
        if re.fullmatch(r"\d+[A-Z]{2}", code):  # 256GB-style already filtered; belt
            continue
        # Compact series+size (Air13 / Pro14) is not an order code
        if re.fullmatch(r"(?:AIR|PRO|NEO)\d{2}", code):
            continue
        return code
    return ""


def normalize_section_header(section: str | None) -> str:
    """Strip multipart markers and marketing tokens from supplier section headers."""
    if not section:
        return ""
    cleaned = strip_part_marker(section)
    cleaned = re.sub(r"(?i)\bновые\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:/")
    return cleaned


def build_config(
    *,
    ram: str = "",
    storage: str = "",
    color: str = "",
    sim: SimType | None = None,
    band: str = "",
    model_code: str = "",
    extra: str = "",
) -> str:
    parts: list[str] = []
    if ram and storage:
        parts.append(f"{ram.replace('GB', '')}/{storage}")
    elif storage:
        parts.append(storage)
    elif ram:
        parts.append(ram)
    if color:
        parts.append(color)  # already display-cased (Deep Blue)
    if band:
        parts.append(band)
    if extra:
        parts.append(extra)
    if sim:
        parts.append(sim)
    if model_code:
        parts.append(model_code.upper())
    return " · ".join(parts)


def build_display_title(device_name: str, config: str) -> str:
    if config:
        return f"{device_name} · {config}"
    return device_name


def identity_key(
    model: str,
    storage: str,
    color: str,
    sim: SimType | None,
    ram: str = "",
    condition: str = "",
    band: str = "",
    model_code: str = "",
    extra: str = "",
) -> str:
    raw = "|".join(
        [
            model.lower(),
            ram.lower(),
            storage.lower(),
            color.lower(),
            (sim or "").lower(),
            condition.lower(),
            band.lower(),
            model_code.lower(),
            extra.lower(),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _rejected(
    *,
    kind: OfferKind = OfferKind.unknown,
    model: str = "",
    storage: str = "",
    color: str = "",
    region: str | None = None,
    display_title: str = "",
    reject_reason: str,
) -> OfferIdentity:
    return OfferIdentity(
        kind=kind,
        brand="",
        device_category="",
        device_name="",
        model=model,
        storage=storage,
        color=color,
        sim=None,
        region=region,
        ram="",
        config="",
        display_title=display_title,
        identity_key="",
        publish=False,
        reject_reason=reject_reason,
    )


def _apple_other_device_name(token: str, working: str) -> tuple[str, str, str, str]:
    """Return brand, category, device_name, model_key."""
    key = re.sub(r"\s+", " ", token.lower())
    brand, category, prefix = APPLE_OTHER_META.get(key, ("Apple", "Техника Apple", prefix_fallback(token)))
    # Keep a short distinctive tail (Pro / Max / generation) without dumping the whole line
    tail = working
    # 11th-gen base iPad is also sold/listed as "iPad A16"
    if key == "ipad":
        tail = re.sub(r"(?i)\ba16\b", "11", tail)
    for pattern, _ in SIM_PATTERNS:
        tail = pattern.sub(" ", tail)
    tail = REGION_TOKEN_RE.sub(" ", tail)
    # GPU/CPU/RAM/storage before orphan slash leftovers
    tail = scrub_spec_leaks(tail)
    tail = strip_emoji(tail)
    tail = APPLE_NAME_JUNK_RE.sub(" ", tail)
    # Air13 / Pro14 → Air 13 / Pro 14
    tail = re.sub(r"(?i)\b(air|pro)(\d{2})\b", r"\1 \2", tail)
    # drop color words (keep connectivity: Wi-Fi / LTE)
    for c in (
        "space\\s*gr[ae]y",
        "space\\s*black",
        "jet\\s*black",
        "rose\\s*gold",
        "sky\\s*blue",
        "deep\\s*blue",
        "mist\\s*blue",
        "icy\\s*blue",
        "black",
        "white",
        "blue",
        "natural",
        "titanium",
        "gold",
        "silver",
        "purple",
        "green",
        "pink",
        "yellow",
        "starlight",
        "midnight",
        "desert",
        "orange",
        "ultramarine",
        "gr[ae]y",
        "blush",
        "indigo",
        "citrus",
        "sky",
        "space",
    ):
        tail = re.sub(rf"\b{c}\b", " ", tail, flags=re.I)
    # drop Apple 5-char model codes (MHFJ4) — they live in config
    for code in re.findall(
        r"\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{5}\b", tail, flags=re.I
    ):
        if not str(code).upper().endswith(("GB", "TB")):
            tail = re.sub(rf"\b{re.escape(code)}\b", " ", tail, flags=re.I)
    # Years are not part of the shelf name (supplier "(2026)" marketing),
    # except MacBook Neo 2025-style model years adjacent to Neo.
    tail = re.sub(r"\(\s*20\d{2}\s*\)", " ", tail)
    if not re.search(r"(?i)\bneo\s*20\d{2}\b", working):
        tail = re.sub(r"\b20\d{2}\b", " ", tail)
    tail = re.sub(re.escape(token), " ", tail, flags=re.I)
    # Drop repeated series words already in prefix (MacBook Air … Air)
    if key == "macbook":
        tail = re.sub(r"(?i)\bmacbook\b", " ", tail)
    if key == "ipad":
        tail = re.sub(r"(?i)\bipad\b", " ", tail)
    if key in {"apple watch", "watch ultra"}:
        tail = re.sub(r"(?i)\b(?:apple\s*)?watch\b|\bultra\b", " ", tail)
    if key == "imac":
        tail = re.sub(r"(?i)\bimac\b|\bmac\s*mini\b", " ", tail)
    tail = re.sub(r"[^\w\s+./-]", " ", tail)
    tail = scrub_spec_leaks(tail)
    tail = re.sub(r"\s+", " ", tail).strip(" -/")
    # keep first ~4 meaningful tokens
    bits = [
        b
        for b in tail.split()
        if b.lower() not in {"apple", "the", "and", "для", "wi", "fi", "wifi", "lte"}
        and b not in {"+", "/"}
    ][:4]
    device_name = prefix if not bits else f"{prefix} {' '.join(bits)}"
    device_name = collapse_duplicate_tokens(device_name)
    device_name = re.sub(r"\banc\b", "ANC", device_name, flags=re.I)
    device_name = re.sub(r"\busb[\s\-]?c\b", "USB-C", device_name, flags=re.I)
    if key == "macbook":
        # MacBook Neo is its own line (A18…), never M-series Air/Pro chips.
        if re.search(r"(?i)\bneo\b", working):
            size_m = re.search(r"(?i)(?:\bneo\s*(1[3-6])\b|\b(1[3-6])\s*neo\b)", working)
            chip_m = re.search(r"(?i)\b(a\d{2})\s*(pro)?\b", working)
            year_m = re.search(r"(?i)\bneo\s*(20\d{2})\b", working)
            parts = ["MacBook", "Neo"]
            if size_m:
                parts.append(size_m.group(1) or size_m.group(2))
            if chip_m:
                chip = chip_m.group(1).upper()
                if chip_m.group(2):
                    chip = f"{chip} Pro"
                parts.append(chip)
            if year_m:
                parts.append(year_m.group(1))
            device_name = " ".join(parts)
            model_key = device_name.lower()
            return brand, category, device_name, model_key
        # Supplier "Max M4" / "Pro M4" → official "M4 Max" / "M4 Pro"
        device_name = re.sub(
            r"(?i)\b(max|pro)\s+m(\d+)\b",
            lambda m: f"M{m.group(2)} {m.group(1).title()}",
            device_name,
        )
        device_name = re.sub(
            r"(?i)\b(air|pro|neo)\b",
            lambda m: m.group(1).title(),
            device_name,
        )
        # "MacBook Air 15 M5 Air" → drop trailing duplicate series
        device_name = re.sub(r"(?i)\b(air|pro|neo)\s+\1\b", r"\1", device_name)
        device_name = re.sub(
            r"(?i)^(macbook(?:\s+(?:air|pro|neo))?.*?)\s+(air|pro|neo)$",
            r"\1",
            device_name,
        )
    if key == "ipad":
        device_name = re.sub(r"(?i)\b(air|pro)\s+\1\b", r"\1", device_name)
        conn = _extract_connectivity(working)
        if conn and conn.lower() not in device_name.lower():
            device_name = f"{device_name} {conn}".strip()
    device_name = scrub_spec_leaks(device_name)
    device_name = collapse_duplicate_tokens(device_name)
    model_key = device_name.lower()
    return brand, category, device_name, model_key


def prefix_fallback(token: str) -> str:
    return token.title()


def should_prepend_section(section: str | None, title: str) -> bool:
    if not section:
        return False
    section = strip_part_marker(section)
    title = strip_part_marker(title)
    if not section:
        return False
    if is_junk_section(section):
        return False
    if re.search(r"(?i)\bairpods\b", section) and re.search(r"(?i)\bfitbit\b", title):
        return False
    if not MODEL_SECTION_RE.search(section):
        return False
    if section.lower().rstrip(":").strip() in title.lower():
        return False
    # Top MacBook: section "MacBook Pro 14 (M1)" + order-code line "MKGQ3 – 16/1tb …"
    # (16/1tb must not be treated as iPhone 16 — blocks glue otherwise)
    if re.search(r"(?i)\bmacbook\b", section) and extract_apple_model_code(strip_emoji(title)):
        return True
    # Title already names a product — don't glue. Use normalize_iphone_model so
    # "16/512" RAM/storage is not mistaken for iPhone 16.
    if normalize_iphone_model(title) or APPLE_OTHER_RE.search(title):
        return False
    # Samsung / Android lines already carry model — don't glue "Прайс Galaxy S"
    if re.search(r"(?i)\b(s2[3-9]|s1[0-9]|galaxy|pixel|redmi|poco|honor|huawei|xiaomi)\b", title):
        return False
    # Full PS5 / DualSense product lines — don't glue another PS5 header onto them
    if re.search(r"(?i)\b(ps\s*5|playstation\s*5|dual\s*sense)\b", title):
        return False
    # Insta360 lines already carry the brand/model
    if re.search(r"(?i)\b(insta\s*360|insta360)\b", title):
        return False
    # Gaming / Dyson / Yandex / Meta lines that already name the product
    if re.search(
        r"(?i)\b(xbox|nintendo|oculus|logitech|steam\s*deck|airwrap|supersonic|"
        r"airstrait|яндекс|yandex|ray-?\s*ban)\b",
        title,
    ):
        return False
    # MacBook continuation: Pro/Air/Neo + M-chip — allow MacBook section glue
    if re.search(r"(?i)\b(?:pro|air)\s+1[3-6]\s+m\d|\bneo\s+20\d{2}\b", title):
        return bool(re.search(r"(?i)\bmacbook\b", section))
    # Compact Air13 / Pro14 continuations under MacBook sections
    if re.search(r"(?i)\b(?:air|pro)\d{2}\b", title):
        return bool(re.search(r"(?i)\bmacbook\b", section))
    # Bare Air13 / Pro14 / Neo lines — glue MacBook header even after stripping «Новые»
    if re.search(r"(?i)^\s*(?:air|pro)\s*1[3-6]\b|^\s*neo\b", title.strip()):
        return bool(re.search(r"(?i)\bmacbook\b", section))
    # Dyson SKU codes under HD## / Airwrap / vacuum sections
    if re.search(r"(?i)^\s*(?:hd\d+|v\d+|ph\d+|hs\d+|sv\d+|tp\d+|hu\d+)\b", title.strip()):
        return bool(re.search(r"(?i)\b(dyson|hd\d+|airwrap|supersonic|беспровод|воздухооч)\b", section))
    return bool(
        CONTINUATION_START_RE.search(title.strip())
        or normalize_iphone_model(title) is None
    )


def is_junk_section(section: str | None) -> bool:
    if not section:
        return False
    s = strip_part_marker(section).strip()
    if not s:
        return False
    if SECTION_JUNK_RE.search(s):
        return True
    if len(s) > 55:
        return True
    lower = s.lower()
    if any(tok in lower for tok in ("выдача", "день заказа", "следующий день", "до 14:00", "до 14.00")):
        return True
    if lower.startswith("прайс"):
        return True
    return False


def is_marketing_noise(title: str) -> bool:
    return bool(MARKETING_RE.search(title))


def collapse_duplicate_tokens(title: str) -> str:
    """Saeco Saeco Magic M1 → Saeco Magic M1"""
    parts = title.split()
    if not parts:
        return title
    out = [parts[0]]
    for part in parts[1:]:
        if part.lower() == out[-1].lower():
            continue
        out.append(part)
    return " ".join(out)


def clean_offer_title(title: str) -> str:
    t = _nfkc(title)
    # Strip logistics / прайс / asis noise while flags still present for region extract upstream
    t = NOISE_PHRASE_RE.sub(" ", t)
    t = strip_emoji(t)
    t = CENA_SUFFIX_RE.sub("", t)
    # Trailing price tokens left on Top payload raw lines ("— 123000₽")
    t = re.sub(r"\s*[-–—]\s*\d[\d\s]*(?:[₽руб.]*|[rR][uU][bB])?\s*$", "", t)
    # Trailing bare RUB amounts — never strip 20xx product years (MacBook Neo 2025)
    t = re.sub(r"\s+\d{5,6}\s*₽\s*$", "", t)
    t = re.sub(r"\s+(?!20\d{2}\b)\d{5,6}\s*$", "", t)
    # Leading price-list label leftovers
    t = re.sub(r"(?i)^\s*прайс\s+", "", t)
    t = re.sub(r"(?i)^\s*galaxy\s+s\s+(?=s\d)", "Galaxy ", t)  # "Galaxy S S25" → "Galaxy S25"
    # Supplier typos (Top re:sale accessories)
    t = re.sub(r"(?i)\bmause\b", "Mouse", t)
    t = re.sub(r"(?i)\bucb-?c\b", "USB-C", t)
    t = collapse_duplicate_tokens(re.sub(r"\s+", " ", t).strip(" -–—/|:;•"))
    return t


def is_junk_offer(title: str) -> bool:
    cleaned = clean_offer_title(title)
    if len(cleaned) < 4:
        return True
    if JUNK_RE.search(title) or JUNK_RE.search(cleaned):
        return True
    # Bare "Цена" / price-label leftovers after strip
    if not cleaned or cleaned.lower() in {"цена", "price", "прайс"}:
        return True
    # Title still dominated by logistics copy → reject
    if re.search(r"(?i)выдача\s+в\s+день|день\s+заказа", cleaned):
        return True
    return False


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

    # iPhone 12–13: all regions → Sim+eSIM (incl. US / CN)
    if gen in {12, 13}:
        return "Sim+eSIM"

    if region_l in {"cn", "china"}:
        if "17e" in model or model == "iphone air":
            return "eSIM"
        return "2Sim"

    # Business rule (Top re:sale): HK/Macao → Sim+eSIM (not dual-nano 2Sim)
    if region_l in {"hk", "mo", "hong kong", "macao", "macau"}:
        return "Sim+eSIM"

    if is_17_family or gen == 17:
        if region_l in ESIM_ONLY_17_REGIONS:
            return "eSIM"
        return "Sim+eSIM"

    if gen in {14, 15, 16}:
        if region_l in {"us", "usa", "usvi"}:
            return "eSIM"
        return "Sim+eSIM"

    return None


def _ps5_revision(text: str) -> tuple[str, str]:
    """Return (text_without_rev, revision_label like '1 ревизия')."""
    m = re.search(r"(?i)\(?\s*(\d+)\s*я?\s*рев\.?\s*\)?", text)
    if not m:
        return text, ""
    rev = f"{m.group(1)} ревизия"
    cleaned = (text[: m.start()] + " " + text[m.end() :]).strip()
    return cleaned, rev


def _normalize_ps5_capacity(text: str) -> str:
    def _tb(m: re.Match[str]) -> str:
        return f"{m.group(1)}Tb"

    def _gb(m: re.Match[str]) -> str:
        return f"{m.group(1)}Gb"

    t = re.sub(r"(?i)\b(\d+)\s*tb\b", _tb, text)
    t = re.sub(r"(?i)\b(\d+)\s*gb\b", _gb, t)
    return t


def parse_sony_ps5(title: str) -> tuple[str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, color) or None."""
    raw = re.sub(r"\s+", " ", title.strip())

    # Portal / Pulse / VR2 Horizon (Bests: "PlayStation Sony Portal White")
    portal = re.search(
        r"(?i)\b(?:playstation\s+)?(?:sony\s+)?portal\b(?:\s+(?P<color>.+))?$",
        raw,
    )
    if portal and re.search(r"(?i)\b(portal|playstation|sony)\b", raw):
        if re.search(r"(?i)\bportal\b", raw) and not re.search(
            r"(?i)\b(ps\s*5|dual\s*sense|pulse)\b", raw
        ):
            color = (portal.group("color") or "").strip(" -–—/")
            color = re.sub(r"(?i)\b(30th\s+anniversary)\b", "30th Anniversary", color)
            if color:
                bits = []
                for part in re.split(r"\s+", color):
                    if part.lower() in {"anniversary"}:
                        bits.append(part.title())
                    elif re.fullmatch(r"\d+th", part, re.I):
                        bits.append(part.lower())
                    else:
                        bits.append(part.title())
                color = " ".join(bits)
            device_name = "Sony Portal"
            return "Sony", "Игровые консоли", device_name, device_name.lower(), color

    pulse = re.search(
        r"(?i)\b(?:playstation\s+)?pulse\s*(?P<model>elite|3d)\b(?:\s+(?P<color>.+))?$",
        raw,
    )
    if pulse:
        model = pulse.group("model").upper() if pulse.group("model").lower() == "3d" else "Elite"
        color = (pulse.group("color") or "").strip()
        if color.lower() in {"camouflage", "camo"}:
            color = "Camouflage"
        elif color:
            color = color.title()
        device_name = f"Pulse {model}"
        return "Sony", "Наушники", device_name, device_name.lower(), color

    if re.search(r"(?i)\b(?:playstation\s+)?vr\s*2\b.*\bhorizon\b|\bhorizon\b.*\bvr\s*2\b", raw):
        device_name = "PS5 VR2 Horizon"
        return "Sony", "VR", device_name, device_name.lower(), ""

    if not re.search(r"(?i)\b(ps\s*5|playstation\s*5|dual\s*sense)\b", raw):
        return None

    # DualSense first — before PS5 de-glue (which would drop the DualSense prefix)
    if re.search(r"(?i)dual\s*sense", raw):
        color = ""
        cm = re.search(
            r"(?i)dual\s*sense(?:\s*(?:edge|ps\s*5))?\s*[:\-–—]?\s*(?P<color>.+)\s*$",
            raw,
        )
        edge = bool(re.search(r"(?i)dual\s*sense\s*edge\b", raw))
        if cm:
            color = cm.group("color").strip()
            if color.lower() in {"ps", "ps5", "edge"}:
                color = ""
            else:
                # Multi-word edition names
                color = " ".join(w.title() if not w.isupper() else w for w in color.split())
                color = re.sub(r"(?i)\bcamo(?:uflage)?\b", "Camo", color)
        if not color:
            tail = re.sub(
                r"(?i).*dual\s*sense(?:\s*(?:edge|ps\s*5))?\s*[:\-–—]?\s*",
                "",
                raw,
            ).strip(" :-–—")
            if tail and not re.search(r"(?i)\bps\s*5\b", tail):
                color = tail.title()
        if color.lower() == "camo":
            color = "Camo"
        device_name = "PS5 DualSense Edge" if edge else "PS5 DualSense"
        model_key = device_name.lower() + (f" {color.lower()}" if color else "")
        return "Sony", "Геймпады", device_name, model_key, color

    # If a PS5 header was wrongly glued onto another PS5 line, keep the last product.
    chunks = [
        c.strip(" -–—:")
        for c in re.split(r"(?i)(?=\bps\s*5\b|\bplaystation\s*5\b)", raw)
        if c.strip()
    ]
    if len(chunks) > 1 and re.search(r"(?i)\bps\s*5\b|\bplaystation\s*5\b", chunks[-1]):
        raw = chunks[-1]

    # Consoles / VR
    t = re.sub(r"(?i)\bplaystation\s*5\b", "PS5", raw)
    t = re.sub(r"(?i)\bps\s*5\b", "PS5", t)
    t = t.strip(" -–—:")
    t, rev = _ps5_revision(t)
    t = _normalize_ps5_capacity(t)
    t = re.sub(r"\s+", " ", t).strip(" -–—:")
    t = re.sub(r"(?i)\bvr\s*2\b", "VR2", t)
    t = re.sub(r"(?i)\bdigital\b", "Digital", t)
    t = re.sub(r"(?i)\bdisk\b", "Disk", t)
    t = re.sub(r"(?i)\bslim\b", "Slim", t)
    t = re.sub(r"(?i)\bpro\b", "Pro", t)
    t = re.sub(r"(?i)\b(\d+)\s*g\b", lambda m: f"{m.group(1)}g", t)
    if rev:
        t = f"{t} {rev}".strip()
    t = re.sub(r"\s+", " ", t).strip()
    if not t.lower().startswith("ps5"):
        t = f"PS5 {t}"
    model_key = t.lower()
    category = "VR" if "vr2" in model_key else "Игровые консоли"
    return "Sony", category, t, model_key, ""


def _title_case_device(text: str) -> str:
    parts = []
    for w in text.split():
        if re.fullmatch(r"\d+[gt]b", w, re.I):
            parts.append(w.upper().replace("TB", "TB").replace("GB", "GB"))
        elif re.fullmatch(r"[a-z]{1,3}\d+[a-z]?", w, re.I):
            parts.append(w.upper())
        elif w.lower() in {"wifi", "wi-fi"}:
            parts.append("Wi-Fi")
        elif w.lower() in {"plus", "pro", "max", "ultra", "lite", "mini", "note", "pad"}:
            parts.append(w.title())
        elif w.lower() == "gt":
            parts.append("GT")
        elif w.lower() == "xt":
            parts.append("XT")
        elif w.lower() == "5g":
            parts.append("5G")
        elif w.lower() == "4g":
            parts.append("4G")
        elif w.lower() == "lte":
            parts.append("LTE")
        else:
            parts.append(w[0].upper() + w[1:] if w else w)
    return " ".join(parts)


def _extract_connectivity(title: str) -> str:
    # Suppliers often use U+2011 non-breaking hyphen in "Wi‑Fi"
    normalized = (
        title.replace("\u2011", "-")
        .replace("\u2010", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\xa0", " ")
    )
    has_wifi = bool(re.search(r"(?i)\bwi-?fi\b", normalized))
    has_lte = bool(re.search(r"(?i)\blte\b|\bcellular\b", normalized))
    has_4g = bool(re.search(r"(?i)\b4g\b", normalized))
    if has_wifi and (has_lte or has_4g):
        return "Wi-Fi + LTE"
    if has_wifi:
        return "Wi-Fi"
    if has_lte:
        return "LTE"
    if has_4g:
        return "4G"
    return ""


def parse_android(title: str) -> tuple[str, str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, color, connectivity) or None."""
    raw = re.sub(r"\s+", " ", title.strip())
    # Tecno Unisale: "Tecno 40 Camon" → "Tecno Camon 40"; "Tecno 8 Phantom" → "Tecno Phantom 8"
    raw = re.sub(r"(?i)\b(tecno)\s+(\d+)\s+(camon|phantom)\b", r"\1 \3 \2", raw)
    m = re.search(
        r"(?i)\b(?P<brand>"
        r"huawei|honor|xiaomi|redmi|poco|google\s*pixel|pixel|"
        r"realme|one\s*plus|oneplus|nothing(?:\s*phone)?|tecno|"
        r"oppo|vivo|motorola|moto|iqoo|infinix|asus|nokia"
        r")\b",
        raw,
    )
    if not m:
        return None
    # Handhelds are not phones — leave to parse_gaming
    if re.search(r"(?i)\brog\s*ally\b", raw):
        return None
    brand_raw = re.sub(r"\s+", " ", m.group("brand").strip().lower())
    brand_map = {
        "huawei": "Huawei",
        "honor": "Honor",
        "xiaomi": "Xiaomi",
        "redmi": "Redmi",
        "poco": "Poco",
        "pixel": "Google",
        "google pixel": "Google",
        "realme": "Realme",
        "oneplus": "OnePlus",
        "one plus": "OnePlus",
        "nothing": "Nothing",
        "nothing phone": "Nothing",
        "tecno": "Tecno",
        "oppo": "Oppo",
        "vivo": "Vivo",
        "motorola": "Motorola",
        "moto": "Motorola",
        "iqoo": "iQOO",
        "infinix": "Infinix",
        "asus": "Asus",
        "nokia": "Nokia",
    }
    brand = brand_map.get(brand_raw, brand_raw.title())
    rest = raw[m.start() :].strip()
    # Normalize Plus spelling before stripping storage/color
    rest = re.sub(r"(?i)\bplus\b", "Plus", rest)
    rest = re.sub(r"(?i)(\w)\+(?!\w)", r"\1 Plus", rest)
    rest = re.sub(r"(?i)\bgoogle\s+pixel\b", "Pixel", rest)
    rest = re.sub(r"(?i)\bone\s*plus\b", "OnePlus", rest)
    rest = re.sub(r"(?i)\bnothing\s+phone\b", "Nothing Phone", rest)
    rest = re.sub(r"(?i)\brealme\b", "Realme", rest)
    rest = re.sub(r"(?i)\btecno\b", "Tecno", rest)
    rest = re.sub(r"(?i)\boppo\b", "Oppo", rest)
    rest = re.sub(r"(?i)\bvivo\b", "Vivo", rest)
    rest = re.sub(r"(?i)\b(?:motorola|moto)\b", "Motorola", rest)
    rest = re.sub(r"(?i)\biqoo\b", "iQOO", rest)
    rest = re.sub(r"(?i)\binfinix\b", "Infinix", rest)
    rest = re.sub(r"(?i)\basus\b", "Asus", rest)
    rest = re.sub(r"(?i)\bnokia\b", "Nokia", rest)

    connectivity = _extract_connectivity(rest)
    color = extract_color(rest)
    ram = extract_ram(rest)
    storage = extract_storage(rest)
    if not storage:
        return None

    # Device body: brand + model tokens before RAM/storage
    body = rest
    cut = None
    ram_m = RAM_STORAGE_RE.search(body)
    stor_m = STORAGE_RE.search(body)
    if ram_m and (not stor_m or ram_m.start() <= stor_m.start()):
        cut = ram_m.start()
    elif stor_m:
        cut = stor_m.start()
    if cut is not None:
        device_body = body[:cut].strip(" -–—/")
    else:
        device_body = body
    # Strip trailing color words from device body
    if color:
        device_body = re.sub(rf"(?i)\b{re.escape(color)}\b", " ", device_body)
        # Also strip multi-word OEM aliases that extract_color resolved
        for alias in (
            "lake cyan",
            "guava soda",
            "lemongrass",
            "jet black",
            "chalk white",
            "awesome lime",
            "dark forest",
            "royal burgundy",
            "glacier blue",
            "blaze purple",
            "blush gold",
            "graphite black",
            "orange ocean",
            "storm gray",
            "storm grey",
            "zen green",
        ):
            device_body = re.sub(rf"(?i)\b{alias}\b", " ", device_body)
    device_body = re.sub(r"(?i)\b(wi-?fi|4g|lte)\b", " ", device_body)
    head = body[: cut if cut is not None else len(body)]
    has_5g = bool(re.search(r"(?i)\b5g\b", head))
    device_body = re.sub(r"\s+", " ", device_body).strip(" -–—/")
    if has_5g and not re.search(r"(?i)\b5g\b", device_body):
        device_body = f"{device_body} 5G".strip()
    device_body = collapse_duplicate_tokens(device_body)
    device_body = re.sub(r"(?i)\bplus\b", "Plus", device_body)
    device_name = _title_case_device(device_body)
    # Brand casing
    for b in (
        "Huawei",
        "Honor",
        "Xiaomi",
        "Redmi",
        "Poco",
        "Pixel",
        "Realme",
        "OnePlus",
        "Nothing",
        "Tecno",
        "Oppo",
        "Vivo",
        "Motorola",
        "iQOO",
        "Infinix",
        "Asus",
        "Nokia",
        "Phone",
    ):
        device_name = re.sub(rf"(?i)\b{b}\b", b, device_name)
    if brand == "Google" and not device_name.lower().startswith("pixel"):
        device_name = f"Pixel {device_name}".strip()
        device_name = re.sub(r"(?i)^pixel\s+pixel\b", "Pixel", device_name)
    if brand == "Nothing" and not re.search(r"(?i)\bphone\b", device_name):
        device_name = re.sub(r"(?i)^nothing\b", "Nothing Phone", device_name)
        device_name = collapse_duplicate_tokens(device_name)
    if brand == "OnePlus":
        device_name = re.sub(r"(?i)^oneplus\b", "OnePlus", device_name)
    device_name = re.sub(r"(?i)\bpromax\b", "Pro Max", device_name)
    device_name = re.sub(r"(?i)\bmate\s+xt\b", "Mate XT", device_name)
    # "Realme GT 7 GT" / "Realme Note 60x Note" — family token repeated after the number
    device_name = re.sub(r"(?i)\b(GT)\s+(\d+\w*)\s+\1\b", r"\1 \2", device_name)
    device_name = re.sub(r"(?i)\b(Note)\s+(\d+\w*)\s+\1\b", r"\1 \2", device_name)
    device_name = collapse_duplicate_tokens(device_name)

    is_pad = bool(re.search(r"(?i)\b(pad|matepad|tablet)\b", device_name))
    category = "Планшеты" if is_pad else "Смартфоны"
    # Color fallbacks for android-specific OEM names (Pixel Lemongrass/Snow only here)
    if not color:
        android_color_map = {
            "terracotta": "Terracotta",
            "beige": "Beige",
            "brown": "Brown",
            "porcelain": "Porcelain",
            "golden white": "Golden White",
            "lemongrass": "Lemongrass",
            "snow": "Snow",
            "lake cyan": "Lake Cyan",
            "guava soda": "Guava Soda",
            "jetblack": "Jet Black",
            "jet black": "Jet Black",
            "pistachio": "Pistachio",
            "sand storm": "Sand Storm",
            "sandstorm": "Sand Storm",
            "obsidian": "Obsidian",
            "hazel": "Hazel",
            "coral": "Coral",
            "awesome lime": "Awesome Lime",
            "lime": "Lime",
            "glacier blue": "Glacier Blue",
            "blaze purple": "Blaze Purple",
            "blush gold": "Blush Gold",
            "graphite black": "Graphite Black",
            "orange ocean": "Orange Ocean",
            "bay": "Bay",
            "cyan": "Cyan",
            "lake cyan": "Lake Cyan",
        }
        for alias, finish in android_color_map.items():
            if alias in {"lemongrass", "snow", "hazel"} and brand != "Google":
                continue
            if re.search(rf"(?i)\b{re.escape(alias)}\b", rest):
                color = finish
                break
    model_key = device_name.lower()
    return brand, category, device_name, model_key, color or "", connectivity


def parse_gaming(title: str) -> tuple[str, str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, color, storage) or None."""
    raw = re.sub(r"\s+", " ", title.strip())

    # ASUS ROG Ally — Unisale writes "Ally XBOX" for Ally X (must win over Xbox)
    if re.search(r"(?i)\brog\s*ally\b", raw):
        storage = extract_storage(raw)
        color = extract_color(raw)
        is_x = bool(re.search(r"(?i)\bally\s*x\b|\bxbox\b", raw))
        device_name = "Asus ROG Ally X" if is_x else "Asus ROG Ally"
        return "Asus", "Игровые консоли", device_name, device_name.lower(), color or "", storage

    if re.search(r"(?i)\bxbox\b", raw):
        storage = extract_storage(raw)
        color = extract_color(raw)
        t = re.sub(r"(?i)\bxbox\b", "Xbox", raw)
        t = re.sub(r"(?i)\bseries\s*x\b", "Series X", t)
        t = re.sub(r"(?i)\bseries\s*s\b", "Series S", t)
        t = re.sub(r"(?i)\belite\s*series\s*2\b", "Elite Series 2", t)
        t = re.sub(r"(?i)\bcontroller\b", "Controller", t)
        # Strip storage/color from device name
        name = t
        name = STORAGE_RE.sub(" ", name)
        if color:
            name = re.sub(rf"(?i)\b{re.escape(color)}\b", " ", name)
        name = re.sub(r"\s+", " ", name).strip(" -–—/")
        name = collapse_duplicate_tokens(name)
        if re.search(r"(?i)\bcontroller|elite\b", name):
            category = "Геймпады"
        else:
            category = "Игровые консоли"
        return "Microsoft", category, name, name.lower(), color or "", storage

    if re.search(r"(?i)\bnintendo\b|\bswitch\s*2\b|\bswitch\s*oled\b", raw):
        t = re.sub(r"(?i)\bnintendo\b", "Nintendo", raw)
        t = re.sub(r"(?i)\bswitch\s*oled\b", "Switch OLED", t)
        t = re.sub(r"(?i)\bswitch\s*2\b", "Switch 2", t)
        t = re.sub(r"(?i)\bpro\s*controller\b", "Pro Controller", t)
        name = collapse_duplicate_tokens(re.sub(r"\s+", " ", t).strip())
        if not name.lower().startswith("nintendo"):
            name = f"Nintendo {name}"
        category = "Геймпады" if re.search(r"(?i)controller", name) else "Игровые консоли"
        return "Nintendo", category, name, name.lower(), "", ""

    if re.search(r"(?i)\b(oculus|meta)\s*quest\b|\bquest\s*3s?\b", raw):
        storage = extract_storage(raw)
        t = re.sub(r"(?i)\boculus\s*quest\b", "Quest", raw)
        t = re.sub(r"(?i)\bmeta\s*quest\b", "Quest", t)
        t = re.sub(r"(?i)\bquest\s*3s\b", "Quest 3S", t)
        t = re.sub(r"(?i)\bquest\s*3\b", "Quest 3", t)
        name = STORAGE_RE.sub(" ", t)
        name = re.sub(r"\s+", " ", name).strip(" -–—/")
        name = collapse_duplicate_tokens(name)
        if not name.lower().startswith("quest"):
            # keep Batman edition etc.
            name = re.sub(r"(?i)^(?:oculus|meta)\s*", "", name).strip()
        device_name = name if name.lower().startswith("quest") else f"Quest {name}"
        device_name = re.sub(r"(?i)^quest\s+quest\b", "Quest", device_name)
        return "Meta", "VR", device_name, device_name.lower(), "", storage

    if re.search(r"(?i)\blogitech\b|\bg29\b|driving\s*force\s*shifter", raw):
        t = re.sub(r"(?i)\blogitech\b", "Logitech", raw)
        t = re.sub(r"(?i)\bdriving\s*force\s*shifter\b", "Driving Force Shifter", t)
        t = re.sub(r"(?i)\bg29\b", "G29", t)
        name = collapse_duplicate_tokens(re.sub(r"\s+", " ", t).strip())
        if not name.lower().startswith("logitech"):
            name = f"Logitech {name}"
        return "Logitech", "Аксессуары", name, name.lower(), "", ""

    if re.search(r"(?i)\bsteam\s*deck\b", raw):
        t = re.sub(r"(?i)\bsteam\s*deck\b", "Steam Deck", raw)
        t = re.sub(r"(?i)\bdocking\s*station\b", "Docking Station", t)
        name = collapse_duplicate_tokens(re.sub(r"\s+", " ", t).strip())
        return "Valve", "Аксессуары", name, name.lower(), "", ""

    return None


def parse_dyson(title: str) -> tuple[str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, color) or None."""
    raw = re.sub(r"\s+", " ", title.strip())
    raw = strip_emoji(raw)
    # Strip Russian category glue from sections: "(Стайлеры)"
    raw = re.sub(r"\([^)]*(?:Стайлер|Пылесос|Воздухооч)[^)]*\)", " ", raw, flags=re.I)
    raw = re.sub(r"\s+", " ", raw).strip()

    is_dysonish = bool(
        re.search(
            r"(?i)\b("
            r"dyson|airwrap|supersonic|airstrait|pencilvac|cinetic|"
            r"hushjet|wash\s*g\d|big\s*ball|"
            r"hd\d+|hs\d+|ht\d+|sv\d+|ph\d+|tp\d+|hu\d+|ds\d+|am\d+|"
            r"v(?:8|10|11|12|15|16)s?\b|gen\s*5\s*detect"
            r")\b",
            raw,
        )
    )
    if not is_dysonish:
        return None
    # Spare parts / section banners — not sellable SKUs
    if re.search(r"(?i)\b(аккумулятор|фильтр|насадк|стайлер\s+dyson\s*$)", raw):
        return None
    # Avoid eating non-Dyson lines that happen to have V15 etc. without vacuum cues —
    # require Dyson brand or known product family tokens
    if not re.search(
        r"(?i)\b(dyson|airwrap|supersonic|airstrait|pencilvac|cinetic|hushjet|"
        r"detect|absolute|fluffy|piston|submarine|big\s*ball|"
        r"hd\d+|hs\d+|ht\d+|ph\d+|tp\d+|hu\d+|am\d+)\b",
        raw,
    ):
        return None
    # Must have a concrete model token (not bare "Dyson" / "Стайлер Dyson")
    if not re.search(
        r"(?i)\b("
        r"airwrap|supersonic|airstrait|pencilvac|cinetic|hushjet|wash\s*g\d|big\s*ball|"
        r"hd\d+|hs\d+|ht\d+|sv\d+|ph\d+|tp\d+|hu\d+|ds\d+|am\d+|"
        r"v(?:8|10|11|12|15|16)s?\b|gen\s*5"
        r")\b",
        raw,
    ):
        return None

    t = re.sub(r"(?i)\bdyson\b", "Dyson", raw)
    # Collapse duplicated product name after section glue
    t = re.sub(r"(?i)\b(airwrap)\s+\1\b", r"\1", t)
    t = re.sub(r"(?i)\b(airstrait)\s+\1\b", r"\1", t)
    t = re.sub(r"(?i)\b(supersonic)\s+\1\b", r"\1", t)
    t = re.sub(r"(?i)\bairwrap\b", "Airwrap", t)
    t = re.sub(r"(?i)\bsupersonic\b", "Supersonic", t)
    t = re.sub(r"(?i)\bairstrait\b", "Airstrait", t)
    t = re.sub(r"(?i)\bpencilvac\b", "PencilVac", t)
    t = re.sub(r"(?i)\bgen\s*5\b", "Gen5", t)
    t = re.sub(r"(?i)\bdetect\b", "Detect", t)
    t = re.sub(r"(?i)\babsolute\b", "Absolute", t)
    t = re.sub(r"(?i)\bfluffy\b", "Fluffy", t)
    t = re.sub(r"(?i)\bpiston\b", "Piston", t)
    t = re.sub(r"(?i)\banimal\b", "Animal", t)
    t = re.sub(r"(?i)\bsubmarine\b", "Submarine", t)
    t = re.sub(r"(?i)\bbig\s*ball\b", "Big Ball", t)
    t = re.sub(r"(?i)\b(?:с\s+)?(?:кейсом|диффузором)\b", " ", t)
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -–—/")

    # Color: slash finishes at end (avoid eating "Long" from Airwrap HS05 Long)
    color = ""
    cm = re.search(
        r"(?i)\b("
        r"[A-Za-z]+(?:\s*/\s*[A-Za-z]+(?:\s+[A-Za-z]+)?)+|"
        r"ceramic\s+pop|jasper\s+plum|kanzan\s+pink|red\s+velvet(?:\s+gold)?|"
        r"apricot\s+topaz|amber\s+silk|vinca\s+blue"
        r")\s*$",
        t,
    )
    if cm:
        color = re.sub(r"\s*/\s*", "/", cm.group(1).strip())
        color = "/".join(
            " ".join(p.title() for p in part.split()) for part in color.split("/")
        )
        color = re.sub(r"(?i)\bCooper\b", "Copper", color)  # supplier typo
        t = t[: cm.start()].strip()
    else:
        # single trailing color
        sm = re.search(r"(?i)\b(black|white|purple|nickel|gold|teal|silver|red)\s*$", t)
        if sm:
            color = sm.group(1).title()
            t = t[: sm.start()].strip()

    t = re.sub(r"\s+", " ", t).strip(" -–—/")
    t = collapse_duplicate_tokens(t)
    if not t.lower().startswith("dyson"):
        # Vacuum/purifier SKUs often omit brand
        if re.search(r"(?i)^\s*(?:v\d+|gen5|pencilvac|ph\d+|tp\d+|hu\d+|am\d+|wash|cinetic|hushjet|hd\d+)", t):
            pass
        else:
            t = f"Dyson {t}"
    # Ensure Supersonic gets HD## if present elsewhere already in t
    device_name = t
    device_name = re.sub(r"(?i)\bhd(\d+)\b", lambda m: f"HD{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\bhs(\d+)\b", lambda m: f"HS{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\bht(\d+)\b", lambda m: f"HT{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\bsv(\d+)\b", lambda m: f"SV{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\bph(\d+)\b", lambda m: f"PH{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\btp(\d+)\b", lambda m: f"TP{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\bhu(\d+)\b", lambda m: f"HU{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\bds(\d+)\b", lambda m: f"DS{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\bam(\d+)\b", lambda m: f"AM{m.group(1)}", device_name)
    device_name = re.sub(r"(?i)\bv(\d+)(s?)\b", lambda m: f"V{m.group(1)}{m.group(2).lower()}", device_name)

    # HD = Supersonic hair dryer; HT = Airstrait straightener; HS = Airwrap
    if re.search(r"(?i)\bhd\d+\b", device_name) or re.search(r"(?i)\bsupersonic\b", device_name):
        category = "Фены"
    elif re.search(r"(?i)\bht\d+\b", device_name) or re.search(r"(?i)\bairstrait\b", device_name):
        category = "Выпрямители"
    elif re.search(r"(?i)\bhs\d+\b", device_name) or re.search(r"(?i)\bairwrap\b", device_name):
        category = "Стайлеры"
    elif re.search(r"(?i)\bam\d+\b", device_name):
        category = "Вентиляторы"
    elif re.search(r"(?i)\b(?:ph\d+|tp\d+|hu\d+|hushjet)\b", device_name) or "воздухо" in device_name.lower():
        category = "Воздухоочистители"
    else:
        category = "Пылесосы"
    return "Dyson", category, device_name, device_name.lower(), color


def parse_yandex(title: str) -> tuple[str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, color) or None."""
    raw = re.sub(r"\s+", " ", title.strip())
    if not re.search(r"(?i)\b(?:яндекс|yandex)\b", raw):
        return None
    color = ""
    cm = re.search(r"\(([^)]+)\)", raw)
    if cm:
        color_raw = cm.group(1).strip()
        color = COLOR_ALIASES.get(color_raw.lower(), color_raw)
        # Title-case Latin; keep Russian mapped via aliases
        if color == color_raw and re.search(r"[A-Za-z]", color_raw):
            color = color_raw.title()
        raw = (raw[: cm.start()] + " " + raw[cm.end() :]).strip()
    raw = re.sub(r"(?i)\byandex\b", "Яндекс", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" -–—/")
    device_name = collapse_duplicate_tokens(raw)
    return "Яндекс", "Умный дом", device_name, device_name.lower(), color


def parse_meta_rayban(title: str) -> tuple[str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, config_extra) or None.

    config_extra carries RW#### · lens · size for display config.
    Unisale often omits the word Meta but still posts RW40xx SKUs.
    """
    raw = re.sub(r"\s+", " ", title.strip())
    m = re.search(
        r"(?i)\bray-?\s*ban(?:\s+meta)?\s+(?P<style>[\w\s]+?)\s+"
        r"(?P<code>RW\d+)\s*"
        r"(?:\((?P<lens>[^)]+)\))?\s*"
        r"(?P<size>[MLS])?\s*$",
        raw,
    )
    if not m:
        # looser: Ray Ban Meta Wayfarer RW4012 (Matte Black/Clear) L
        # or Ray-Ban Wayfarer RW4012 without Meta token
        m = re.search(
            r"(?i)\bray-?\s*ban(?:\s+meta)?\s+(?P<style>.+?)\s+(?P<code>RW\d+)\b"
            r"(?:\s*\((?P<lens>[^)]+)\))?(?:\s+(?P<size>[MLS]))?",
            raw,
        )
    if not m:
        # Bare RW40xx with Ray-Ban somewhere
        m = re.search(
            r"(?i)\bray-?\s*ban\b.*?\b(?P<code>RW\d+)\b"
            r"(?:\s*\((?P<lens>[^)]+)\))?(?:\s+(?P<size>[MLS]))?",
            raw,
        )
        if m:
            style_m = re.search(
                r"(?i)\bray-?\s*ban(?:\s+meta)?\s+(?P<style>.+?)\s+RW\d+",
                raw,
            )
            style = (style_m.group("style") if style_m else "Smart Glasses").strip()
            style = re.sub(r"\s+", " ", style)
            style = _title_case_device(style) if style else "Smart Glasses"
            code = m.group("code").upper()
            lens = (m.group("lens") or "").strip()
            size = (m.group("size") or "").strip().upper()
            device_name = f"Ray-Ban Meta {style}"
            bits = [code]
            if lens:
                bits.append(lens)
            if size:
                bits.append(size)
            return "Meta", "Очки", device_name, device_name.lower(), " · ".join(bits)
        return None
    style = re.sub(r"\s+", " ", m.group("style").strip())
    style = re.sub(r"(?i)^meta\s+", "", style).strip()
    style = _title_case_device(style)
    code = m.group("code").upper()
    lens = (m.group("lens") or "").strip()
    size = (m.group("size") or "").strip().upper()
    device_name = f"Ray-Ban Meta {style}"
    bits = [code]
    if lens:
        bits.append(lens)
    if size:
        bits.append(size)
    extra = " · ".join(bits)
    return "Meta", "Очки", device_name, device_name.lower(), extra


def parse_galaxy_buds(title: str) -> tuple[str, str, str, str] | None:
    """Return (device_name, model_key, color, category) or None."""
    raw = re.sub(r"\s+", " ", title.strip())
    # Do not steal OnePlus/Pixel/etc. Buds lines
    if re.search(
        r"(?i)\b(oneplus|one\s*plus|pixel|xiaomi|huawei|honor|beats|airpods|nothing)\b",
        raw,
    ):
        return None
    m = re.search(
        r"(?i)\b(?:galaxy\s+)?buds\s*(?P<body>\d(?:\s*pro)?(?:\s*fe)?)\b",
        raw,
    )
    if not m:
        return None
    # Bare "Buds N" without Galaxy — only accept if no other brand cue (section may glue Galaxy)
    if not re.search(r"(?i)\bgalaxy\b", raw) and re.search(r"(?i)\b(buds\s*\d)", raw):
        # Still allow Top-style "Buds 4 Pro Black" under Galaxy sections (section prepended upstream)
        pass
    body = re.sub(r"\s+", " ", m.group("body").strip())
    body = re.sub(r"(?i)\bpro\b", "Pro", body)
    body = re.sub(r"(?i)\bfe\b", "FE", body)
    device_name = f"Galaxy Buds {body}"
    device_name = collapse_duplicate_tokens(device_name)
    color = extract_color(raw[m.end() :]) or extract_color(raw)
    return device_name, device_name.lower(), color or "", "Наушники"


def parse_galaxy_watch(title: str) -> tuple[str, str, str, str, str] | None:
    """Return (device_name, model_key, color, connectivity, size) or None."""
    raw = re.sub(r"\s+", " ", title.strip())
    # Avoid Apple Watch Ultra false positives
    if re.search(r"(?i)\bapple\s*watch\b", raw):
        return None
    # Galaxy Watch Ultra (SM-L705F etc.) — must win over Apple `watch ultra` token
    if re.search(r"(?i)\bgalaxy\s+watch\s+ultra\b", raw) or (
        re.search(r"(?i)\bgalaxy\b", raw)
        and re.search(r"(?i)\bwatch\s+ultra\b", raw)
        and re.search(r"(?i)\bsm-[a-z0-9]+", raw)
    ):
        size_m = re.search(r"(?i)\b(\d{2})\s*mm\b", raw)
        size = f"{size_m.group(1)}mm" if size_m else ""
        connectivity = "LTE" if re.search(r"(?i)\blte\b", raw) else ""
        color = extract_color(raw)
        device_name = "Galaxy Watch Ultra" + (f" {size}" if size else "")
        return device_name, device_name.lower(), color or "", connectivity, size
    if not re.search(r"(?i)\b(?:galaxy\s+)?watch\s*8\b", raw):
        return None
    ultra = bool(re.search(r"(?i)\bultra\b", raw))
    classic = bool(re.search(r"(?i)\bclassic\b", raw))
    size_m = re.search(r"(?i)\b(\d{2})\s*mm\b", raw)
    size = f"{size_m.group(1)}mm" if size_m else ""
    connectivity = "LTE" if re.search(r"(?i)\blte\b", raw) else ""
    color = extract_color(raw)
    if ultra:
        device_name = "Galaxy Watch 8 Ultra"
    elif classic:
        device_name = "Galaxy Watch 8 Classic"
    else:
        device_name = "Galaxy Watch 8"
    if size:
        device_name = f"{device_name} {size}"
    return device_name, device_name.lower(), color or "", connectivity, size


def strip_part_marker(text: str | None) -> str:
    """Remove Unisale multipart markers like '(часть 1/2)'."""
    if not text:
        return ""
    cleaned = PART_MARKER_RE.sub(" ", text)
    return re.sub(r"\s+", " ", cleaned).strip(" -/")


def scrub_spec_leaks(text: str) -> str:
    """Drop RAM/GPU fragments that must not appear in device_name."""
    out = CPU_GPU_TUPLE_RE.sub(" ", text)
    out = RAM_STORAGE_RE.sub(" ", out)
    out = STORAGE_RE.sub(" ", out)
    out = RAM_ORPHAN_SLASH_RE.sub(" ", out)
    out = EMBEDDED_PRICE_RE.sub(" ", out)
    # Bare capacity tokens left after unit strip: "iPad … 512 Space Black"
    out = re.sub(r"\b(64|128|256|512|1024|2048)\b", " ", out)
    out = re.sub(r"\s*/\s*", " ", out)
    out = re.sub(r"\s+", " ", out).strip(" -/")
    return out


def parse_galaxy_tab(title: str) -> tuple[str, str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, color, storage) or None.

    Galaxy Tab S10 Lite etc. must never become Apple Watch S10.
    Identity keeps series + variant + connectivity (Wi-Fi / 5G); OEM codes stripped.
    """
    raw = strip_emoji(re.sub(r"\s+", " ", title.strip()))
    if not re.search(r"(?i)\b(?:galaxy\s+)?tab\b|\bsm-x\d+", raw):
        return None
    color = extract_color(raw)
    if color.lower() == "grey":
        color = "Gray"
    storage = extract_storage(raw)
    if not storage:
        return None

    series_m = re.search(
        r"(?i)\btab\s*s\s*(?P<num>\d+)\s*(?P<var>lite|fe(?:\s*\+|\s*plus)?|plus|ultra)?",
        raw,
    )
    if not series_m:
        # Fallback: keep legacy soft parse for odd titles
        t = re.sub(r"(?i)\bsamsung\b", " ", raw)
        t = re.sub(r"(?i)\bgalaxy\b", "Galaxy", t)
        t = re.sub(r"(?i)\btab\s*s\s*(\d+)", r"Tab S\1", t)
        t = re.sub(r"(?i)\btab\b", "Tab", t)
        t = re.sub(r"(?i)\blite\b", "Lite", t)
        t = re.sub(r"(?i)\bfe\b", "FE", t)
        t = re.sub(r"(?i)\bultra\b", "Ultra", t)
        t = re.sub(r"(?i)\bplus\b", "Plus", t)
        if color:
            t = re.sub(rf"(?i)\b{re.escape(color)}\b", " ", t)
        t = re.sub(r"(?i)\b(?:coralred|coraled|coralpink|coral|grey|gray)\b", " ", t)
        t = re.sub(r"(?i)\b(?:sm-)?x\d+\w*\b", " ", t)
        t = RAM_STORAGE_RE.sub(" ", t)
        t = STORAGE_RE.sub(" ", t)
        t = re.sub(r"(?i)\b(?:wi[\s\-]?fi|5g|lte)\b", " ", t)
        t = re.sub(r"\s+", " ", t).strip(" -–—/")
        t = collapse_duplicate_tokens(t)
        if not re.search(r"(?i)\bgalaxy\b", t):
            t = f"Galaxy {t}"
        return "Samsung", "Планшеты", t, t.lower(), color or "", storage

    num = series_m.group("num")
    var_raw = (series_m.group("var") or "").strip().lower()
    if var_raw in {"fe+", "fe plus", "feplus"}:
        variant = "FE+"
    elif var_raw == "fe":
        variant = "FE"
    elif var_raw == "lite":
        variant = "Lite"
    elif var_raw == "plus":
        variant = "Plus"
    elif var_raw == "ultra":
        variant = "Ultra"
    else:
        variant = ""

    code_m = re.search(r"(?i)\b(?:sm-)?x(?P<code>\d{3,4})\w*\b", raw)
    code = (code_m.group("code") if code_m else "").upper()

    has_wifi = bool(re.search(r"(?i)\bwi[\s\-]?fi\b", raw))
    has_cell = bool(re.search(r"(?i)\b(5g|lte|cellular)\b", raw))
    # Samsung tablet codes: …0 Wi-Fi, …6 cellular (X930/X936, X730/X736, …)
    if code:
        if code.endswith("6"):
            has_cell = True
        elif code.endswith("0"):
            has_wifi = True

    connectivity = ""
    if has_cell:
        connectivity = "5G"
    elif has_wifi:
        connectivity = "Wi-Fi"

    parts = ["Galaxy", "Tab", f"S{num}"]
    if variant:
        parts.append(variant)
    if connectivity:
        parts.append(connectivity)
    device_name = " ".join(parts)
    return "Samsung", "Планшеты", device_name, device_name.lower(), color or "", storage


def parse_galaxy_ring(title: str) -> tuple[str, str, str, str, str] | None:
    """Return (device_name, model_key, color, size, model_code) or None.

    OEM finishes: Titanium Black / Titanium Silver / Titanium Gold; sizes 5–13.
    Unisale: `Galaxy Ring Titanium Gold 10 Q500`.
    """
    raw = re.sub(r"\s+", " ", title.strip())
    if not re.search(r"(?i)\bgalaxy\s+ring\b", raw):
        return None
    color = ""
    for finish in ("Titanium Gold", "Titanium Silver", "Titanium Black"):
        if re.search(rf"(?i)\b{re.escape(finish)}\b", raw):
            color = finish
            break
    if not color:
        if re.search(r"(?i)\bgold\b", raw):
            color = "Titanium Gold"
        elif re.search(r"(?i)\bsilver\b", raw):
            color = "Titanium Silver"
        elif re.search(r"(?i)\bblack\b", raw):
            color = "Titanium Black"
    size_m = re.search(r"(?i)\b([5-9]|1[0-3])\b(?!\s*mm)", raw)
    size = size_m.group(1) if size_m else ""
    code_m = re.search(r"(?i)\b(Q\d{3,5})\b", raw)
    model_code = code_m.group(1).upper() if code_m else ""
    device_name = "Galaxy Ring" + (f" {size}" if size else "")
    return device_name, device_name.lower(), color, size, model_code


def parse_macbook_bare(title: str) -> tuple[str, str, str, str] | None:
    """MacBook Pro/Air/Neo continuation titles without the MacBook word.

    Unisale: optional leading Apple order code + color before Mx chip
    (`MC654 Air 13 Silver M4 24/512GB`).
    """
    raw = re.sub(r"\s+", " ", title.strip())
    if re.search(r"(?i)\b(iphone|ipad|airpods|watch)\b", raw):
        return None
    m = MACBOOK_BARE_RE.search(raw)
    if not m:
        return None
    if m.groupdict().get("year"):
        device_name = f"MacBook Neo {m.group('year')}"
    else:
        series = m.group("series").title()
        size = m.group("size")
        chip = m.group("chip")
        tier = (m.group("tier") or "").title()
        # "Pro 14 M1 Pro" → MacBook Pro 14 M1 Pro
        chip_part = f"M{chip}" + (f" {tier}" if tier else "")
        device_name = f"MacBook {series} {size} {chip_part}"
    # Optional year in title
    ym = re.search(r"(?i)\b(20\d{2})\b", raw[m.end() : m.end() + 12])
    if ym and "Neo" not in device_name:
        device_name = f"{device_name} {ym.group(1)}"
    return "Apple", "Ноутбуки", device_name, device_name.lower()


def parse_audio(title: str) -> tuple[str, str, str, str, str] | None:
    """Headphones/speakers: JBL, Marshall, Beats, Bose, Sennheiser, HK, B&W, Beoplay.

    Return (brand, category, device_name, model_key, color) or None.
    Colors often appear in parentheses on Unisale lines.
    """
    raw = re.sub(r"\s+", " ", title.strip())
    raw = strip_emoji(raw)
    raw = re.sub(r"\s*[-–—]\s*\d[\d\s]*\s*$", "", raw).strip()

    brand = ""
    brand_re = None
    if re.search(r"(?i)\bharman\s*kardon\b|\bh/?k\s+onyx\b", raw):
        brand = "Harman Kardon"
        brand_re = r"harman\s*kardon|h/?k"
    elif re.search(r"(?i)\bbowers\s*(?:&|and)\s*wilkins\b|\bb\s*&\s*w\b|\bb&w\b", raw):
        brand = "Bowers & Wilkins"
        brand_re = r"bowers\s*(?:&|and)\s*wilkins|b\s*&\s*w|b&w"
    elif re.search(r"(?i)\bbeoplay\b|\bbang\s*(?:&|and)\s*olufsen\b|\bb\s*&\s*o\b", raw):
        brand = "Beoplay"
        brand_re = r"beoplay|bang\s*(?:&|and)\s*olufsen|b\s*&\s*o"
    elif re.search(r"(?i)\bone\s*plus\b|\boneplus\b", raw) and re.search(r"(?i)\bbuds\b", raw):
        brand = "OnePlus"
        brand_re = r"one\s*plus|oneplus"
    elif re.search(r"(?i)\bjbl\b", raw) or re.search(r"(?i)\bpartybox\b", raw):
        brand = "JBL"
        brand_re = r"jbl"
    elif re.search(r"(?i)\bmarshall\b", raw):
        brand = "Marshall"
        brand_re = r"marshall"
    elif re.search(r"(?i)\bbeats\b", raw):
        brand = "Beats"
        brand_re = r"beats"
    elif re.search(r"(?i)\bbose\b", raw):
        brand = "Bose"
        brand_re = r"bose"
    elif re.search(r"(?i)\bsennheiser\b", raw):
        brand = "Sennheiser"
        brand_re = r"sennheiser"
    else:
        return None

    # Parenthetical color preferred (Unisale: Flip 7 (Purple))
    color = ""
    cm = re.search(r"\(([^)]+)\)", raw)
    if cm:
        color_raw = cm.group(1).strip()
        # Skip packs / region codes / non-color parentheticals
        if not re.search(
            r"(?i)\b(combo|pack|case|anc|usb|mm|gen|type-?c|уценк)\b",
            color_raw,
        ) and not re.fullmatch(r"[A-Za-z]{2}", color_raw):
            key = re.sub(r"\s+", " ", color_raw.lower())
            if key in COLOR_ALIASES:
                color = COLOR_ALIASES[key]
            else:
                got = extract_color(color_raw)
                # Only accept if extract_color covers the paren (no mystery flavors)
                if got and re.sub(r"[^a-z0-9]+", "", got.lower()) in re.sub(
                    r"[^a-z0-9]+", "", key
                ):
                    color = got
        raw = (raw[: cm.start()] + " " + raw[cm.end() :]).strip()
    if not color:
        color = extract_color(raw)

    t = raw
    if brand_re:
        t = re.sub(rf"(?i)\b(?:{brand_re})\b", brand, t, count=1)
    # Normalize common model tokens
    t = re.sub(r"(?i)\bflip\b", "Flip", t)
    t = re.sub(r"(?i)\bpill\b", "Pill", t)
    t = re.sub(r"(?i)\bcharge\b", "Charge", t)
    t = re.sub(r"(?i)\bxtreme\b", "Xtreme", t)
    t = re.sub(r"(?i)\bemberton\b", "Emberton", t)
    t = re.sub(r"(?i)\bwillen\b", "Willen", t)
    t = re.sub(r"(?i)\bmotif\b", "Motif", t)
    t = re.sub(r"(?i)\bacton\b", "Acton", t)
    t = re.sub(r"(?i)\bstanmore\b", "Stanmore", t)
    t = re.sub(r"(?i)\bwoburn\b", "Woburn", t)
    t = re.sub(r"(?i)\bonyx\s+studio\b", "Onyx Studio", t)
    t = re.sub(r"(?i)\baura\s+studio\b", "Aura Studio", t)
    t = re.sub(r"(?i)\bmomentum\b", "Momentum", t)
    t = re.sub(r"(?i)\btrue\s+wireless\b", "True Wireless", t)
    t = re.sub(r"(?i)\bultra\s+open\b", "Ultra Open", t)
    t = re.sub(r"(?i)\bearbuds\b", "Earbuds", t)
    t = re.sub(r"(?i)\bquietcomfort\b", "QuietComfort", t)
    t = re.sub(r"(?i)\bsolo\b", "Solo", t)
    t = re.sub(r"(?i)\bstudio\b", "Studio", t)
    t = re.sub(r"(?i)\bpx\s*7\s*s?2e?\b", "Px7 S2e", t)
    t = re.sub(r"(?i)\bpx\s*8\b", "Px8", t)
    t = re.sub(r"(?i)\bh95\b", "H95", t)
    t = re.sub(r"(?i)\bhx\b", "HX", t)
    t = re.sub(r"(?i)\banc\b", "ANC", t)
    t = re.sub(r"(?i)\bii\b", "II", t)
    t = re.sub(r"(?i)\biii\b", "III", t)

    if color:
        t = re.sub(rf"(?i)\b{re.escape(color)}\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -–—/")
    t = collapse_duplicate_tokens(t)
    device_name = t
    # Ensure brand prefix once
    if brand == "Harman Kardon":
        device_name = re.sub(r"(?i)^(?:harman\s*kardon|h/?k)\s*", "", device_name).strip()
        device_name = f"Harman Kardon {device_name}".strip()
    elif brand == "Bowers & Wilkins":
        device_name = re.sub(r"(?i)^(?:bowers\s*(?:&|and)\s*wilkins|b\s*&\s*w|b&w)\s*", "", device_name).strip()
        device_name = f"Bowers & Wilkins {device_name}".strip()
    elif brand == "Beoplay":
        device_name = re.sub(r"(?i)^(?:beoplay|bang\s*(?:&|and)\s*olufsen|b\s*&\s*o)\s*", "", device_name).strip()
        if not device_name.lower().startswith("beoplay"):
            device_name = f"Beoplay {device_name}".strip()
    elif not device_name.lower().startswith(brand.lower()):
        device_name = f"{brand} {device_name}"

    device_name = re.sub(r"\s+", " ", device_name).strip()
    low = device_name.lower()
    if re.search(
        r"(?i)\b("
        r"motif|momentum|solo|px\s*7|px\s*8|hx|h95|ultra\s+open|"
        r"quietcomfort|\bqc\b|earbuds?|buds|headset|headphone"
        r")\b",
        low,
    ):
        category = "Наушники"
    elif re.search(
        r"(?i)\b("
        r"flip|pill|emberton|onyx|aura|charge|xtreme|boombox|clip|"
        r"acton|stanmore|woburn|willen|soundlink|speaker|studio\s*\d|partybox|\bgo\b"
        r")\b",
        low,
    ):
        category = "Колонки"
    elif brand in {"Beats", "Bose", "Sennheiser", "Beoplay", "Bowers & Wilkins"}:
        category = "Наушники"
    else:
        category = "Колонки"

    # Must have a model token beyond brand alone
    bare = re.sub(rf"(?i)^{re.escape(brand)}\s*", "", device_name).strip()
    if len(bare) < 2:
        return None
    return brand, category, device_name, device_name.lower(), color or ""


def parse_camera(title: str) -> tuple[str, str, str, str, str, str] | None:
    """Fujifilm Instax, DJI Osmo, GoPro Hero, Canon PowerShot.

    Return (brand, category, device_name, model_key, color, extra) or None.
    Instax ≠ Insta360 — never route Instax into insta360 kind.
    """
    raw = re.sub(r"\s+", " ", title.strip())
    raw = strip_emoji(raw)

    # --- Fujifilm Instax (not Insta360) ---
    if re.search(r"(?i)\binstax\b", raw) and not re.search(r"(?i)\binsta\s*360\b", raw):
        color = extract_color(raw)
        t = re.sub(r"(?i)\bfujifilm\b", "", raw)
        t = re.sub(r"(?i)\binstax\b", "Instax", t)
        t = re.sub(r"(?i)\bsquare\b", "Square", t)
        t = re.sub(r"(?i)\blink\b", "Link", t)
        t = re.sub(r"(?i)\bwide\b", "Wide", t)
        t = re.sub(r"(?i)\bmini\b", "Mini", t)
        t = re.sub(r"(?i)\bsq\s*1\b", "SQ1", t)
        t = re.sub(r"(?i)\bsq\s*40\b", "SQ40", t)
        t = re.sub(r"(?i)\bevo\b", "Evo", t)
        # "Instax sq1 Square" → "Instax Square SQ1"
        t = re.sub(r"(?i)\binstax\s+sq1\s+square\b", "Instax Square SQ1", t)
        t = re.sub(r"(?i)\binstax\s+square\s+sq1\b", "Instax Square SQ1", t)
        if color:
            t = re.sub(rf"(?i)\b{re.escape(color)}\b", " ", t)
            t = re.sub(r"(?i)\bchalk\s+white\b", " ", t)
        t = re.sub(r"\([^)]*\)", " ", t)
        t = re.sub(r"\s+", " ", t).strip(" -–—/")
        t = collapse_duplicate_tokens(t)
        if not t.lower().startswith("instax"):
            t = f"Instax {t}"
        device_name = t
        return "Fujifilm", "Фото", device_name, device_name.lower(), color or "", ""

    # --- DJI Osmo (brand optional: suppliers often write bare "Osmo Mobile 7") ---
    if re.search(r"(?i)\bosmo\b", raw) and (
        re.search(r"(?i)\bdji\b", raw)
        or re.search(r"(?i)\bosmo\s+(?:mobile|pocket|action|nano)\b", raw)
    ):
        color = extract_color(raw)
        extra = ""
        cm = re.search(r"\(([^)]+)\)", raw)
        if cm:
            extra = cm.group(1).strip()
            raw = (raw[: cm.start()] + " " + raw[cm.end() :]).strip()
        t = re.sub(r"(?i)\bdji\b", "DJI", raw)
        t = re.sub(r"(?i)\bosmo\b", "Osmo", t)
        # "Osmo 6 Action" / "Osmo Action 6" → Osmo Action 6
        t = re.sub(r"(?i)\bosmo\s+(\d+)\s+action\b", r"Osmo Action \1", t)
        t = re.sub(r"(?i)\bosmo\s+action\s+(\d+)\b", r"Osmo Action \1", t)
        t = re.sub(r"(?i)\bosmo\s+pocket\s+(\d+)\b", r"Osmo Pocket \1", t)
        t = re.sub(r"(?i)\bosmo\s+(\d+)\s+pocket\b", r"Osmo Pocket \1", t)
        t = re.sub(r"(?i)\bmobile\s*(\d+)\s*p?\b", r"Mobile \1", t)
        t = re.sub(r"(?i)\bmobile\b", "Mobile", t)
        t = re.sub(r"(?i)\bcreator\s*combo\b", "Creator Combo", t)
        t = re.sub(r"(?i)\btracker\b", "Tracker", t)
        if color:
            t = re.sub(rf"(?i)\b{re.escape(color)}\b", " ", t)
        t = re.sub(r"\s+", " ", t).strip(" -–—/")
        t = collapse_duplicate_tokens(t)
        if not t.lower().startswith("dji"):
            t = f"DJI {t}"
        return "DJI", "Экшн-камеры", t, t.lower(), color or "", extra

    # --- DJI Mic (Mini 2 / Mic 3 kits) ---
    if re.search(r"(?i)\bdji\b", raw) and re.search(r"(?i)\bmic\b", raw):
        extra = ""
        cm = re.search(r"\(([^)]+)\)", raw)
        if cm:
            extra = cm.group(1).strip()
            raw = (raw[: cm.start()] + " " + raw[cm.end() :]).strip()
        t = re.sub(r"(?i)\bdji\b", "DJI", raw)
        t = re.sub(r"(?i)\bmic\s*mini\b", "Mic Mini", t)
        t = re.sub(r"(?i)\bmic\b", "Mic", t)
        t = re.sub(r"(?i)\btransmitter\b", "Transmitter", t)
        t = re.sub(r"(?i)\bmicrophone\b", "Microphone", t)
        t = re.sub(r"[‼️!]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip(" -–—/")
        t = collapse_duplicate_tokens(t)
        if not t.lower().startswith("dji"):
            t = f"DJI {t}"
        return "DJI", "Аксессуары", t, t.lower(), "", extra

    # --- GoPro Hero ---
    if re.search(r"(?i)\bgopro\b", raw):
        color = extract_color(raw)
        t = re.sub(r"(?i)\bgopro\b", "GoPro", raw)
        t = re.sub(
            r"(?i)\bhero\s*(\d+)\s*(black)?\b",
            lambda m: f"Hero {m.group(1)}" + (" Black" if m.group(2) else ""),
            t,
        )
        if color:
            t = re.sub(rf"(?i)\b{re.escape(color)}\b", " ", t)
        t = re.sub(r"\([^)]*\)", " ", t)
        t = re.sub(r"\s+", " ", t).strip(" -–—/")
        t = collapse_duplicate_tokens(t)
        if not t.lower().startswith("gopro"):
            t = f"GoPro {t}"
        return "GoPro", "Экшн-камеры", t, t.lower(), color or "", ""

    # --- Canon PowerShot ---
    if re.search(r"(?i)\b(?:canon\s+)?powershot\b", raw):
        color = extract_color(raw)
        t = re.sub(r"(?i)\bcanon\b", "Canon", raw)
        t = re.sub(r"(?i)\bpowershot\b", "PowerShot", t)
        t = re.sub(r"(?i)\b(?:ps)?g7\s*x\b", "G7X", t)
        t = re.sub(
            r"(?i)\bmark\s*(iii|ii|i|3|2|1)\b",
            lambda m: "Mark "
            + {"3": "III", "2": "II", "1": "I", "iii": "III", "ii": "II", "i": "I"}[
                m.group(1).lower()
            ],
            t,
        )
        t = re.sub(r"(?i)\bsx\s*740(?:\s*hs)?\b", "SX740 HS", t)
        if color:
            t = re.sub(rf"(?i)\b{re.escape(color)}\b", " ", t)
        t = re.sub(r"\([^)]*\)", " ", t)
        t = re.sub(r"\s+", " ", t).strip(" -–—/")
        t = collapse_duplicate_tokens(t)
        if not t.lower().startswith("canon"):
            t = f"Canon {t}"
        return "Canon", "Фото", t, t.lower(), color or "", ""

    # --- Kodak Charmera (retro keychain cameras; Unisale action-cam section) ---
    if re.search(r"(?i)\bcharmera\b", raw):
        extra = ""
        pm = re.search(r"\(\+?\s*([^)]+)\)", raw)
        if pm:
            extra = pm.group(1).strip()
            raw = re.sub(r"\s+", " ", (raw[: pm.start()] + " " + raw[pm.end() :]).strip())
        if re.search(r"(?i)\b2000\b", raw):
            device_name = "Kodak Charmera 2000"
            if re.search(r"(?i)\bmillennium\b", raw) and "millennium" not in extra.lower():
                extra = " · ".join(x for x in [extra, "Millennium"] if x)
        else:
            device_name = "Kodak Charmera 1987"
        return "Kodak", "Фото", device_name, device_name.lower(), "", extra

    return None


# Insta360 model bodies (order: longer phrases first)
_INSTA360_BODY = (
    r"luna\s*ultra|"
    r"ace\s*pro\s*2|ace\s*pro|ace|"
    r"go\s*ultra|go\s*3s|go\s*3|go\s*2|"
    r"one\s*rs|one\s*x\s*2|one\s*x2|"
    r"mic\s*air|mic|"
    r"link\s*2|link|"
    r"x\s*[2-6]|"
    r"flow|sphere"
)

INSTA360_RE = re.compile(
    rf"(?i)\b(?:insta\s*360|insta360)\s*(?P<body>{_INSTA360_BODY})\b",
)


def _format_insta360_body(body: str) -> str:
    b = re.sub(r"\s+", " ", body.strip().lower())
    b = re.sub(r"^x\s*([2-6])$", r"X\1", b)
    mapping = {
        "luna ultra": "Luna Ultra",
        "ace pro 2": "Ace Pro 2",
        "ace pro": "Ace Pro",
        "ace": "Ace",
        "go ultra": "GO Ultra",
        "go 3s": "GO 3S",
        "go 3": "GO 3",
        "go 2": "GO 2",
        "one rs": "ONE RS",
        "one x 2": "ONE X2",
        "one x2": "ONE X2",
        "mic air": "Mic Air",
        "mic": "Mic",
        "link 2": "Link 2",
        "link": "Link",
        "flow": "Flow",
        "sphere": "Sphere",
    }
    if b in mapping:
        return mapping[b]
    if re.fullmatch(r"x[2-5]", b):
        return b.upper()
    return b.title()


def parse_insta360(title: str) -> tuple[str, str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, color, extra) or None."""
    raw = re.sub(r"\s+", " ", title.strip())
    # Glued supplier forms: "360x5" / "insta360x5" / X6
    raw = re.sub(r"(?i)(360)\s*(x\s*[2-6])", r"\1 \2", raw)
    raw = re.sub(r"(?i)\binsta360(?=x)", "Insta360 ", raw)
    extra = ""
    pm = re.search(r"\(([^)]+)\)", raw)
    if pm:
        extra = pm.group(1).strip()
        raw = re.sub(r"\s+", " ", (raw[: pm.start()] + " " + raw[pm.end() :]).strip())
    m = INSTA360_RE.search(raw)
    if not m:
        return None
    model_part = _format_insta360_body(m.group("body"))
    device_name = f"Insta360 {model_part}"
    color = extract_color(raw[m.end() :]) or extract_color(raw)
    if color and color.lower() == "gray":
        color = "Grey"
    # OEM Luna Ultra finishes: Cosmic Black / Stellar White
    if model_part == "Luna Ultra":
        if color.lower() == "black":
            color = "Cosmic Black"
        elif color.lower() == "white":
            color = "Stellar White"
    category = "Аксессуары" if model_part.lower().startswith(("mic", "link", "flow")) else "Экшн-камеры"
    return "Insta360", category, device_name, device_name.lower(), color or "", extra


def is_airpods_spare_part(title: str) -> bool:
    """Single ear / L/R spare parts must never reach the storefront."""
    if not re.search(r"(?i)\bairpods?\b", title):
        return False
    if re.search(r"(?i)\b(ухо|уш[аи]|левое|правое|left|right)\b", title):
        return True
    # Lone L/R token: "AirPods Pro 2 L", "AirPods 4 R ANC"
    if re.search(r"(?i)(?:^|[\s·|/])([LR])(?:[\s·|/]|$)", title):
        return True
    return False


def is_airpods_case_or_box(title: str) -> bool:
    """Charging case / box sold separately from the earbuds set."""
    if not re.search(r"(?i)\bairpods?\b", title):
        return False
    return bool(re.search(r"(?i)(?:кейс|\bcase\b|\bbox\b)", title))


def parse_airpods_case(title: str) -> tuple[str, str, str, str] | None:
    """Return (brand, category, device_name, model_key) for AirPods case/box SKUs."""
    if not is_airpods_case_or_box(title):
        return None
    # Drop case markers so parse_airpods can resolve generation (Pro 3 / 4 ANC / …).
    stripped = re.sub(r"(?i)(?:кейс|\bcase\b|\bbox\b|type[\s\-]?c|usb[\s\-]?c)", " ", title)
    stripped = re.sub(r"[/|]+", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    base = parse_airpods(stripped)
    if base is None:
        return None
    brand, _category, device_name, _model = base
    case_name = f"{device_name} Case"
    return brand, "Аксессуары", case_name, case_name.lower()


def parse_airpods(title: str) -> tuple[str, str, str, str] | None:
    """Return (brand, category, device_name, model_key) or None.

    AirPods 4 aliases:
      - без шумодава → AirPods 4
      - ANC / шумодав / шумоподавление → AirPods 4 ANC
    Max line is handled by parse_airpods_max.
    """
    raw = strip_emoji(re.sub(r"\s+", " ", title.strip()))
    if not re.search(r"(?i)\bairpods?\b", raw):
        return None
    if re.search(r"(?i)\bairpods?\s*max\b", raw):
        return None

    if re.search(r"(?i)\bpro\s*3\b", raw):
        device_name = "AirPods Pro 3"
    elif re.search(r"(?i)\bpro\s*2\b", raw):
        device_name = "AirPods Pro 2"
    elif re.search(r"(?i)\bpro\b", raw):
        device_name = "AirPods Pro"
    elif re.search(r"(?i)\bairpods?\s*4\b|\b4\s*(?:anc|без|с\s*шумо)", raw) or re.search(
        r"(?i)\bairpods?\b.*\b4\b|\b4\b.*\bairpods?\b", raw
    ):
        explicit_no_anc = bool(re.search(r"(?i)без\s*шумо", raw))
        has_anc = bool(
            re.search(r"(?i)\banc\b|шумодав|шумоподав", raw)
        )
        if explicit_no_anc:
            device_name = "AirPods 4"
        elif has_anc:
            device_name = "AirPods 4 ANC"
        else:
            device_name = "AirPods 4"
    elif re.search(r"(?i)\bairpods?\s*3\b", raw):
        device_name = "AirPods 3"
    elif re.search(r"(?i)\bairpods?\s*2\b", raw):
        device_name = "AirPods 2"
    else:
        # Bare "AirPods" without generation — not specific enough
        return None

    return "Apple", "Наушники", device_name, device_name.lower()


def parse_airpods_max(title: str) -> tuple[str, str, str, str, str] | None:
    """Return (brand, category, device_name, model_key, color) or None.

    Generations (Bests re:sale naming):
      - AirPods Max Lightning — 2020 gen1 Lightning
      - AirPods Max USB-C — 2024 gen1 Type-C (suppliers often write "Max 2 USB-C")
      - AirPods Max 2 — 2026 gen2 H2 (usually marked 2026)
    """
    if not re.search(r"(?i)\bairpods?\s*max\b", title):
        return None

    is_usbc = bool(
        re.search(
            r"(?i)("
            r"\busb-?c\b|"
            r"\btype-?c\b|"
            r"\bтайп\s*-?[cс]\b|"
            r"\bтайпси\b|"
            r"\btype\s*c\b|"
            r"\b2024\b"
            r")",
            title,
        )
    )
    is_2026 = bool(re.search(r"(?i)\b2026\b", title))
    is_gen2_word = bool(
        re.search(
            r"(?i)("
            r"\bairpods?\s*max\s*2\b|"
            r"\bmax\s*2\b|"
            r"\bgen(?:eration)?\s*2\b|"
            r"\b2\s*(?:gen|generation|gen\.?)\b|"
            r"\b2\s*-?\s*е?\s*пок|"
            r"\bвторо[ей]\s*пок|"
            r"\bh2\b"
            r")",
            title,
        )
    )
    is_lightning = bool(
        re.search(
            r"(?i)("
            r"\blightning\b|"
            r"\bлайтнинг\b|"
            r"\b2020\b"
            r")",
            title,
        )
    )

    # Priority: connector/year beats supplier "Max 2 USB-C" slang for 2024 refresh
    if is_usbc and not is_2026:
        device_name = "AirPods Max USB-C"
    elif is_2026 or (is_gen2_word and not is_usbc):
        device_name = "AirPods Max 2"
    elif is_lightning:
        device_name = "AirPods Max Lightning"
    else:
        # Top re:sale style: "AirPods Max Blue" — generation unknown
        device_name = "AirPods Max"

    color = extract_color(title)
    key = re.sub(r"\s+", " ", (color or "").lower()).strip()
    if key == "grey":
        key = "gray"

    modern = {
        "black": "Midnight",
        "midnight": "Midnight",
        "starlight": "Starlight",
        "blue": "Blue",
        "purple": "Purple",
        "orange": "Orange",
    }
    legacy = {
        "black": "Space Gray",
        "space gray": "Space Gray",
        "gray": "Space Gray",
        "silver": "Silver",
        "sky blue": "Sky Blue",
        "blue": "Sky Blue",
        "pink": "Pink",
        "green": "Green",
    }

    # Color palette still helps Lightning vs modern when gen unknown
    if device_name == "AirPods Max" and key in {
        "silver",
        "pink",
        "green",
        "sky blue",
        "space gray",
        "gray",
    }:
        device_name = "AirPods Max Lightning"

    # Top re:sale style "AirPods Max Blue" — generation ambiguous → caller must reject
    if device_name == "AirPods Max":
        return None

    if device_name == "AirPods Max Lightning":
        color = legacy.get(key, color.title() if color else "")
    else:
        # USB-C / Max 2
        color = modern.get(key, color.title() if color else "")

    return "Apple", "Наушники", device_name, device_name.lower(), color or ""


def classify_offer(title: str, *, section: str | None = None) -> OfferIdentity:
    section = normalize_section_header(section) or None
    working = strip_part_marker(title.strip())
    # Cyrillic lookalike «е» in Latin color tokens (Orangе → Orange)
    working = re.sub(r"(?i)orang\u0435", "Orange", working)
    working = re.sub(r"(?i)\bновые\b", " ", working)
    working = re.sub(r"\s+", " ", working).strip()
    if should_prepend_section(section, working):
        working = strip_part_marker(f"{section} {working}".strip())
        working = re.sub(r"(?i)\bновые\b", " ", working)
        working = re.sub(r"\s+", " ", working).strip()

    # Detect ASIS before noise strip (markers get removed from the working title)
    asis_from = " ".join(x for x in [working, section or "", title] if x)
    asis_kind = asis_tier(asis_from)
    condition = asis_kind or ""

    if is_junk_offer(working):
        cleaned = clean_offer_title(working)
        return _rejected(model=cleaned[:80].lower(), display_title=cleaned or working, reject_reason="junk_or_noise")

    if is_airpods_spare_part(working) or is_airpods_spare_part(title):
        cleaned = clean_offer_title(working)
        return _rejected(
            model=cleaned[:80].lower(),
            display_title=cleaned or working,
            reject_reason="airpods_spare_part",
        )

    if is_marketing_noise(working):
        return _rejected(
            model=clean_offer_title(working)[:80].lower(),
            display_title=working,
            reject_reason="noise_or_unrecognized",
        )

    # User-directed: drop iMacs from the storefront. Mac mini under the same
    # Unisale section ("iMac \\ Mac mini") must still publish.
    if re.search(r"(?i)\bimac\b", working) and not re.search(r"(?i)\bmac\s*mini\b", working):
        cleaned = clean_offer_title(working)
        return _rejected(
            model=cleaned[:80].lower() or "imac",
            display_title=cleaned or working,
            reject_reason="imac_excluded",
        )

    # Cables / lightning accessories must not become MacBook SKUs
    if re.search(r"(?i)\bmacbook\b", working) and re.search(
        r"(?i)\b(кабел|cable|lightning|type[\s\-]?c)\b", working
    ):
        if not re.search(r"(?i)\b(air|pro|neo)\s*1?[3-6]?\b|\bm\d+\b", working):
            cleaned = clean_offer_title(working)
            return _rejected(
                model=cleaned[:80].lower(),
                display_title=cleaned or working,
                reject_reason="noise_or_unrecognized",
            )

    region = extract_region(working)
    sim_text = extract_sim_text(working)
    # Color from pre-clean text too (Deep Blue still present)
    color = extract_color(working)
    working = clean_offer_title(working)
    if region is None:
        region = extract_region(working)
    if sim_text is None:
        sim_text = extract_sim_text(working)
    if not color:
        color = extract_color(working)

    storage = extract_storage(working)
    ram = extract_ram(working)

    brand = ""
    device_category = ""
    device_name = ""
    kind = OfferKind.unknown
    model = ""
    sim: SimType | None = None
    band = ""

    iphone_model = normalize_iphone_model(working)
    galaxy_model = normalize_galaxy_model(working)
    other_matches = list(APPLE_OTHER_RE.finditer(working))
    # Prefer concrete product tokens over bare `watch ultra` when Galaxy is present
    if re.search(r"(?i)\bgalaxy\b", working):
        other_matches = [m for m in other_matches if "watch" not in m.group(0).lower()]
    other = max(other_matches, key=lambda m: len(m.group(0))) if other_matches else None
    watch = parse_apple_watch(working) or parse_apple_watch(title)
    galaxy_buds = parse_galaxy_buds(working) or parse_galaxy_buds(title)
    galaxy_watch = parse_galaxy_watch(working) or parse_galaxy_watch(title)
    galaxy_tab = parse_galaxy_tab(working) or parse_galaxy_tab(title)
    galaxy_ring = parse_galaxy_ring(working) or parse_galaxy_ring(title)
    sony = (
        parse_sony_ps5(working)
        or parse_sony_ps5(title)
        or (parse_sony_ps5(f"{section} {working}") if section else None)
    )
    android = (
        parse_android(working)
        or parse_android(title)
        or (parse_android(f"{section} {working}") if section else None)
    )
    gaming = (
        parse_gaming(working)
        or parse_gaming(title)
        or (parse_gaming(f"{section} {working}") if section else None)
    )
    dyson = (
        parse_dyson(working)
        or parse_dyson(title)
        or (parse_dyson(f"{section} {working}") if section else None)
    )
    yandex = (
        parse_yandex(working)
        or parse_yandex(title)
        or (parse_yandex(f"{section} {working}") if section else None)
    )
    meta = (
        parse_meta_rayban(working)
        or parse_meta_rayban(title)
        or (parse_meta_rayban(f"{section} {working}") if section else None)
    )
    audio = (
        parse_audio(working)
        or parse_audio(title)
        or (parse_audio(f"{section} {working}") if section else None)
    )
    camera = (
        parse_camera(working)
        or parse_camera(title)
        or (parse_camera(f"{section} {working}") if section else None)
    )
    macbook_bare = parse_macbook_bare(working) or parse_macbook_bare(title)
    insta = (
        parse_insta360(working)
        or parse_insta360(title)
        or (parse_insta360(f"{section} {working}") if section else None)
    )
    airpods_max = (
        parse_airpods_max(working)
        or parse_airpods_max(title)
        or (parse_airpods_max(f"{section} {working}") if section else None)
    )
    airpods_case = None
    airpods = None
    if not airpods_max:
        airpods_case = (
            parse_airpods_case(working)
            or parse_airpods_case(title)
            or (parse_airpods_case(f"{section} {working}") if section else None)
        )
        if not airpods_case:
            airpods = (
                parse_airpods(working)
                or parse_airpods(title)
                or (parse_airpods(f"{section} {working}") if section else None)
            )

    extra = ""
    ring_model_code = ""

    # Samsung/Galaxy BEFORE iPhone — otherwise "S26 Ultra 16/1TB" becomes iPhone 16
    if galaxy_model:
        kind = OfferKind.samsung
        brand = "Samsung"
        device_category = category_for_phone(asis_tier_name=asis_kind)
        model = galaxy_model
        device_name = format_device_name(model)
        color = normalize_galaxy_a_color(model, color)
        if not storage and not ram:
            return _rejected(
                kind=kind,
                model=model,
                storage=storage,
                color=color,
                region=region,
                display_title=device_name,
                reject_reason="samsung_missing_storage",
            )
        if not color:
            return _rejected(
                kind=kind,
                model=model,
                storage=storage,
                color=color,
                region=region,
                display_title=build_display_title(device_name, build_config(ram=ram, storage=storage)),
                reject_reason="samsung_missing_color",
            )
        sim = sim_text
    elif galaxy_buds:
        kind = OfferKind.samsung
        brand = "Samsung"
        device_name, model, buds_color, device_category = galaxy_buds
        if buds_color:
            color = buds_color
        storage = ""
        ram = ""
        if not color:
            return _rejected(
                kind=kind,
                model=model,
                color="",
                display_title=device_name,
                reject_reason="samsung_missing_color",
            )
    elif galaxy_watch:
        kind = OfferKind.samsung
        brand = "Samsung"
        device_category = "Часы"
        device_name, model, watch_color, connectivity, _size = galaxy_watch
        if watch_color:
            color = watch_color
        storage = ""
        ram = ""
        extra = connectivity
        if not color:
            return _rejected(
                kind=kind,
                model=model,
                color="",
                display_title=device_name,
                reject_reason="samsung_missing_color",
            )
    elif galaxy_tab:
        kind = OfferKind.samsung
        brand, device_category, device_name, model, tab_color, storage = galaxy_tab
        if tab_color:
            color = tab_color
        ram = ""
        sim = None
        if not color:
            return _rejected(
                kind=kind,
                model=model,
                storage=storage,
                color="",
                display_title=device_name,
                reject_reason="samsung_missing_color",
            )
    elif galaxy_ring:
        kind = OfferKind.samsung
        brand = "Samsung"
        device_category = "Аксессуары"
        device_name, model, ring_color, ring_size, ring_code = galaxy_ring
        if ring_color:
            color = ring_color
        storage = ""
        ram = ""
        if ring_code:
            ring_model_code = ring_code
        if ring_size:
            extra = f"Size {ring_size}"
        if not color:
            return _rejected(
                kind=kind,
                model=model,
                color="",
                display_title=device_name,
                reject_reason="samsung_missing_color",
            )
    elif iphone_model:
        kind = OfferKind.iphone
        brand = "Apple"
        device_category = category_for_phone(asis_tier_name=asis_kind)
        model = iphone_model
        device_name = format_device_name(model)
        color = normalize_pro_titanium_color(model, color)
        color = normalize_air_color(model, color)
        color = normalize_17e_color(model, color)
        color = normalize_base_17_color(model, color)
        color = normalize_starlight_white_color(model, color)
        if not storage:
            return _rejected(
                kind=kind,
                model=model,
                storage=storage,
                color=color,
                region=region,
                display_title=device_name,
                reject_reason="iphone_missing_storage",
            )
        if not is_allowed_iphone_storage(model, storage):
            return _rejected(
                kind=kind,
                model=model,
                storage=storage,
                color=color,
                region=region,
                display_title=build_display_title(device_name, build_config(storage=storage, color=color)),
                reject_reason="iphone_invalid_storage",
            )
        if not color:
            return _rejected(
                kind=kind,
                model=model,
                storage=storage,
                color=color,
                region=region,
                display_title=build_display_title(device_name, build_config(storage=storage)),
                reject_reason="iphone_missing_color",
            )
        sim = infer_sim(model, region, sim_text)
        if sim is None:
            cfg = build_config(storage=storage, color=color)
            return _rejected(
                kind=kind,
                model=model,
                storage=storage,
                color=color,
                region=region,
                display_title=build_display_title(device_name, cfg),
                reject_reason="iphone_missing_sim",
            )
    elif watch and not re.search(r"(?i)\bgalaxy\s*watch\b", working):
        kind = OfferKind.apple_other
        brand = "Apple"
        device_category = "Часы"
        device_name, model, watch_color, band = watch
        # Never keep extract_color from the band (e.g. White Ocean Band → White).
        color = watch_color
        # Phone/tablet RAM·storage must never stick to watch identities
        storage = ""
        ram = ""
        if device_name.startswith("Apple Watch Ultra"):
            if not color:
                return _rejected(
                    kind=kind,
                    model=model,
                    color="",
                    display_title=build_display_title(
                        device_name, build_config(band=band)
                    ),
                    reject_reason="watch_missing_case_color",
                )
            if color.lower() not in {"black titanium", "natural titanium"}:
                return _rejected(
                    kind=kind,
                    model=model,
                    color=color,
                    display_title=build_display_title(
                        device_name, build_config(color=color, band=band)
                    ),
                    reject_reason="watch_invalid_case_color",
                )
        else:
            # Series / SE: require case size (mm) and case color for storefront
            if not re.search(r"(?i)\b\d{2}\s*mm\b", device_name):
                return _rejected(
                    kind=kind,
                    model=model,
                    color=color,
                    display_title=build_display_title(
                        device_name, build_config(color=color, band=band)
                    ),
                    reject_reason="watch_missing_size",
                )
            if not color:
                return _rejected(
                    kind=kind,
                    model=model,
                    color="",
                    display_title=build_display_title(
                        device_name, build_config(band=band)
                    ),
                    reject_reason="watch_missing_case_color",
                )
    elif sony:
        kind = OfferKind.sony
        brand, device_category, device_name, model, sony_color = sony
        if sony_color:
            color = sony_color
        # Console names already embed capacity/revision — don't duplicate in config
        if device_category in {"Игровые консоли", "VR"}:
            storage = ""
            ram = ""
    elif android:
        kind = OfferKind.android
        brand, device_category, device_name, model, and_color, connectivity = android
        if and_color:
            color = and_color
        extra = connectivity
        sim = None  # Android: region flag optional metadata only
        if not color:
            return _rejected(
                kind=kind,
                model=model,
                storage=storage,
                color="",
                region=region,
                display_title=build_display_title(device_name, build_config(ram=ram, storage=storage)),
                reject_reason="android_missing_color",
            )
    elif gaming:
        kind = OfferKind.gaming
        brand, device_category, device_name, model, game_color, game_storage = gaming
        if game_color:
            color = game_color
        if game_storage:
            storage = game_storage
        else:
            storage = ""
        ram = ""
        sim = None
    elif dyson:
        kind = OfferKind.dyson
        brand, device_category, device_name, model, dyson_color = dyson
        if dyson_color:
            color = dyson_color
        storage = ""
        ram = ""
        sim = None
    elif yandex:
        kind = OfferKind.yandex
        brand, device_category, device_name, model, ya_color = yandex
        if ya_color:
            color = ya_color
        storage = ""
        ram = ""
        sim = None
    elif meta:
        kind = OfferKind.meta
        brand, device_category, device_name, model, meta_extra = meta
        color = ""
        storage = ""
        ram = ""
        sim = None
        extra = meta_extra
    elif audio:
        kind = OfferKind.audio
        brand, device_category, device_name, model, audio_color = audio
        if audio_color:
            color = audio_color
        storage = ""
        ram = ""
        sim = None
        if not color:
            return _rejected(
                kind=kind,
                model=model,
                color="",
                display_title=device_name,
                reject_reason="audio_missing_color",
            )
    elif camera:
        kind = OfferKind.camera
        brand, device_category, device_name, model, cam_color, cam_extra = camera
        if cam_color:
            color = cam_color
        storage = ""
        ram = ""
        sim = None
        extra = cam_extra
    elif insta:
        kind = OfferKind.insta360
        brand, device_category, device_name, model, insta_color, insta_extra = insta
        if insta_color:
            color = insta_color
        storage = ""
        ram = ""
        sim = None
        extra = insta_extra
    elif airpods_max:
        kind = OfferKind.apple_other
        brand, device_category, device_name, model, max_color = airpods_max
        device_category = category_for_headphones(asis_tier_name=asis_kind)
        if max_color:
            color = max_color
        storage = ""
        ram = ""
        sim = None
    elif airpods_case:
        kind = OfferKind.apple_other
        brand, device_category, device_name, model = airpods_case
        color = ""
        storage = ""
        ram = ""
        sim = None
    elif airpods:
        kind = OfferKind.apple_other
        brand, device_category, device_name, model = airpods
        device_category = category_for_headphones(asis_tier_name=asis_kind)
        color = ""
        storage = ""
        ram = ""
        sim = None
    elif re.search(r"(?i)\bairpods?\s*max\b", f"{working} {title}"):
        # Ambiguous Max line (e.g. Top re:sale "AirPods Max Blue") — need year/USB-C/Lightning
        return _rejected(
            kind=OfferKind.apple_other,
            model="airpods max",
            color=color,
            display_title=clean_offer_title(working) or working,
            reject_reason="airpods_max_missing_generation",
        )
    elif other:
        token = other.group(0)
        # Incomplete watch lines must not publish via the generic Apple-other path
        if re.search(r"(?i)(?:apple\s*watch|watch\s*ultra)", token):
            return _rejected(
                kind=OfferKind.apple_other,
                model="apple watch",
                color=color,
                display_title=clean_offer_title(working) or working,
                reject_reason="watch_incomplete",
            )
        kind = OfferKind.apple_other
        brand, device_category, device_name, model = _apple_other_device_name(token, working)
    elif macbook_bare:
        kind = OfferKind.apple_other
        brand, device_category, device_name, model = macbook_bare
    else:
        return _rejected(
            model=re.sub(r"\s+", " ", working.lower())[:80],
            storage=storage,
            color=color,
            region=region,
            display_title=working,
            reject_reason="noise_or_unrecognized",
        )

    model_code = ""
    if kind == OfferKind.apple_other and device_category in {"Планшеты", "Ноутбуки", "Аксессуары", "ТВ"}:
        model_code = extract_apple_model_code(working) or extract_apple_model_code(title)
    elif ring_model_code:
        model_code = ring_model_code

    config = build_config(
        ram=ram,
        storage=storage,
        color=color,
        sim=sim,
        band=band,
        model_code=model_code,
        extra=extra,
    )
    display = build_display_title(device_name, config)
    key = identity_key(
        model,
        storage,
        color,
        sim,
        ram=ram,
        condition=condition,
        band=band,
        model_code=model_code,
        extra=extra,
    )
    return OfferIdentity(
        kind=kind,
        brand=brand,
        device_category=device_category,
        device_name=device_name,
        model=model,
        storage=storage,
        color=color,
        sim=sim,
        region=region,
        ram=ram,
        config=config,
        display_title=display,
        identity_key=key,
        publish=True,
        band=band,
        model_code=model_code,
    )
