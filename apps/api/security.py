"""Auth, rate limits, output filtering — defensive controls used by the API."""

from __future__ import annotations

import hmac
import hashlib
import ipaddress
import os
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass
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
    if is_weak_secret(settings.api_secret_key, min_len=32):
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


def admin_csrf_allowed(request: Request) -> bool:
    """Fetch Metadata: browsers send Sec-Fetch-Site; curl/tests omit it."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return True
    path = request.url.path
    if not path.startswith("/api/v1/admin"):
        return True
    site = (request.headers.get("sec-fetch-site") or "").strip().lower()
    if site in {"", "none", "same-origin"}:
        return True
    origin = (request.headers.get("origin") or "").rstrip("/")
    allowed = {item.rstrip("/") for item in get_settings().cors_origin_list}
    return bool(origin and origin in allowed)


async def require_admin(
    request: Request,
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
    if not admin_csrf_allowed(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недопустимый источник запроса",
        )
    return credentials.username


def _auth_date_fresh(pairs: dict[str, str], *, max_age_sec: int | None) -> bool:
    if max_age_sec is None:
        return True
    raw = pairs.get("auth_date")
    try:
        ts = int(raw or "")
    except ValueError:
        return False
    return abs(time.time() - ts) <= max_age_sec


def verify_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_sec: int | None = None,
) -> dict[str, str] | None:
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
    if not _auth_date_fresh(pairs, max_age_sec=max_age_sec):
        return None
    return pairs


def verify_telegram_login_widget(
    fields: dict[str, str],
    bot_token: str,
    *,
    max_age_sec: int = 86400,
) -> dict[str, str] | None:
    """Validate Telegram Login Widget payload (HMAC-SHA256 of bot token SHA256)."""
    if not bot_token:
        return None
    received = fields.get("hash", "")
    if not received:
        return None
    check = {k: str(v) for k, v in fields.items() if k != "hash" and v is not None}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(check.items()))
    secret = hashlib.sha256(bot_token.encode()).digest()
    digest = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, received):
        return None
    if not _auth_date_fresh(check, max_age_sec=max_age_sec):
        return None
    return check


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_sec: float) -> "RateDecision":
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - window_sec
            bucket[:] = [t for t in bucket if t >= cutoff]
            retry_after = 0
            if len(bucket) >= limit:
                oldest = bucket[0] if bucket else now
                retry_after = max(1, int(oldest + window_sec - now) + 1)
                remaining = 0
                allowed = False
            else:
                bucket.append(now)
                remaining = max(0, limit - len(bucket))
                allowed = True
            reset_epoch = int(time.time() + window_sec)
            return RateDecision(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                retry_after=retry_after,
                reset_epoch=reset_epoch,
            )

    def allow(self, key: str, limit: int, window_sec: float) -> bool:
        return self.check(key, limit, window_sec).allowed


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    reset_epoch: int


limiter = SlidingWindowLimiter()
_redis_client: Any = None
_redis_lock = Lock()
_redis_disabled = False


_RFC1918 = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


def _peer_is_trusted_proxy(host: str) -> bool:
    name = (host or "").strip().lower()
    if not name:
        return False
    extra = {item.strip().lower() for item in get_settings().trusted_proxy_list}
    if name in extra or name in {"localhost"}:
        return True
    if name.startswith("::ffff:"):
        name = name[7:]
    try:
        ip = ipaddress.ip_address(name)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    if ip.version == 4:
        return any(ip in net for net in _RFC1918)
    return bool(ip in ipaddress.ip_network("fc00::/7") or ip.is_link_local)


def client_ip(request: Request) -> str:
    """Socket peer, unless that peer is a local/private reverse proxy."""
    peer = ""
    if request.client and request.client.host:
        peer = request.client.host.strip()
    if _peer_is_trusted_proxy(peer):
        cf = (request.headers.get("cf-connecting-ip") or "").strip()
        if cf:
            return cf
        real = (request.headers.get("x-real-ip") or "").strip()
        if real:
            return real
    return peer or "unknown"


def _redis() -> Any:
    """Optional shared counter store. Failures fall back to in-process memory."""
    global _redis_client, _redis_disabled
    if _redis_disabled:
        return None
    if _redis_client is not None:
        return _redis_client
    with _redis_lock:
        if _redis_disabled:
            return None
        if _redis_client is not None:
            return _redis_client
        url = (get_settings().redis_url or "").strip()
        if not url:
            _redis_disabled = True
            return None
        try:
            import redis

            client = redis.Redis.from_url(url, socket_connect_timeout=0.15, socket_timeout=0.15)
            client.ping()
        except Exception:
            _redis_disabled = True
            return None
        _redis_client = client
        return _redis_client


def _redis_check(key: str, limit: int, window_sec: float) -> RateDecision | None:
    client = _redis()
    if client is None:
        return None
    now = time.time()
    cutoff = now - window_sec
    try:
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        _removed, count = pipe.execute()
        if int(count) >= limit:
            oldest = client.zrange(key, 0, 0, withscores=True)
            retry_after = 1
            if oldest:
                retry_after = max(1, int(oldest[0][1] + window_sec - now) + 1)
            return RateDecision(
                allowed=False,
                limit=limit,
                remaining=0,
                retry_after=retry_after,
                reset_epoch=int(now + window_sec),
            )
        member = f"{now:.6f}:{secrets.token_hex(4)}"
        pipe = client.pipeline()
        pipe.zadd(key, {member: now})
        pipe.expire(key, int(window_sec) + 2)
        pipe.execute()
        remaining = max(0, limit - int(count) - 1)
        return RateDecision(
            allowed=True,
            limit=limit,
            remaining=remaining,
            retry_after=0,
            reset_epoch=int(now + window_sec),
        )
    except Exception:
        return None


def rate_limit_rule(method: str, path: str) -> tuple[str, int, float] | None:
    """Return (bucket_suffix, limit, window_sec) or None to skip."""
    if path == "/health":
        return None
    if method == "POST" and path.rstrip("/") == "/api/v1/orders":
        return ("orders", 8, 60.0)
    if method == "POST" and path.rstrip("/") == "/api/v1/auth/login":
        return ("auth-login", 5, 60.0)
    if method == "POST" and path.rstrip("/") == "/api/v1/auth/register":
        return ("auth-register", 3, 300.0)
    if method == "POST" and path.rstrip("/") in {
        "/api/v1/auth/telegram",
        "/api/v1/auth/telegram-login",
    }:
        return ("auth-telegram", 8, 60.0)
    if method == "POST" and path.rstrip("/") == "/api/v1/auth/refresh":
        return ("auth-refresh", 30, 60.0)
    if method == "POST" and path.startswith("/api/v1/auth/"):
        return ("auth", 12, 60.0)
    if method == "GET" and "/api/v1/orders/by-number/" in path:
        return ("order-lookup", 20, 60.0)
    if (
        method == "GET"
        and path.startswith("/api/v1/me/orders/")
        and path.rstrip("/") != "/api/v1/me/orders"
    ):
        return ("me-order", 30, 60.0)
    if method == "GET" and path.startswith("/api/v1/catalog/media/"):
        return ("catalog-media", 600, 60.0)
    if method == "POST" and path.startswith("/api/v1/admin/products/") and path.rstrip("/").endswith("/image"):
        return ("admin-upload", 20, 60.0)
    if method == "GET" and path.rstrip("/") == "/api/v1/me/export":
        return ("me-export", 6, 60.0)
    if method == "POST" and path.rstrip("/") == "/api/v1/me/delete":
        return ("me-delete", 3, 300.0)
    if path.startswith("/api/v1/admin"):
        return ("admin", 60, 60.0)
    return ("global", 240, 60.0)


def rate_limit_headers(decision: RateDecision) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(decision.limit),
        "X-RateLimit-Remaining": str(decision.remaining),
        "X-RateLimit-Reset": str(decision.reset_epoch),
    }
    if not decision.allowed:
        headers["Retry-After"] = str(decision.retry_after or 60)
    return headers


def check_rate_limit(request: Request) -> dict[str, str]:
    rule = rate_limit_rule(request.method, request.url.path)
    if rule is None:
        return {}
    suffix, limit, window = rule
    ip = client_ip(request)
    redis_key = f"rl:{ip}:{suffix}"
    decision = _redis_check(redis_key, limit, window)
    if decision is None:
        decision = limiter.check(f"{ip}:{suffix}", limit, window)
    headers = rate_limit_headers(decision)
    request.state.rate_limit_headers = headers
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов, повторите позже",
            headers=headers,
        )
    return headers


def new_order_access_token() -> str:
    return secrets.token_urlsafe(32)
