from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.core.rate_limits import PlanTier
from app.db.session import get_session
from app.models.alert import Alert
from app.models.item import Item, ItemTopic
from app.models.metric import Metric
from app.models.org import Org, OrgMember
from app.models.source import Source
from app.models.subscription import Subscription
from app.models.topic import Topic
from app.models.user import User
from app.schemas import (
    AlertMuteRequest,
    AlertOut,
    ItemAdminOut,
    ItemOut,
    ItemTopicLockRequest,
    ItemTopicOut,
    ManualGrantRequest,
    ManualRevokeRequest,
    MetricOut,
    OrgCreate,
    OrgEditorChatRequest,
    OrgInviteCreate,
    OrgInviteOut,
    OrgMemberOut,
    OrgOut,
    SubscriptionCreateRequest,
    SubscriptionOut,
    SubscriptionSummaryOut,
    SubscriptionSummaryTierOut,
    SourceCreate,
    SourceOut,
    SourceUpdate,
    TopicCreate,
    TopicOut,
    TopicUpdate,
)
from app.services.corp import create_invite
from app.services.alerts import resolve_alert as emit_resolved_alert

router = APIRouter(dependencies=[Depends(require_admin_session)])


async def _get_item_topics(session: AsyncSession, item_id: int) -> list[ItemTopicOut]:
    rows = await session.execute(
        select(ItemTopic, Topic).join(Topic, ItemTopic.topic_id == Topic.id).where(
            ItemTopic.item_id == item_id
        )
    )
    topics: list[ItemTopicOut] = []
    for item_topic, topic in rows.all():
        topics.append(
            ItemTopicOut(
                topic_id=item_topic.topic_id,
                topic_name=topic.name,
                locked=item_topic.locked,
                score=item_topic.score,
                assigned_by=item_topic.assigned_by,
            )
        )
    return topics


@router.get("/overview")
async def overview(
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
    session: AsyncSession = Depends(get_session),
) -> list[SourceOut]:
    result = await session.execute(select(Source))
    return [SourceOut.model_validate(source) for source in result.scalars().all()]


