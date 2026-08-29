from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import get_settings
from apps.api.db import get_db
from apps.api.deps import peek_user
from apps.api.models.user import User
from apps.api.schemas.account import (
    PRIVACY_POLICY_VERSION,
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    TelegramInitIn,
    TelegramLoginIn,
    TokenOut,
)
from apps.api.security import verify_telegram_init_data, verify_telegram_login_widget
from apps.api.services.accounts import unique_referral_code
from apps.api.services.passwords import dummy_verify, hash_password, password_error, verify_password
from apps.api.services.sessions import (
    issue_session,
    load_refresh_row,
    revoke_all_sessions,
    rotate_refresh,
)
from apps.api.services.tokens import parse_refresh_claims

router = APIRouter(prefix="/auth", tags=["auth"])

_TG_MAX_AGE = 60 * 60 * 36
_AUTH_FAIL = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")


async def _referrer_id(db: AsyncSession, code: str | None) -> UUID | None:
    if not code or not code.strip():
        return None
    needle = code.strip().upper()
    result = await db.execute(select(User.id).where(User.referral_code == needle, User.is_active.is_(True)))
    found = result.scalar_one_or_none()
    if found is None:
        raise HTTPException(status_code=400, detail="Реферальный код не найден")
    return found


def _stamp_consent(user: User) -> None:
    user.privacy_consented_at = datetime.now(timezone.utc)
    user.privacy_policy_version = PRIVACY_POLICY_VERSION


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    email = str(payload.email).strip().lower()
    taken = await db.execute(select(User.id).where(User.email == email))
    if taken.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Этот email уже зарегистрирован")
    problem = password_error(payload.password, email=email)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    referrer = await _referrer_id(db, payload.referral_code)
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        name=(payload.name or "").strip() or None,
        phone=(payload.phone or "").strip() or None,
        referral_code=await unique_referral_code(db),
        referred_by_id=referrer,
    )
    _stamp_consent(user)
    db.add(user)
    await db.flush()
    return await issue_session(db, user)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    email = str(payload.email).strip().lower()
    result = await db.execute(select(User).where(User.email == email, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None or not user.password_hash:
        dummy_verify(payload.password)
        raise _AUTH_FAIL
    if not verify_password(payload.password, user.password_hash):
        raise _AUTH_FAIL
    return await issue_session(db, user)


async def _upsert_telegram_user(
    db: AsyncSession,
    *,
    telegram_id: str,
    name: str | None,
    referral_code: str | None,
    privacy_consent: bool,
) -> User:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Недействительные данные Telegram")
        if name and not user.name:
            user.name = name
        return user
    if privacy_consent is not True:
        raise HTTPException(status_code=400, detail="Нужно согласие на обработку персональных данных")
    referrer = await _referrer_id(db, referral_code)
    user = User(
        telegram_id=telegram_id,
        name=name,
        referral_code=await unique_referral_code(db),
        referred_by_id=referrer,
    )
    _stamp_consent(user)
    db.add(user)
    await db.flush()
    return user


@router.post("/telegram", response_model=TokenOut)
async def auth_telegram(payload: TelegramInitIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram-вход не настроен")
    parsed = verify_telegram_init_data(
        payload.init_data,
        settings.telegram_bot_token,
        max_age_sec=_TG_MAX_AGE,
    )
    if parsed is None:
        raise HTTPException(status_code=401, detail="Недействительные данные Telegram")
    try:
        tg_user = json.loads(parsed.get("user") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=401, detail="Недействительные данные Telegram") from exc
    telegram_id = str(tg_user.get("id") or "")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Недействительные данные Telegram")
    first = str(tg_user.get("first_name") or "").strip()
    last = str(tg_user.get("last_name") or "").strip()
    name = " ".join(part for part in (first, last) if part) or None
    user = await _upsert_telegram_user(
        db,
        telegram_id=telegram_id,
        name=name,
        referral_code=payload.referral_code,
        privacy_consent=payload.privacy_consent,
    )
    return await issue_session(db, user)


@router.post("/telegram-login", response_model=TokenOut)
async def auth_telegram_login(payload: TelegramLoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram-вход не настроен")
    fields = {
        k: str(v)
        for k, v in payload.model_dump(exclude={"referral_code", "privacy_consent"}).items()
        if k == "hash" or (v is not None and str(v) != "")
    }
    parsed = verify_telegram_login_widget(fields, settings.telegram_bot_token, max_age_sec=_TG_MAX_AGE)
    if parsed is None:
        raise HTTPException(status_code=401, detail="Недействительные данные Telegram")
    first = (payload.first_name or "").strip()
    last = (payload.last_name or "").strip()
    name = " ".join(part for part in (first, last) if part) or None
    user = await _upsert_telegram_user(
        db,
        telegram_id=str(payload.id),
        name=name,
        referral_code=payload.referral_code,
        privacy_consent=payload.privacy_consent,
    )
    return await issue_session(db, user)


@router.post("/refresh", response_model=TokenOut)
async def refresh_session(payload: RefreshIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    secret = get_settings().api_secret_key
    claims = parse_refresh_claims(payload.refresh_token, secret)
    if claims is None:
        raise HTTPException(status_code=401, detail="Нужен вход")
    row = await load_refresh_row(db, claims)
    user_result = await db.execute(select(User).where(User.id == claims.user_id))
    user = user_result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    reused = row is not None and row.revoked_at is not None
    if reused and user is not None:
        await revoke_all_sessions(db, user)
        await db.commit()
        raise HTTPException(status_code=401, detail="Нужен вход")
    if (
        row is None
        or row.revoked_at is not None
        or row.expires_at <= now
        or user is None
        or not user.is_active
        or user.token_version != claims.token_version
    ):
        raise HTTPException(status_code=401, detail="Нужен вход")
    return await rotate_refresh(db, user, row)


@router.post("/logout", status_code=204)
async def logout(
    payload: LogoutIn | None = None,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(peek_user),
) -> Response:
    body = payload or LogoutIn()
    secret = get_settings().api_secret_key
    target = user
    if body.refresh_token:
        claims = parse_refresh_claims(body.refresh_token, secret)
        if claims is not None:
            row = await load_refresh_row(db, claims)
            if row and row.revoked_at is None:
                row.revoked_at = datetime.now(timezone.utc)
            if target is None:
                found = await db.execute(select(User).where(User.id == claims.user_id))
                target = found.scalar_one_or_none()
    if target is not None:
        await revoke_all_sessions(db, target)
        await db.commit()
    return Response(status_code=204)
