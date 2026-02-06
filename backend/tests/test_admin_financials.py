from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api.routes.admin import create_org, create_subscription, financials_summary
from app.core.rate_limits import PlanTier
from app.models.org import Org
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.financials import SubscriptionCreateRequest
from app.schemas.org import OrgCreate


@pytest.mark.asyncio
async def test_create_subscription_updates_user(session) -> None:
    user = User(tg_id=999, plan_tier=PlanTier.FREE)
    session.add(user)
    await session.commit()

    payload = SubscriptionCreateRequest(
        tg_id=999,
        plan_tier=PlanTier.PRO,
        status="active",
        amount_rub=1500,
    )
    subscription = await create_subscription(payload, session)

    result = await session.execute(select(User).where(User.id == user.id))
    refreshed = result.scalar_one()
    assert refreshed.plan_tier == PlanTier.PRO
    assert subscription.user_id == user.id


@pytest.mark.asyncio
async def test_financials_summary_counts(session) -> None:
    now = datetime.now(timezone.utc)
    user_one = User(tg_id=1, plan_tier=PlanTier.PRO)
    user_two = User(tg_id=2, plan_tier=PlanTier.PRO)
    session.add_all([user_one, user_two])
    await session.flush()
    subscription_active = Subscription(
        user_id=user_one.id,
        plan_tier=PlanTier.PRO,
        status="active",
        amount_rub=2000,
        started_at=now - timedelta(days=1),
        created_at=now - timedelta(days=1),
    )
    subscription_expired = Subscription(
        user_id=user_two.id,
        plan_tier=PlanTier.PRO,
        status="active",
        amount_rub=1000,
        started_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=2),
        created_at=now - timedelta(days=10),
    )
    session.add_all([subscription_active, subscription_expired])
    await session.commit()

    summary = await financials_summary(session=session, to=now)
    assert summary.revenue_rub == 3000
    assert summary.payments_count == 2
    assert summary.active_subscriptions_count == 1


@pytest.mark.asyncio
async def test_create_org_creates_user_from_tg_id(session) -> None:
    payload = OrgCreate(name="Test Org", admin_user_tg_id=123456)
    org = await create_org(payload, session)

    result = await session.execute(select(User).where(User.id == org.admin_user_id))
    user = result.scalar_one()
    assert user.tg_id == 123456

    result = await session.execute(select(Org).where(Org.id == org.id))
    assert result.scalar_one().name == "Test Org"
