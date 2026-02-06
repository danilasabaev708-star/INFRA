from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    plan_tier: str
    status: str
    amount_rub: int
    started_at: datetime
    expires_at: datetime | None


class ManualGrantRequest(BaseModel):
    user_id: int
    plan_tier: str
    expires_at: datetime | None = None
    amount_rub: int = 0


class ManualRevokeRequest(BaseModel):
    user_id: int
