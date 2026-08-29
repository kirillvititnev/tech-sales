from __future__ import annotations

from urllib.parse import urlencode

from apps.api.security import (
    admin_credentials_valid,
    escape_like,
    is_weak_secret,
    public_product_attributes,
    rate_limit_rule,
    runtime_secret_problems,
    verify_telegram_init_data,
)


def test_escape_like_wildcards() -> None:
    assert escape_like("100%_off") == "100\\%\\_off"
    assert escape_like("a\\b") == "a\\\\b"


def test_public_attributes_drop_internal_keys() -> None:
    raw = {
        "device_name": "iPhone 16",
        "folder": "Apple",
        "norm_key": "secret-match",
        "region_samples": ["RU"],
        "storage": "256GB",
        "cost": "not-a-public-field",
    }
    out = public_product_attributes(raw)
    assert out["device_name"] == "iPhone 16"
    assert out["storage"] == "256GB"
    assert "folder" not in out
    assert "norm_key" not in out
    assert "region_samples" not in out


def test_admin_rejects_wrong_password(monkeypatch) -> None:
    from apps.api.config import get_settings

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse")
    get_settings.cache_clear()
    try:
        assert admin_credentials_valid("admin", "correct-horse")
        assert not admin_credentials_valid("admin", "wrong")
        assert not admin_credentials_valid("other", "correct-horse")
    finally:
        get_settings.cache_clear()


def test_telegram_init_data_hmac() -> None:
    import hashlib
    import hmac as hmaclib

    token = "123:test-token"
    fields = {"auth_date": "1", "query_id": "AA", "user": '{"id":1,"username":"alice"}'}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmaclib.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    digest = hmaclib.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    init_data = urlencode({**fields, "hash": digest})
    parsed = verify_telegram_init_data(init_data, token)
    assert parsed is not None
    assert parsed["query_id"] == "AA"
    assert verify_telegram_init_data(init_data, "wrong") is None
    assert verify_telegram_init_data("hash=dead", token) is None
    assert verify_telegram_init_data(init_data, token, max_age_sec=1) is None


def test_rate_limit_rules() -> None:
    assert rate_limit_rule("GET", "/health") is None
    assert rate_limit_rule("POST", "/api/v1/orders")[0] == "orders"
    assert rate_limit_rule("POST", "/api/v1/auth/login")[0] == "auth-login"
    assert rate_limit_rule("POST", "/api/v1/auth/register")[0] == "auth-register"
    assert rate_limit_rule("POST", "/api/v1/auth/login")[1] == 5
    assert rate_limit_rule("POST", "/api/v1/auth/refresh")[0] == "auth-refresh"
    assert rate_limit_rule("GET", "/api/v1/orders/by-number/WS-1")[0] == "order-lookup"
    assert rate_limit_rule("GET", "/api/v1/me/orders/WS-1")[0] == "me-order"
    assert rate_limit_rule("GET", "/api/v1/me/orders")[0] == "global"
    assert rate_limit_rule("GET", "/api/v1/admin/orders")[0] == "admin"


def test_weak_secret_denylist() -> None:
    assert is_weak_secret("whiteshop")
    assert is_weak_secret("change-me-admin")
    assert is_weak_secret("changeme-redis")
    assert is_weak_secret("change-me-in-production")
    assert is_weak_secret("short")
    assert not is_weak_secret("correct-horse-battery")


def test_runtime_secret_problems_flag_defaults(monkeypatch) -> None:
    from apps.api.config import get_settings

    monkeypatch.setenv("ADMIN_PASSWORD", "whiteshop")
    monkeypatch.setenv("API_SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://whiteshop:whiteshop@localhost:5433/whiteshop")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()
    try:
        problems = runtime_secret_problems()
        assert any("ADMIN_PASSWORD" in p for p in problems)
        assert any("DATABASE_URL" in p for p in problems)
        assert any("REDIS_URL" in p for p in problems)
        assert any("API_SECRET_KEY" in p for p in problems)
    finally:
        get_settings.cache_clear()
