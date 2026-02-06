from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InitDataRequest(BaseModel):
    init_data: str = Field(..., description="initData от Telegram WebApp")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tg_id: int
    username: str | None = None
    plan_tier: str
    plan_expires_at: datetime | None = None
    jobs_enabled: bool
    delivery_mode: str
    batch_interval_hours: int
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
    only_important: bool


class AuthResponse(BaseModel):
    user: UserOut
    message: str


class UserSettingsUpdate(BaseModel):
    delivery_mode: str | None = None
    batch_interval_hours: int | None = None
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
    only_important: bool | None = None
    jobs_enabled: bool | None = None


class UserTopicsUpdate(BaseModel):
    topic_ids: list[int]


class AiRequest(BaseModel):
    purpose: str
    prompt: str


class AiResponse(BaseModel):
    message: str
    data: dict[str, Any] | None = None
