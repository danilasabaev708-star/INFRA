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
    created_at: datetime


class SubscriptionCreateRequest(BaseModel):
    user_id: int | None = None
    tg_id: int | None = None
    plan_tier: str
    status: str = "active"
    amount_rub: int = 0
    started_at: datetime | None = None
    expires_at: datetime | None = None


class SubscriptionSummaryTierOut(BaseModel):
    revenue_rub: int
    count: int


class SubscriptionSummaryOut(BaseModel):
    revenue_rub: int
    payments_count: int
    new_subscriptions_count: int
    active_subscriptions_count: int
    by_tier: dict[str, SubscriptionSummaryTierOut]


class ManualGrantRequest(BaseModel):
    user_id: int
    plan_tier: str
    expires_at: datetime | None = None
    amount_rub: int = 0


class ManualRevokeRequest(BaseModel):
    user_id: int
