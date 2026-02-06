from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    value: float
    labels: dict | None = None
    collected_at: datetime
