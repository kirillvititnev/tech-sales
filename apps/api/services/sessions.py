from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import get_settings
from apps.api.models.account import AuthRefreshToken
from apps.api.models.user import User
from apps.api.schemas.account import TokenOut
from apps.api.services.tokens import TokenClaims, TokenPair, hash_jti, issue_token_pair


def _pair_out(pair: TokenPair) -> TokenOut:
    return TokenOut(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


async def persist_refresh(db: AsyncSession, user: User, pair: TokenPair) -> None:
    db.add(
        AuthRefreshToken(
            user_id=user.id,
            jti_hash=hash_jti(pair.refresh_jti),
            expires_at=pair.refresh_expires_at,
        )
    )


async def issue_session(db: AsyncSession, user: User) -> TokenOut:
    pair = issue_token_pair(user.id, get_settings().api_secret_key, token_version=user.token_version)
    await persist_refresh(db, user, pair)
    await db.commit()
    return _pair_out(pair)


async def load_refresh_row(db: AsyncSession, claims: TokenClaims) -> AuthRefreshToken | None:
    result = await db.execute(
        select(AuthRefreshToken).where(AuthRefreshToken.jti_hash == hash_jti(claims.jti))
    )
    return result.scalar_one_or_none()


async def revoke_all_sessions(db: AsyncSession, user: User) -> None:
    user.token_version = int(user.token_version or 0) + 1
    now = datetime.now(timezone.utc)
    await db.execute(
        update(AuthRefreshToken)
        .where(AuthRefreshToken.user_id == user.id, AuthRefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


async def rotate_refresh(db: AsyncSession, user: User, row: AuthRefreshToken) -> TokenOut:
    row.revoked_at = datetime.now(timezone.utc)
    pair = issue_token_pair(user.id, get_settings().api_secret_key, token_version=user.token_version)
    await persist_refresh(db, user, pair)
    await db.commit()
    return _pair_out(pair)
