from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://whiteshop:whiteshop@localhost:5433/whiteshop"
    redis_url: str = "redis://localhost:6379/0"
    api_secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    default_markup_percent: float = 10.0
    price_round_to: int = 100
    parse_interval_minutes: int = 15

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
