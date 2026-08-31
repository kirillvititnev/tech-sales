from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

import jwt

TOKEN_ALGORITHMS = ("HS256",)
ISSUER = "whiteshop"
AUDIENCE = "whiteshop-api"
ACCESS_TTL_SEC = 15 * 60
REFRESH_TTL_SEC = 60 * 60 * 24 * 14
_REQUIRED_CLAIMS = ["exp", "iat", "nbf", "iss", "aud", "sub"]


def hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    token_version: int
    jti: str
    typ: Literal["access", "refresh"]
    exp: datetime


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    refresh_jti: str
    refresh_expires_at: datetime
    expires_in: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _encode(
    *,
    user_id: UUID,
    secret: str,
    typ: Literal["access", "refresh"],
    token_version: int,
    ttl_sec: int,
) -> tuple[str, str, datetime]:
    now = _now()
    exp = now + timedelta(seconds=ttl_sec)
    jti = secrets.token_urlsafe(16)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": exp,
        "jti": jti,
        "typ": typ,
        "ver": int(token_version),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, jti, exp


def issue_access_token(
    user_id: UUID,
    secret: str,
    *,
    ttl_sec: int = ACCESS_TTL_SEC,
    token_version: int = 0,
) -> str:
    token, _, _ = _encode(
        user_id=user_id,
        secret=secret,
        typ="access",
        token_version=token_version,
        ttl_sec=ttl_sec,
    )
    return token


def issue_token_pair(user_id: UUID, secret: str, *, token_version: int = 0) -> TokenPair:
    access, _, _ = _encode(
        user_id=user_id,
        secret=secret,
        typ="access",
        token_version=token_version,
        ttl_sec=ACCESS_TTL_SEC,
    )
    refresh, refresh_jti, refresh_exp = _encode(
        user_id=user_id,
        secret=secret,
        typ="refresh",
        token_version=token_version,
        ttl_sec=REFRESH_TTL_SEC,
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        refresh_jti=refresh_jti,
        refresh_expires_at=refresh_exp,
        expires_in=ACCESS_TTL_SEC,
    )


def _decode(token: str, secret: str, *, expected_typ: Literal["access", "refresh"]) -> TokenClaims | None:
    if not token or token.count(".") != 2:
        return None
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=list(TOKEN_ALGORITHMS),
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": _REQUIRED_CLAIMS, "verify_signature": True},
        )
    except jwt.InvalidTokenError:
        return None
    if payload.get("typ") != expected_typ:
        return None
    try:
        user_id = UUID(str(payload["sub"]))
        version = int(payload.get("ver", 0))
        jti = str(payload["jti"])
        exp_raw = payload["exp"]
        if isinstance(exp_raw, datetime):
            exp = exp_raw if exp_raw.tzinfo else exp_raw.replace(tzinfo=timezone.utc)
        else:
            exp = datetime.fromtimestamp(int(exp_raw), tz=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return None
    if not jti:
        return None
    return TokenClaims(user_id=user_id, token_version=version, jti=jti, typ=expected_typ, exp=exp)


def parse_access_token(token: str, secret: str) -> UUID | None:
    claims = parse_access_claims(token, secret)
    return None if claims is None else claims.user_id


def parse_access_claims(token: str, secret: str) -> TokenClaims | None:
    return _decode(token, secret, expected_typ="access")


def parse_refresh_claims(token: str, secret: str) -> TokenClaims | None:
    return _decode(token, secret, expected_typ="refresh")
