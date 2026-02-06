from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.admin import parse_admin_ids


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "INFRA"
    app_env: str = "dev"
    database_url: str = Field(
        default="postgresql+asyncpg://infra:infra@db:5432/infra",
        alias="DATABASE_URL",
    )
    bot_token: str = Field(default="", alias="BOT_TOKEN")
    admin_ids: Any = Field(default="", alias="ADMIN_IDS")
    alerts_tg_group_id: int | None = Field(default=None, alias="ALERTS_TG_GROUP_ID")
    openserp_url: str | None = Field(default=None, alias="OPENSERP_URL")
    chroma_url: str | None = Field(default=None, alias="CHROMA_URL")
    global_rate_limit_per_minute: int = Field(default=30, alias="GLOBAL_RATE_LIMIT_PER_MIN")
    metrics_interval_seconds: int = Field(default=60, alias="METRICS_INTERVAL_SECONDS")
    metrics_retention_days: int = Field(default=183, alias="METRICS_RETENTION_DAYS")
    web_search_cache_minutes_min: int = Field(default=5, alias="WEB_SEARCH_CACHE_MIN")
    web_search_cache_minutes_max: int = Field(default=30, alias="WEB_SEARCH_CACHE_MAX")

    @property
    def admin_id_list(self) -> list[int]:
        return parse_admin_ids(self.admin_ids)


@lru_cache
def get_settings() -> Settings:
    return Settings()