@router.post("/sources", response_model=SourceOut)
async def create_source(
    payload: SourceCreate,
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


@router.get("/sources/{source_id}/state")
async def get_source_state(
    source_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Источник не найден.")
    return {"id": source.id, "state": source.state or {}}


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
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
    session: AsyncSession = Depends(get_session),
) -> list[TopicOut]:
    result = await session.execute(select(Topic))
    return [TopicOut.model_validate(topic) for topic in result.scalars().all()]


@router.post("/topics", response_model=TopicOut)
async def create_topic(
    payload: TopicCreate,
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
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тема не найдена.")
    await session.delete(topic)
    await session.commit()
    return {"message": "Тема удалена."}


@router.get("/items", response_model=list[ItemOut])
async def list_items_admin(
    session: AsyncSession = Depends(get_session),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None, alias="to"),
    source_id: int | None = None,
    limit: int = Query(default=200, ge=1, le=500),
) -> list[ItemOut]:
    stmt = select(Item)
    if source_id is not None:
        stmt = stmt.where(Item.source_id == source_id)
    if from_:
        stmt = stmt.where(Item.published_at >= from_)
    if to:
        stmt = stmt.where(Item.published_at <= to)
    result = await session.execute(
        stmt.order_by(Item.published_at.desc().nullslast(), Item.id.desc()).limit(limit)
    )
    return [ItemOut.model_validate(item) for item in result.scalars().all()]


@router.get("/items/{item_id}", response_model=ItemAdminOut)
async def get_item_admin(
    item_id: int,
    session: AsyncSession = Depends(get_session),
) -> ItemAdminOut:
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Материал не найден.")
    topics = await _get_item_topics(session, item_id)
    payload = ItemOut.model_validate(item).model_dump()
    return ItemAdminOut(**payload, sentinel_json=item.sentinel_json, topics=topics)


@router.post("/items/{item_id}/topics/lock", response_model=list[ItemTopicOut])
async def lock_item_topics(
    item_id: int,
    payload: ItemTopicLockRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[ItemTopicOut]:
    request_payload = payload or ItemTopicLockRequest()
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Материал не найден.")
    stmt = select(ItemTopic).where(ItemTopic.item_id == item_id)
    if request_payload.topic_ids:
        stmt = stmt.where(ItemTopic.topic_id.in_(request_payload.topic_ids))
    rows = (await session.execute(stmt)).scalars().all()
    if not rows:
        if request_payload.topic_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указанные темы не привязаны к материалу.",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Темы не найдены.")
    for row in rows:
        row.locked = True
    await session.commit()
    return await _get_item_topics(session, item_id)


@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(
    session: AsyncSession = Depends(get_session),
) -> list[AlertOut]:
    result = await session.execute(select(Alert).order_by(Alert.created_at.desc()))
    return [AlertOut.model_validate(alert) for alert in result.scalars().all()]


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut)
async def ack_alert(
    alert_id: int,
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


@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert_admin(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
) -> AlertOut:
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Алерт не найден.")
    alert.status = "resolved"
    await emit_resolved_alert(session, alert.dedup_key, "Алерт закрыт вручную.")
    await session.commit()
    await session.refresh(alert)
    return AlertOut.model_validate(alert)


@router.get("/metrics", response_model=list[MetricOut])
async def list_metrics(
    session: AsyncSession = Depends(get_session),
) -> list[MetricOut]:
    result = await session.execute(select(Metric).order_by(Metric.collected_at.desc()).limit(200))
    return [MetricOut.model_validate(metric) for metric in result.scalars().all()]


@router.get("/subscriptions", response_model=list[SubscriptionOut])
async def list_subscriptions(
    session: AsyncSession = Depends(get_session),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None, alias="to"),
    plan_tier: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    user_id: int | None = None,
    tg_id: int | None = None,
) -> list[SubscriptionOut]:
    stmt = select(Subscription)
    if tg_id is not None:
        stmt = stmt.join(User, Subscription.user_id == User.id).where(User.tg_id == tg_id)
    if user_id is not None:
        stmt = stmt.where(Subscription.user_id == user_id)
    if plan_tier:
        stmt = stmt.where(Subscription.plan_tier == plan_tier)
    if status_filter:
        stmt = stmt.where(Subscription.status == status_filter)
    if from_:
        stmt = stmt.where(Subscription.created_at >= from_)
    if to:
        stmt = stmt.where(Subscription.created_at <= to)
    result = await session.execute(stmt.order_by(Subscription.created_at.desc()))
    return [SubscriptionOut.model_validate(sub) for sub in result.scalars().all()]


@router.post("/subscriptions", response_model=SubscriptionOut)
async def create_subscription(
    payload: SubscriptionCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> SubscriptionOut:
    if not payload.user_id and not payload.tg_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите user_id или tg_id.",
        )
    user = None
    if payload.user_id:
        result = await session.execute(select(User).where(User.id == payload.user_id))
        user = result.scalar_one_or_none()
        if user and payload.tg_id and user.tg_id != payload.tg_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id и tg_id не совпадают.",
            )
    if not user:
        result = await session.execute(select(User).where(User.tg_id == payload.tg_id))
        user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    started_at = payload.started_at or datetime.now(timezone.utc)
    subscription = Subscription(
        user_id=user.id,
        plan_tier=payload.plan_tier,
        status=payload.status,
        amount_rub=payload.amount_rub,
        started_at=started_at,
        expires_at=payload.expires_at,
    )
    session.add(subscription)
    user.plan_tier = payload.plan_tier
    user.plan_expires_at = payload.expires_at
    await session.commit()
    await session.refresh(subscription)
    return SubscriptionOut.model_validate(subscription)


