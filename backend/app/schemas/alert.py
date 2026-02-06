from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dedup_key: str
    title: str
    message: str
    severity: str
    status: str
    acknowledged: bool
    muted_until: datetime | None
    last_sent_at: datetime | None
    created_at: datetime


class AlertMuteRequest(BaseModel):
    minutes: int = 15
