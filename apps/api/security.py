"""Auth, rate limits, output filtering — defensive controls used by the API."""

from __future__ import annotations

import hmac
import hashlib
import os
import secrets
import time
from collections import defaultdict
from threading import Lock
from typing import Any
from urllib.parse import parse_qsl, unquote, urlparse

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from apps.api.config import get_settings

http_basic = HTTPBasic(auto_error=False)

WEAK_SECRETS = frozenset(
    {
        "",
        "whiteshop",
        "change-me-admin",
        "changeme-redis",
        "change-me-in-production",
        "__GENERATE__",
    }
)


def is_weak_secret(value: str | None, *, min_len: int = 12) -> bool:
    if value is None:
        return True
    text = value.strip()
    if text in WEAK_SECRETS:
        return True
    return len(text) < min_len


def _password_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    if parsed.password is None:
        return None
    return unquote(parsed.password)


def runtime_secret_problems() -> list[str]:
    settings = get_settings()
    problems: list[str] = []
    if is_weak_secret(settings.admin_password):
        problems.append("ADMIN_PASSWORD is missing or a known default")
    if is_weak_secret(_password_from_url(settings.database_url)):
        problems.append("DATABASE_URL uses a known-default Postgres password")
    if is_weak_secret(_password_from_url(settings.redis_url)):
        problems.append("REDIS_URL has no password or a known default")
    if is_weak_secret(settings.api_secret_key):
        problems.append("API_SECRET_KEY is missing or a known default")
    return problems


def assert_runtime_secrets() -> None:
    """Refuse to boot with placeholder credentials (WS-R1). Tests set ALLOW_INSECURE_DEFAULTS=1."""
    if os.environ.get("ALLOW_INSECURE_DEFAULTS") == "1":
        return
    problems = runtime_secret_problems()
    if problems:
        raise RuntimeError(
            "Refusing to start with insecure defaults. Run `make env`. " + "; ".join(problems)
        )

PUBLIC_PRODUCT_ATTR_KEYS = (
    "device_category",
    "device_name",
    "storage",
    "ram",
    "color",
    "sim",
    "band",
    "config",
    "kind",
)


def escape_like(term: str) -> str:
    """Neutralize LIKE wildcards so user search cannot broaden the query."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def public_product_attributes(raw: dict | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key in PUBLIC_PRODUCT_ATTR_KEYS:
        value = raw.get(key)
        if isinstance(value, str) and value:
            out[key] = value
    return out


def admin_credentials_configured() -> bool:
    settings = get_settings()
    return bool(settings.admin_username and settings.admin_password)


def admin_credentials_valid(username: str, password: str) -> bool:
    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        return False
    user_ok = hmac.compare_digest(username, settings.admin_username)
    pass_ok = hmac.compare_digest(password, settings.admin_password)
    return user_ok and pass_ok


async def require_admin(
    credentials: HTTPBasicCredentials | None = Depends(http_basic),
) -> str:
    if not admin_credentials_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Админка не сконфигурирована (ADMIN_USERNAME / ADMIN_PASSWORD)",
        )
    if credentials is None or not admin_credentials_valid(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется вход в админку",
            headers={"WWW-Authenticate": 'Basic realm="White Shop admin"'},
        )
    return credentials.username


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict[str, str] | None:
    """Validate Mini App initData HMAC. Returns parsed fields or None."""
    if not init_data or not bot_token:
        return None
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received = pairs.pop("hash", "")
    if not received:
        return None
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, received):
        return None
    return pairs


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_sec: float) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - window_sec
            bucket[:] = [t for t in bucket if t >= cutoff]
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    # Prefer hop-by-hop headers set by Cloudflare; do not trust X-Forwarded-For.
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_rule(method: str, path: str) -> tuple[str, int, float] | None:
    """Return (bucket_suffix, limit, window_sec) or None to skip."""
    if path == "/health":
        return None
    if method == "POST" and path.rstrip("/") == "/api/v1/orders":
        return ("orders", 8, 60.0)
    if method == "GET" and "/api/v1/orders/by-number/" in path:
        return ("order-lookup", 20, 60.0)
    if path.startswith("/api/v1/admin"):
        return ("admin", 60, 60.0)
    return ("global", 240, 60.0)


def check_rate_limit(request: Request) -> None:
    rule = rate_limit_rule(request.method, request.url.path)
    if rule is None:
        return
    suffix, limit, window = rule
    key = f"{client_ip(request)}:{suffix}"
    if not limiter.allow(key, limit, window):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов, повторите позже",
            headers={"Retry-After": "60"},
        )


def new_order_access_token() -> str:
    return secrets.token_urlsafe(32)
