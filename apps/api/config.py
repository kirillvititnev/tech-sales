from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://whiteshop:whiteshop@localhost:5433/whiteshop"
    redis_url: str = "redis://localhost:6379/0"
    api_secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"
    admin_username: str | None = None
    admin_password: str | None = None
    api_docs_enabled: bool = False
    allowed_hosts: str = "localhost,127.0.0.1,testserver,whiteshop.tech,www.whiteshop.tech"
    # Extra hop-by-hop proxy names (comma-separated). Loopback and RFC1918 are always trusted.
    trusted_proxies: str = ""

    # Temporary: storefront shows supplier median (no markup) until pricing strategy returns.
    default_markup_percent: float = 0.0
    price_round_to: int = 100
    parse_interval_minutes: int = 15
    product_image_dir: str = "data/product-images"

    telegram_bot_token: str | None = None
    # One or more chat ids (user or group), comma-separated. Negative for groups.
    admin_telegram_chat_id: str | None = None

    @field_validator(
        "telegram_bot_token",
        "admin_telegram_chat_id",
        "admin_username",
        "admin_password",
        mode="before",
    )
    @classmethod
    def empty_as_none(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.split("#", 1)[0].strip()
            if not value:
                return None
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def trusted_proxy_list(self) -> list[str]:
        return [h.strip() for h in self.trusted_proxies.split(",") if h.strip()]

    @property
    def admin_telegram_chat_ids(self) -> list[str]:
        if not self.admin_telegram_chat_id:
            return []
        return [part.strip() for part in self.admin_telegram_chat_id.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
