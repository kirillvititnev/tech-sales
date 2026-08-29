from __future__ import annotations

import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.user import User

_ALPHABET = string.ascii_uppercase + string.digits


def new_referral_code() -> str:
    return "WS" + "".join(secrets.choice(_ALPHABET) for _ in range(8))


async def unique_referral_code(db: AsyncSession) -> str:
    for _ in range(12):
        code = new_referral_code()
        exists = await db.execute(select(User.id).where(User.referral_code == code))
        if exists.scalar_one_or_none() is None:
            return code
    return new_referral_code() + secrets.token_hex(2).upper()
