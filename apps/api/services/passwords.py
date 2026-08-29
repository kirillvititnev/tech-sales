from __future__ import annotations

import bcrypt
import secrets

BCRYPT_ROUNDS = 12
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_BYTES = 72

_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password123",
        "12345678",
        "123456789",
        "qwerty123",
        "qwertyui",
        "11111111",
        "whiteshop",
        "whiteshop1",
        "admin123",
        "letmein1",
        "iloveyou",
        "passw0rd",
    }
)

# Same cost as real hashes so a missing user does not fail faster than a wrong password.
_DUMMY_HASH = bcrypt.hashpw(secrets.token_urlsafe(16).encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def dummy_verify(plain: str) -> None:
    """Burn the same bcrypt work as a real check. Result is discarded."""
    try:
        bcrypt.checkpw(plain.encode("utf-8"), _DUMMY_HASH)
    except ValueError:
        return


def password_error(plain: str, *, email: str | None = None) -> str | None:
    if len(plain) < MIN_PASSWORD_LEN:
        return "Пароль должен быть не короче 8 символов"
    if len(plain.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "Пароль слишком длинный"
    lowered = plain.lower().strip()
    if lowered in _COMMON_PASSWORDS:
        return "Слишком простой пароль, выберите другой"
    if email:
        local = email.split("@", 1)[0].lower()
        if local and lowered == local:
            return "Пароль не должен совпадать с email"
    return None
