from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceCreate(BaseModel):
    name: str
    source_type: str = "content"
    url: str | None = None
    trust_manual: int = 50
    job_keywords: list[str] | None = None
    job_regex: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    url: str | None = None
    trust_manual: int | None = None
    job_keywords: list[str] | None = None
    job_regex: str | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    url: str | None
    trust_manual: int
    job_keywords: list[str] | None = None
    job_regex: str | None = None
    created_at: datetime
