from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from pydantic import ValidationError

from apps.api.schemas.account import (
    AdminBonusAdjust,
    AdminUserPatch,
    ProfilePatch,
    RegisterIn,
    TelegramLoginIn,
)
from apps.api.schemas.order import OrderCreate
from apps.api.security import verify_telegram_login_widget
from apps.api.services.passwords import hash_password, password_error, verify_password
from apps.api.services.referrals import referral_credits
from apps.api.services.tokens import (
    ACCESS_TTL_SEC,
    issue_access_token,
    issue_token_pair,
    parse_access_claims,
    parse_access_token,
    parse_refresh_claims,
)

_SECRET = "unit-test-secret-key-must-be-32b!"


def test_password_roundtrip() -> None:
    hashed = hash_password("correct-horse")
    assert hashed != "correct-horse"
    assert verify_password("correct-horse", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("correct-horse", "")


def test_access_token_roundtrip() -> None:
    user_id = uuid4()
    token = issue_access_token(user_id, _SECRET)
    assert parse_access_token(token, _SECRET) == user_id
    assert parse_access_token(token, "other-secret-key-must-be-32b!!") is None
    assert parse_access_token(token[:-1] + ("0" if token[-1] != "0" else "1"), _SECRET) is None
    claims = parse_access_claims(token, _SECRET)
    assert claims is not None
    assert claims.typ == "access"
    assert claims.token_version == 0


def test_access_token_expired() -> None:
    user_id = uuid4()
    token = issue_access_token(user_id, _SECRET, ttl_sec=-5)
    assert parse_access_token(token, _SECRET) is None


def test_token_pair_refresh_is_not_access() -> None:
    user_id = uuid4()
    pair = issue_token_pair(user_id, _SECRET, token_version=3)
    assert pair.expires_in == ACCESS_TTL_SEC
    access = parse_access_claims(pair.access_token, _SECRET)
    refresh = parse_refresh_claims(pair.refresh_token, _SECRET)
    assert access is not None and access.token_version == 3
    assert refresh is not None and refresh.jti == pair.refresh_jti
    assert parse_access_claims(pair.refresh_token, _SECRET) is None
    assert parse_refresh_claims(pair.access_token, _SECRET) is None


def test_jwt_rejects_none_algorithm_and_wrong_audience() -> None:
    import base64
    import json
    from datetime import datetime, timedelta, timezone

    import jwt

    user_id = uuid4()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iss": "whiteshop",
        "aud": "whiteshop-api",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=15),
        "jti": "abc",
        "typ": "access",
        "ver": 0,
    }
    json_payload = {
        "sub": str(user_id),
        "iss": "whiteshop",
        "aud": "whiteshop-api",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "jti": "abc",
        "typ": "access",
        "ver": 0,
    }

    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).rstrip(b"=").decode()

    none_token = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64(json_payload)}."
    assert parse_access_token(none_token, _SECRET) is None

    wrong_aud = jwt.encode({**payload, "aud": "other-api"}, _SECRET, algorithm="HS256")
    assert parse_access_token(wrong_aud, _SECRET) is None

    missing_exp = dict(payload)
    missing_exp.pop("exp")
    no_exp = jwt.encode(missing_exp, _SECRET, algorithm="HS256")
    assert parse_access_token(no_exp, _SECRET) is None


def test_referral_credits_three_levels() -> None:
    total = Decimal("10000")
    percents = (Decimal("5"), Decimal("2"), Decimal("1"))
    ids = [uuid4(), uuid4(), uuid4()]
    credits = referral_credits(total, percents, ids)
    assert credits == [
        (ids[0], 1, Decimal("500.00")),
        (ids[1], 2, Decimal("200.00")),
        (ids[2], 3, Decimal("100.00")),
    ]


def test_referral_credits_skip_zero_and_short_chain() -> None:
    ids = [uuid4()]
    credits = referral_credits(Decimal("1000"), (Decimal("0"), Decimal("2"), Decimal("1")), ids)
    assert credits == []
    credits = referral_credits(Decimal("1000"), (Decimal("5"), Decimal("2"), Decimal("1")), ids)
    assert credits == [(ids[0], 1, Decimal("50.00"))]


def test_register_requires_privacy() -> None:
    RegisterIn.model_validate(
        {"email": "a@example.com", "password": "longenough", "privacy_consent": True}
    )
    try:
        RegisterIn.model_validate(
            {"email": "a@example.com", "password": "longenough", "privacy_consent": False}
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


def test_telegram_login_widget_hmac() -> None:
    import hashlib
    import hmac
    import time

    token = "123:test-token"
    fields = {"id": "42", "first_name": "Ann", "auth_date": str(int(time.time()))}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hashlib.sha256(token.encode()).digest()
    digest = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    parsed = verify_telegram_login_widget({**fields, "hash": digest}, token)
    assert parsed is not None
    assert parsed["id"] == "42"
    assert verify_telegram_login_widget({**fields, "hash": "dead"}, token) is None
    stale_fields = {"id": "42", "first_name": "Ann", "auth_date": "1"}
    stale_check = "\n".join(f"{k}={v}" for k, v in sorted(stale_fields.items()))
    stale_digest = hmac.new(secret, stale_check.encode(), hashlib.sha256).hexdigest()
    assert verify_telegram_login_widget({**stale_fields, "hash": stale_digest}, token, max_age_sec=60) is None


def test_telegram_login_coerces_numeric_id() -> None:
    payload = TelegramLoginIn.model_validate(
        {"id": 99, "auth_date": 1710000000, "hash": "abc", "first_name": "Ann"}
    )
    assert payload.id == "99"
    assert payload.auth_date == "1710000000"


def test_mass_assignment_rejected_on_write_models() -> None:
    try:
        RegisterIn.model_validate(
            {
                "email": "a@example.com",
                "password": "correct-horse",
                "privacy_consent": True,
                "role": "admin",
                "bonus_balance": 999,
            }
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
    try:
        ProfilePatch.model_validate({"name": "Ann", "is_active": True, "token_version": 9})
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
    try:
        OrderCreate.model_validate(
            {
                "customer_name": "Ann Smith",
                "customer_phone": "+79990000000",
                "delivery_type": "pickup_moscow",
                "privacy_consent": True,
                "items": [{"product_id": str(uuid4()), "quantity": 1}],
                "admin_status": "paid",
            }
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
    try:
        AdminBonusAdjust.model_validate({"delta": 100, "role": "admin", "bonus_balance": 999})
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
    try:
        AdminUserPatch.model_validate({"is_active": False, "password_hash": "x"})
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


def test_common_password_rejected() -> None:
    assert password_error("password123") is not None
    assert password_error("correct-horse", email="correct-horse@example.com") is not None
    RegisterIn.model_validate(
        {"email": "a@example.com", "password": "correct-horse", "privacy_consent": True}
    )
    try:
        RegisterIn.model_validate(
            {"email": "a@example.com", "password": "password123", "privacy_consent": True}
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