@router.get("/financials/summary", response_model=SubscriptionSummaryOut)
async def financials_summary(
    session: AsyncSession = Depends(get_session),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None, alias="to"),
) -> SubscriptionSummaryOut:
    filters = []
    if from_:
        filters.append(Subscription.created_at >= from_)
    if to:
        filters.append(Subscription.created_at <= to)
    revenue = await session.execute(
        select(func.coalesce(func.sum(Subscription.amount_rub), 0)).where(*filters)
    )
    revenue_rub = int(revenue.scalar_one() or 0)
    payments = await session.execute(select(func.count()).select_from(Subscription).where(*filters))
    payments_count = int(payments.scalar_one())
    new_subscriptions_count = payments_count
    boundary = to or datetime.now(timezone.utc)
    active_filters = [
        Subscription.status == "active",
        Subscription.started_at <= boundary,
        or_(Subscription.expires_at.is_(None), Subscription.expires_at >= boundary),
    ]
    active_count_result = await session.execute(
        select(func.count()).select_from(Subscription).where(*active_filters)
    )
    active_subscriptions_count = int(active_count_result.scalar_one())
    tier_rows = await session.execute(
        select(
            Subscription.plan_tier,
            func.coalesce(func.sum(Subscription.amount_rub), 0),
            func.count(),
        )
        .where(*filters)
        .group_by(Subscription.plan_tier)
    )
    by_tier: dict[str, SubscriptionSummaryTierOut] = {}
    for plan, revenue_sum, count in tier_rows.all():
        by_tier[str(plan)] = SubscriptionSummaryTierOut(
            revenue_rub=int(revenue_sum or 0), count=int(count)
        )
    for tier in (PlanTier.FREE, PlanTier.PRO, PlanTier.CORP):
        by_tier.setdefault(str(tier), SubscriptionSummaryTierOut(revenue_rub=0, count=0))
    return SubscriptionSummaryOut(
        revenue_rub=revenue_rub,
        payments_count=payments_count,
        new_subscriptions_count=new_subscriptions_count,
        active_subscriptions_count=active_subscriptions_count,
        by_tier=by_tier,
    )


@router.get("/financials", response_model=list[SubscriptionOut])
async def list_financials(
    session: AsyncSession = Depends(get_session),
) -> list[SubscriptionOut]:
    result = await session.execute(select(Subscription).order_by(Subscription.created_at.desc()))
    return [SubscriptionOut.model_validate(sub) for sub in result.scalars().all()]


@router.post("/financials/grant")
async def manual_grant(
    payload: ManualGrantRequest,
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
    session: AsyncSession = Depends(get_session),
) -> OrgOut:
    if not payload.admin_user_id and not payload.admin_user_tg_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите admin_user_id или admin_user_tg_id.",
        )
    user = None
    if payload.admin_user_id:
        result = await session.execute(select(User).where(User.id == payload.admin_user_id))
        user = result.scalar_one_or_none()
    if not user and payload.admin_user_tg_id:
        result = await session.execute(select(User).where(User.tg_id == payload.admin_user_tg_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(tg_id=payload.admin_user_tg_id)
            session.add(user)
            await session.flush()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    org = Org(name=payload.name, admin_user_id=user.id)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return OrgOut.model_validate(org)


@router.get("/corp/orgs", response_model=list[OrgOut])
async def list_orgs(
    session: AsyncSession = Depends(get_session),
) -> list[OrgOut]:
    result = await session.execute(select(Org).order_by(Org.created_at.desc()))
    return [OrgOut.model_validate(org) for org in result.scalars().all()]


@router.get("/corp/orgs/{org_id}/members", response_model=list[OrgMemberOut])
async def list_org_members(
    org_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[OrgMemberOut]:
    result = await session.execute(select(OrgMember).where(OrgMember.org_id == org_id))
    return [OrgMemberOut.model_validate(member) for member in result.scalars().all()]


@router.post("/corp/orgs/{org_id}/editor-chat", response_model=OrgOut)
async def update_editor_chat(
    org_id: int,
    payload: OrgEditorChatRequest,
    session: AsyncSession = Depends(get_session),
) -> OrgOut:
    result = await session.execute(select(Org).where(Org.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена.")
    org.editor_chat_id = payload.editor_chat_id
    await session.commit()
    await session.refresh(org)
    return OrgOut.model_validate(org)


@router.post("/corp/orgs/{org_id}/invites", response_model=OrgInviteOut)
async def create_org_invite(
    org_id: int,
    payload: OrgInviteCreate = OrgInviteCreate(),
    session: AsyncSession = Depends(get_session),
) -> OrgInviteOut:
    invite = await create_invite(session, org_id, payload.expires_in_hours)
    await session.commit()
    return OrgInviteOut.model_validate(invite)
