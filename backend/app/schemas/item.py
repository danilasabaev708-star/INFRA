from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    external_id: str | None = None
    url: str | None = None
    title: str
    text: str
    published_at: datetime | None = None
    content_hash: str
    lang: str
    is_job: bool
    impact: str | None = None
    trust_score: int | None = None
    trust_status: str | None = None
    created_at: datetime


class ItemTopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    topic_name: str
    locked: bool
    score: float | None = None
    assigned_by: str


class ItemAdminOut(ItemOut):
    sentinel_json: dict | None = None
    topics: list[ItemTopicOut] = []


class ItemTopicLockRequest(BaseModel):
    topic_ids: list[int] | None = None
