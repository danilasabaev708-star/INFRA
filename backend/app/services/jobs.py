from __future__ import annotations

from app.core.rate_limits import PlanTier
from app.models.user import User


class JobsAccessError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def ensure_jobs_access(user: User) -> None:
    if user.plan_tier != PlanTier.PRO:
        raise JobsAccessError("Jobs доступны только на PRO.")
    if not user.jobs_enabled:
        raise JobsAccessError("Включите Jobs в профиле.")
