"""Keep local .env hardened: unique secrets, chmod 600. Never print secret values."""

from __future__ import annotations

import os
import re
import secrets
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]

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

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_weak_secret(value: str | None, *, min_len: int = 12) -> bool:
    if value is None:
        return True
    text = value.strip()
    if text in WEAK_SECRETS:
        return True
    return len(text) < min_len


def _new_secret() -> str:
    return secrets.token_urlsafe(24)


def _has_key(text: str, key: str) -> bool:
    prefix = f"{key}="
    return any(line.startswith(prefix) for line in text.splitlines())


def get_key(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in text.splitlines():
        if line.startswith(prefix):
            raw = line[len(prefix) :].split("#", 1)[0].strip()
            if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                raw = raw[1:-1]
            return raw
    return None


def set_key(text: str, key: str, value: str) -> str:
    prefix = f"{key}="
    lines = text.splitlines()
    found = False
    out: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1] != "":
            out.append("")
        out.append(f"{key}={value}")
    return "\n".join(out) + "\n"


def password_from_url(url: str | None) -> str | None:
    if not url:
        return None
    normalized = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    if parsed.password is None:
        return None
    return unquote(parsed.password)


def rewrite_database_url(url: str | None, user: str, password: str, db: str) -> str:
    host, port = "localhost", 5433
    if url:
        parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
        host = parsed.hostname or host
        port = parsed.port or port
    user_q = quote(user, safe="")
    pass_q = quote(password, safe="")
    return f"postgresql+asyncpg://{user_q}:{pass_q}@{host}:{port}/{db}"


def rewrite_redis_url(url: str | None, password: str) -> str:
    host, port, db = "localhost", 6379, "0"
    if url:
        parsed = urlparse(url)
        host = parsed.hostname or host
        port = parsed.port or port
        db = (parsed.path or "/0").lstrip("/") or "0"
    pass_q = quote(password, safe="")
    return f"redis://:{pass_q}@{host}:{port}/{db}"


def _docker_compose(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _postgres_volume_exists() -> bool:
    try:
        result = subprocess.run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    return any(name.endswith("postgres_data") for name in result.stdout.splitlines())


def _ensure_postgres(user: str) -> bool:
    try:
        up = _docker_compose("up", "-d", "postgres", timeout=90)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if up.returncode != 0:
        return False
    for _ in range(30):
        ready = _docker_compose("exec", "-T", "postgres", "pg_isready", "-U", user, timeout=10)
        if ready.returncode == 0:
            return True
        time.sleep(1)
    return False


def _alter_postgres(user: str, old_password: str, new_password: str) -> bool:
    if not _IDENT.fullmatch(user):
        return False
    escaped = new_password.replace("'", "''")
    sql = f"ALTER USER {user} WITH PASSWORD '{escaped}';"
    try:
        result = _docker_compose(
            "exec",
            "-T",
            "-e",
            f"PGPASSWORD={old_password}",
            "postgres",
            "psql",
            "-U",
            user,
            "-d",
            user,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _recreate_redis() -> None:
    try:
        _docker_compose("up", "-d", "--force-recreate", "redis", timeout=90)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return


def harden_env(
    env_path: Path,
    example: Path,
    *,
    rotate_postgres: bool = True,
    recreate_redis: bool = True,
) -> list[str]:
    notes: list[str] = []
    if not env_path.exists():
        env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        notes.append("created .env from .env.example")

    text = env_path.read_text(encoding="utf-8")
    for key, default in (
        ("POSTGRES_USER", "whiteshop"),
        ("POSTGRES_DB", "whiteshop"),
        ("ADMIN_USERNAME", "admin"),
        ("API_DOCS_ENABLED", "false"),
        ("API_HOST", "127.0.0.1"),
        ("API_PORT", "8000"),
    ):
        if not _has_key(text, key):
            text = set_key(text, key, default)
            notes.append(f"set {key}")

    user = get_key(text, "POSTGRES_USER") or "whiteshop"
    db = get_key(text, "POSTGRES_DB") or "whiteshop"
    pg_now = get_key(text, "POSTGRES_PASSWORD") or password_from_url(get_key(text, "DATABASE_URL"))
    if is_weak_secret(pg_now):
        new_pg = _new_secret()
        wrote = False
        if rotate_postgres:
            volume = _postgres_volume_exists()
            if volume:
                if _ensure_postgres(user) and pg_now and _alter_postgres(user, pg_now, new_pg):
                    wrote = True
                    notes.append("POSTGRES_PASSWORD rotated in volume")
                else:
                    notes.append(
                        "Postgres volume still has the old password; start postgres (`make up`) and re-run `make env`"
                    )
            else:
                wrote = True
                notes.append("POSTGRES_PASSWORD generated for first-time init")
        else:
            wrote = True
            notes.append("POSTGRES_PASSWORD generated")
        if wrote:
            text = set_key(text, "POSTGRES_PASSWORD", new_pg)
            text = set_key(
                text,
                "DATABASE_URL",
                rewrite_database_url(get_key(text, "DATABASE_URL"), user, new_pg, db),
            )
    elif get_key(text, "DATABASE_URL") and pg_now:
        # Keep URL in sync if the password key was already strong.
        text = set_key(
            text,
            "DATABASE_URL",
            rewrite_database_url(get_key(text, "DATABASE_URL"), user, pg_now, db),
        )

    redis_now = get_key(text, "REDIS_PASSWORD") or password_from_url(get_key(text, "REDIS_URL"))
    if is_weak_secret(redis_now):
        new_redis = _new_secret()
        text = set_key(text, "REDIS_PASSWORD", new_redis)
        text = set_key(text, "REDIS_URL", rewrite_redis_url(get_key(text, "REDIS_URL"), new_redis))
        notes.append("REDIS_PASSWORD generated")
        if recreate_redis:
            _recreate_redis()
    elif redis_now:
        text = set_key(text, "REDIS_URL", rewrite_redis_url(get_key(text, "REDIS_URL"), redis_now))

    if is_weak_secret(get_key(text, "ADMIN_PASSWORD")):
        text = set_key(text, "ADMIN_PASSWORD", _new_secret())
        notes.append("ADMIN_PASSWORD generated — see .env")

    if is_weak_secret(get_key(text, "API_SECRET_KEY")):
        text = set_key(text, "API_SECRET_KEY", _new_secret())
        notes.append("API_SECRET_KEY generated")

    if not _has_key(text, "API_DOCS_ENABLED") or (get_key(text, "API_DOCS_ENABLED") or "").lower() in {
        "true",
        "1",
        "yes",
    }:
        text = set_key(text, "API_DOCS_ENABLED", "false")
        notes.append("API_DOCS_ENABLED=false")

    env_path.write_text(text, encoding="utf-8")
    os.chmod(env_path, 0o600)

    web_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(
            (
                "ADMIN_USERNAME=",
                "ADMIN_PASSWORD=",
                "API_INTERNAL_URL=",
                "NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=",
            )
        ):
            web_lines.append(line.split("#", 1)[0].rstrip())
    web_env = env_path.parent / "apps" / "web" / ".env.local"
    web_env.parent.mkdir(parents=True, exist_ok=True)
    web_env.write_text("\n".join(web_lines) + "\n", encoding="utf-8")
    os.chmod(web_env, 0o600)

    data = env_path.parent / "data"
    if data.is_dir():
        for session in data.glob("*.session"):
            os.chmod(session, 0o600)

    notes.append(".env ready (mode 600)")
    return notes


def main() -> None:
    notes = harden_env(ROOT / ".env", ROOT / ".env.example")
    for note in notes:
        print(note)


if __name__ == "__main__":
    main()
