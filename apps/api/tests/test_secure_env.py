from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load_secure_env():
    path = ROOT / "scripts" / "secure_env.py"
    spec = importlib.util.spec_from_file_location("secure_env", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_harden_env_replaces_placeholder_secrets(tmp_path: Path) -> None:
    se = _load_secure_env()
    example = tmp_path / ".env.example"
    example.write_text(
        "POSTGRES_USER=whiteshop\n"
        "POSTGRES_PASSWORD=whiteshop\n"
        "POSTGRES_DB=whiteshop\n"
        "DATABASE_URL=postgresql+asyncpg://whiteshop:whiteshop@localhost:5433/whiteshop\n"
        "REDIS_PASSWORD=changeme-redis\n"
        "REDIS_URL=redis://:changeme-redis@localhost:6379/0\n"
        "ADMIN_USERNAME=admin\n"
        "ADMIN_PASSWORD=change-me-admin\n"
        "API_SECRET_KEY=change-me-in-production\n",
        encoding="utf-8",
    )
    env_path = tmp_path / ".env"
    notes = se.harden_env(env_path, example, rotate_postgres=False, recreate_redis=False)
    text = env_path.read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD=whiteshop" not in text
    assert "ADMIN_PASSWORD=change-me-admin" not in text
    assert "REDIS_PASSWORD=changeme-redis" not in text
    assert "API_SECRET_KEY=change-me-in-production" not in text
    pg = se.get_key(text, "POSTGRES_PASSWORD")
    admin = se.get_key(text, "ADMIN_PASSWORD")
    redis = se.get_key(text, "REDIS_PASSWORD")
    secret = se.get_key(text, "API_SECRET_KEY")
    assert pg and not se.is_weak_secret(pg)
    assert admin and not se.is_weak_secret(admin)
    assert redis and not se.is_weak_secret(redis)
    assert secret and not se.is_weak_secret(secret)
    assert se.password_from_url(se.get_key(text, "DATABASE_URL")) == pg
    assert se.password_from_url(se.get_key(text, "REDIS_URL")) == redis
    assert env_path.stat().st_mode & 0o777 == 0o600
    assert any("generated" in n or "ready" in n for n in notes)
