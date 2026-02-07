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
    admin_panel_username: str = Field(default="admin", alias="ADMIN_PANEL_USERNAME")
    admin_panel_password_hash: str | None = Field(default=None, alias="ADMIN_PANEL_PASSWORD_HASH")
    admin_panel_password: str | None = Field(default=None, alias="ADMIN_PANEL_PASSWORD")
    admin_jwt_secret: str = Field(default="", alias="ADMIN_JWT_SECRET")
    admin_jwt_ttl_min: int = Field(default=120, alias="ADMIN_JWT_TTL_MIN")
    init_data_max_age_seconds: int = Field(default=300, alias="INIT_DATA_MAX_AGE_SECONDS")
    web_admin_origin: str = Field(default="http://localhost:8080", alias="WEB_ADMIN_ORIGIN")
    tma_origin: str | None = Field(default=None, alias="TMA_ORIGIN")
    tma_origins: str | None = Field(default=None, alias="TMA_ORIGINS")
    alerts_tg_group_id: int | None = Field(default=None, alias="ALERTS_TG_GROUP_ID")
    openserp_url: str | None = Field(default=None, alias="OPENSERP_URL")
    openserp_timeout_seconds: int = Field(default=15, alias="OPENSERP_TIMEOUT_SECONDS")
    litellm_url: str | None = Field(default=None, alias="LITELLM_URL")
    litellm_model: str | None = Field(default=None, alias="LITELLM_MODEL")
    litellm_api_key: str | None = Field(default=None, alias="LITELLM_API_KEY")
    litellm_timeout_seconds: int = Field(default=20, alias="LITELLM_TIMEOUT_SECONDS")
    chroma_url: str | None = Field(default=None, alias="CHROMA_URL")
    global_rate_limit_per_minute: int = Field(default=30, alias="GLOBAL_RATE_LIMIT_PER_MIN")
    public_rate_limit_per_minute: int = Field(default=60, alias="PUBLIC_RATE_LIMIT_PER_MIN")
    public_rate_limit_window_seconds: int = Field(default=60, alias="PUBLIC_RATE_LIMIT_WINDOW_SECONDS")
    metrics_interval_seconds: int = Field(default=60, alias="METRICS_INTERVAL_SECONDS")
    metrics_retention_days: int = Field(default=183, alias="METRICS_RETENTION_DAYS")
    web_search_cache_minutes_min: int = Field(default=5, alias="WEB_SEARCH_CACHE_MIN")
    web_search_cache_minutes_max: int = Field(default=30, alias="WEB_SEARCH_CACHE_MAX")
    web_search_cache_max_entries: int = Field(default=500, alias="WEB_SEARCH_CACHE_MAX_ENTRIES")
    ingestion_interval_seconds: int = Field(default=60, alias="INGESTION_INTERVAL_SECONDS")
    ingestion_request_timeout_seconds: int = Field(
        default=15, alias="INGESTION_REQUEST_TIMEOUT_SECONDS"
    )
    ingestion_request_retries: int = Field(default=2, alias="INGESTION_REQUEST_RETRIES")
    telethon_api_id: int | None = Field(default=None, alias="TELETHON_API_ID")
    telethon_api_hash: str = Field(default="", alias="TELETHON_API_HASH")
    telethon_session: str = Field(default="", alias="TELETHON_SESSION")
    reddit_client_id: str = Field(default="", alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str = Field(default="", alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(default="INFRA/1.0", alias="REDDIT_USER_AGENT")

    @property
    def cors_origins(self) -> list[str]:
        origins: list[str] = []
        if self.web_admin_origin:
            origins.append(self.web_admin_origin)
        raw_tma = self.tma_origins or self.tma_origin
        if raw_tma:
            origins.extend([origin.strip() for origin in raw_tma.split(",") if origin.strip()])
        seen: set[str] = set()
        unique_origins: list[str] = []
        for origin in origins:
            if origin not in seen:
                unique_origins.append(origin)
                seen.add(origin)
        return unique_origins

    @property
    def admin_id_list(self) -> list[int]:
        return parse_admin_ids(self.admin_ids)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _is_prod(settings: Settings) -> bool:
    return settings.app_env.lower() in {"prod", "production"}


def _is_bcrypt_hash(value: str) -> bool:
    return any(value.startswith(prefix) for prefix in ("$2a$", "$2b$", "$2y$"))


def validate_settings(settings: Settings) -> None:
    if not _is_prod(settings):
        return
    if settings.admin_panel_password:
        raise ValueError("ADMIN_PANEL_PASSWORD нельзя использовать в production.")
    if not settings.admin_panel_password_hash:
        raise ValueError("ADMIN_PANEL_PASSWORD_HASH обязателен в production.")
    if not _is_bcrypt_hash(settings.admin_panel_password_hash):
        raise ValueError("ADMIN_PANEL_PASSWORD_HASH должен быть bcrypt-хешем.")
    if len(settings.admin_jwt_secret) < 32:
        raise ValueError("ADMIN_JWT_SECRET слишком короткий для production.")
    if any("*" in origin for origin in settings.cors_origins):
        raise ValueError("CORS origins с '*' запрещены при allow_credentials в production.")
