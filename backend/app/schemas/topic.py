from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TopicCreate(BaseModel):
    name: str
    description: str | None = None


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime


class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
