from __future__ import annotations

from dataclasses import dataclass


class PlanTier:
    FREE = "free"
    PRO = "pro"
    CORP = "corp"


class DeliveryMode:
    DIGEST = "digest"
    INSTANT = "instant"


@dataclass(frozen=True)
class AiPlanLimit:
    daily_limit: int | None
    throttle_seconds: int


AI_LIMITS = {
    PlanTier.FREE: AiPlanLimit(daily_limit=5, throttle_seconds=0),
    PlanTier.PRO: AiPlanLimit(daily_limit=200, throttle_seconds=5),
    PlanTier.CORP: AiPlanLimit(daily_limit=None, throttle_seconds=2),
}
