from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.rate_limits import PlanTier
from app.db.session import get_session
from app.models.alert import Alert
from app.models.metric import Metric
from app.models.org import Org
from app.models.source import Source
from app.models.subscription import Subscription
from app.models.topic import Topic
from app.models.user import User
from app.schemas import (
    AlertMuteRequest,
    AlertOut,
    ManualGrantRequest,
    ManualRevokeRequest,
    MetricOut,
    OrgCreate,
    OrgInviteOut,
    OrgOut,
    SubscriptionOut,
    SourceCreate,
    SourceOut,
    SourceUpdate,
    TopicCreate,
    TopicOut,
    TopicUpdate,
)
from app.services.corp import create_invite

router = APIRouter()


@router.get("/overview")
async def overview(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    users_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    topics_count = (await session.execute(select(func.count()).select_from(Topic))).scalar_one()
    sources_count = (await session.execute(select(func.count()).select_from(Source))).scalar_one()
    alerts_open = (
        await session.execute(select(func.count()).select_from(Alert).where(Alert.status == "open"))
    ).scalar_one()
    return {
        "users": users_count,
        "topics": topics_count,
        "sources": sources_count,
        "alerts_open": alerts_open,
    }


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[SourceOut]:
    result = await session.execute(select(Source))
    return [SourceOut.model_validate(source) for source in result.scalars().all()]


@router.post("/sources", response_model=SourceOut)
async def create_source(
    payload: SourceCreate,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> SourceOut:
    source = Source(**payload.model_dump())
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return SourceOut.model_validate(source)


@router.put("/sources/{source_id}", response_model=SourceOut)
async def update_source(
    source_id: int,
    payload: SourceUpdate,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> SourceOut:
    result = await session.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Источник не найден.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    await session.commit()
    await session.refresh(source)
    return SourceOut.model_validate(source)


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Источник не найден.")
    await session.delete(source)
    await session.commit()
    return {"message": "Источник удалён."}


@router.get("/topics", response_model=list[TopicOut])
async def list_topics_admin(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[TopicOut]:
    result = await session.execute(select(Topic))
    return [TopicOut.model_validate(topic) for topic in result.scalars().all()]


@router.post("/topics", response_model=TopicOut)
async def create_topic(
    payload: TopicCreate,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> TopicOut:
    topic = Topic(**payload.model_dump())
    session.add(topic)
    await session.commit()
    await session.refresh(topic)
    return TopicOut.model_validate(topic)


@router.put("/topics/{topic_id}", response_model=TopicOut)
async def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> TopicOut:
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тема не найдена.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(topic, field, value)
    await session.commit()
    await session.refresh(topic)
    return TopicOut.model_validate(topic)


@router.delete("/topics/{topic_id}")
async def delete_topic(
    topic_id: int,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тема не найдена.")
    await session.delete(topic)
    await session.commit()
    return {"message": "Тема удалена."}


@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[AlertOut]:
    result = await session.execute(select(Alert).order_by(Alert.created_at.desc()))
    return [AlertOut.model_validate(alert) for alert in result.scalars().all()]


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut)
async def ack_alert(
    alert_id: int,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AlertOut:
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Алерт не найден.")
    alert.acknowledged = True
    await session.commit()
    await session.refresh(alert)
    return AlertOut.model_validate(alert)


@router.post("/alerts/{alert_id}/mute", response_model=AlertOut)
async def mute_alert(
    alert_id: int,
    payload: AlertMuteRequest,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AlertOut:
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Алерт не найден.")
    alert.muted_until = datetime.now(timezone.utc) + timedelta(minutes=payload.minutes)
    await session.commit()
    await session.refresh(alert)
    return AlertOut.model_validate(alert)


@router.get("/metrics", response_model=list[MetricOut])
async def list_metrics(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[MetricOut]:
    result = await session.execute(select(Metric).order_by(Metric.collected_at.desc()).limit(200))
    return [MetricOut.model_validate(metric) for metric in result.scalars().all()]


@router.get("/financials", response_model=list[SubscriptionOut])
async def list_financials(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[SubscriptionOut]:
    result = await session.execute(select(Subscription).order_by(Subscription.created_at.desc()))
    return [SubscriptionOut.model_validate(sub) for sub in result.scalars().all()]


@router.post("/financials/grant")
async def manual_grant(
    payload: ManualGrantRequest,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(User).where(User.id == payload.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    user.plan_tier = payload.plan_tier
    user.plan_expires_at = payload.expires_at
    sub = Subscription(
        user_id=user.id,
        plan_tier=payload.plan_tier,
        amount_rub=payload.amount_rub,
        expires_at=payload.expires_at,
    )
    session.add(sub)
    await session.commit()
    return {"message": "Подписка обновлена."}


@router.post("/financials/revoke")
async def manual_revoke(
    payload: ManualRevokeRequest,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(User).where(User.id == payload.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    user.plan_tier = PlanTier.FREE
    user.plan_expires_at = None
    await session.commit()
    return {"message": "Подписка отозвана."}


@router.post("/corp/orgs", response_model=OrgOut)
async def create_org(
    payload: OrgCreate,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> OrgOut:
    org = Org(name=payload.name, admin_user_id=payload.admin_user_id)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return OrgOut.model_validate(org)


@router.post("/corp/orgs/{org_id}/invites", response_model=OrgInviteOut)
async def create_org_invite(
    org_id: int,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> OrgInviteOut:
    invite = await create_invite(session, org_id)
    await session.commit()
    return OrgInviteOut.model_validate(invite)
