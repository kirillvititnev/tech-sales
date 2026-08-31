from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import get_settings
from apps.api.db import get_db
from apps.api.models.user import User
from apps.api.services.tokens import parse_access_claims

_WWW = {"WWW-Authenticate": 'Bearer realm="White Shop"'}


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
        return token or None
    return None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Нужен вход",
        headers=_WWW,
    )


async def _load_user(db: AsyncSession, token: str) -> User | None:
    claims = parse_access_claims(token, get_settings().api_secret_key)
    if claims is None:
        return None
    result = await db.execute(select(User).where(User.id == claims.user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None or int(user.token_version or 0) != claims.token_version:
        return None
    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = _bearer_token(request)
    if not token:
        return None
    user = await _load_user(db, token)
    if user is None:
        raise _unauthorized()
    return user


async def peek_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = _bearer_token(request)
    if not token:
        return None
    return await _load_user(db, token)


async def require_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise _unauthorized()
    return user
