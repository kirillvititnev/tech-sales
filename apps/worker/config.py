from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettingsEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://whiteshop:whiteshop@localhost:5433/whiteshop"
    redis_url: str = "redis://localhost:6379/0"
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_session_path: str = "./data/telegram.session"
    telegram_proxy: str | None = None
    parse_interval_minutes: int = 15
    default_markup_percent: float = 10.0
    price_round_to: int = 100
    min_offer_price_rub: int = 6000

    @field_validator("telegram_api_id", "telegram_api_hash", "telegram_proxy", mode="before")
    @classmethod
    def empty_as_none(cls, value: Any) -> Any:
        if value == "":
            return None
        return value


@lru_cache
def get_worker_settings() -> WorkerSettingsEnv:
    return WorkerSettingsEnv()
