from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limits import AI_LIMITS, PlanTier
from app.models.ai_usage import AiUsage
from app.models.user import User


class RateLimitError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _msk_day_bounds(now: datetime) -> tuple[datetime, datetime]:
    msk = ZoneInfo("Europe/Moscow")
    now_msk = now.astimezone(msk)
    start_msk = datetime(now_msk.year, now_msk.month, now_msk.day, tzinfo=msk)
    end_msk = start_msk + timedelta(days=1)
    return start_msk.astimezone(timezone.utc), end_msk.astimezone(timezone.utc)


async def check_and_record_usage(
    session: AsyncSession,
    user: User,
    purpose: str,
) -> None:
    if purpose not in {"qa", "deepdive"}:
        return

    plan = user.plan_tier or PlanTier.FREE
    limits = AI_LIMITS.get(plan, AI_LIMITS[PlanTier.FREE])
    now = datetime.now(timezone.utc)

    if limits.throttle_seconds and user.last_ai_request_at:
        delta = (now - user.last_ai_request_at).total_seconds()
        if delta < limits.throttle_seconds:
            raise RateLimitError("Слишком часто. Попробуйте позже.")

    if limits.daily_limit is not None:
        start, end = _msk_day_bounds(now)
        count_query = select(func.count()).select_from(AiUsage).where(
            AiUsage.user_id == user.id,
            AiUsage.created_at >= start,
            AiUsage.created_at < end,
        )
        result = await session.execute(count_query)
        used = result.scalar_one()
        if used >= limits.daily_limit:
            raise RateLimitError("Дневной лимит исчерпан.")

    session.add(AiUsage(user_id=user.id, purpose=purpose, tokens=0))
    user.last_ai_request_at = now
    await session.flush()
