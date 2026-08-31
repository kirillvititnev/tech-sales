"""Catalog / admin product search: tokenized AND-match over a rich haystack."""

from __future__ import annotations

import re

from sqlalchemy import func

from apps.api.models.catalog import Product
from apps.api.security import escape_like

_CAPACITY_RE = re.compile(r"(?i)^(\d+)\s*(gb|tb)$")
_SPLIT_RE = re.compile(r"[^\w]+", re.UNICODE)


def search_tokens(q: str | None) -> list[str]:
    """Split query into AND-tokens; expand 256GB → also 256, 1TB → also 1."""
    if not q:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in _SPLIT_RE.split(q.strip()):
        token = part.strip().casefold()
        if not token:
            continue
        candidates = [token]
        cap = _CAPACITY_RE.fullmatch(token)
        if cap:
            candidates.append(cap.group(1))
        for cand in candidates:
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
    return out


def _attr(key: str):
    return Product.attributes[key].astext


def search_haystack():
    """Storefront-visible text fields + bare storage digits for capacity search.

    Slug is omitted — its hex suffix (…d17e…) false-positives short numeric tokens.
    """
    storage = _attr("storage")
    config = _attr("config")
    storage_bare = func.regexp_replace(func.coalesce(storage, ""), r"(?i)\s*(gb|tb)\b", "", "g")
    config_bare = func.regexp_replace(func.coalesce(config, ""), r"(?i)\s*(gb|tb)\b", "", "g")
    title_flat = func.replace(func.replace(Product.title, "·", " "), "/", " ")
    return func.concat_ws(
        " ",
        title_flat,
        Product.brand,
        _attr("device_name"),
        _attr("device_category"),
        config,
        config_bare,
        storage,
        storage_bare,
        _attr("color"),
        _attr("sim"),
        _attr("ram"),
        _attr("band"),
        _attr("model"),
        _attr("model_code"),
        _attr("condition"),
        _attr("kind"),
        _attr("extra"),
    )


def apply_search_tokens(stmt, q: str | None):
    """AND-match every search token against the product haystack."""
    haystack = search_haystack()
    for token in search_tokens(q):
        if token.isdigit():
            # Word-ish boundary so 17 ≠ d17e; allow optional GB/TB after capacity digits
            pattern = rf"(^|[^0-9a-z]){re.escape(token)}(?:\s*(?:gb|tb))?([^0-9a-z]|$)"
            stmt = stmt.where(haystack.op("~*")(pattern))
        else:
            stmt = stmt.where(haystack.ilike(f"%{escape_like(token)}%", escape="\\"))
    return stmt
