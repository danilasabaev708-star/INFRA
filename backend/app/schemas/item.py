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
