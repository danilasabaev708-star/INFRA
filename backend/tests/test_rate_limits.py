from __future__ import annotations

import pytest

from app.core.rate_limits import PlanTier
from app.models.user import User
from app.services.ai_usage import RateLimitError, check_and_record_usage


@pytest.mark.asyncio
async def test_rate_limit_counter(session):
    user = User(tg_id=111, plan_tier=PlanTier.FREE)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    for _ in range(5):
        await check_and_record_usage(session, user, "qa")
    await session.commit()

    with pytest.raises(RateLimitError):
        await check_and_record_usage(session, user, "qa")
