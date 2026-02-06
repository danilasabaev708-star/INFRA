from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limits import DeliveryMode
from app.db.session import SessionLocal
from app.models.delivery import DeliveryMessage
from app.models.item import Item, ItemTopic
from app.models.user import User, user_topics
from app.services.telegram import build_deepdive_keyboard, format_smart_card, get_bot

logger = logging.getLogger(__name__)
_pending_instants: dict[int, set[int]] = defaultdict(set)
_last_digest_sent: dict[int, datetime] = {}


def _now_msk() -> datetime:
    return datetime.now(tz=ZoneInfo("Europe/Moscow"))


def _is_in_quiet_hours(user: User, now: datetime | None = None) -> bool:
    if user.quiet_hours_start is None or user.quiet_hours_end is None:
        return False
    now = now or _now_msk()
    start = user.quiet_hours_start
    end = user.quiet_hours_end
    if start == end:
        return False
    hour = now.hour
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


async def _already_delivered(session: AsyncSession, user_id: int, item_id: int) -> bool:
    result = await session.execute(
        select(DeliveryMessage.id).where(
            DeliveryMessage.user_id == user_id, DeliveryMessage.item_id == item_id
        )
    )
    return result.scalar_one_or_none() is not None


async def _user_topic_ids(session: AsyncSession, user_id: int) -> list[int]:
    rows = await session.execute(select(user_topics.c.topic_id).where(user_topics.c.user_id == user_id))
    return [row[0] for row in rows.all()]


async def _item_matches_user(session: AsyncSession, item: Item, user: User) -> bool:
    topic_ids = await _user_topic_ids(session, user.id)
    if not topic_ids:
        return False
    result = await session.execute(
        select(ItemTopic.item_id).where(
            ItemTopic.item_id == item.id, ItemTopic.topic_id.in_(topic_ids)
        )
    )
    return result.scalar_one_or_none() is not None


async def _send_item(session: AsyncSession, user: User, item: Item) -> None:
    if not item.id:
        await session.flush()
    if await _already_delivered(session, user.id, item.id):
        return
    try:
        bot = get_bot()
        message = await bot.send_message(
            chat_id=user.tg_id,
            text=format_smart_card(item),
            reply_markup=build_deepdive_keyboard(item.id),
            disable_web_page_preview=False,
        )
        session.add(
            DeliveryMessage(
                user_id=user.id,
                item_id=item.id,
                chat_id=user.tg_id,
                message_id=message.message_id,
            )
        )
        await session.flush()
    except Exception:
        logger.exception("Failed to send item %s to user %s", item.id, user.id)


async def enqueue_instant_delivery(session: AsyncSession, item: Item) -> None:
    if not item.id:
        await session.flush()
    result = await session.execute(
        select(User)
        .join(user_topics, user_topics.c.user_id == User.id)
        .join(ItemTopic, ItemTopic.topic_id == user_topics.c.topic_id)
        .where(ItemTopic.item_id == item.id)
        .distinct()
    )
    users = result.scalars().all()
    now = _now_msk()
    for user in users:
        if user.delivery_mode != DeliveryMode.INSTANT:
            continue
        if user.only_important and item.impact != "high":
            continue
        if await _already_delivered(session, user.id, item.id):
            continue
        if _is_in_quiet_hours(user, now):
            _pending_instants[user.id].add(item.id)
            continue
        await _send_item(session, user, item)


async def _deliver_pending_instants(session: AsyncSession) -> None:
    if not _pending_instants:
        return
    for user_id, item_ids in list(_pending_instants.items()):
        user = await session.get(User, user_id)
        if not user:
            _pending_instants.pop(user_id, None)
            continue
        if _is_in_quiet_hours(user):
            continue
        if not item_ids:
            _pending_instants.pop(user_id, None)
            continue
        items = (
            await session.execute(select(Item).where(Item.id.in_(list(item_ids))))
        ).scalars().all()
        remaining = set(item_ids)
        for item in items:
            if user.only_important and item.impact != "high":
                remaining.discard(item.id)
                continue
            if not await _item_matches_user(session, item, user):
                remaining.discard(item.id)
                continue
            await _send_item(session, user, item)
            remaining.discard(item.id)
        if remaining:
            _pending_instants[user_id] = remaining
        else:
            _pending_instants.pop(user_id, None)


async def _deliver_digest_for_user(
    session: AsyncSession,
    user: User,
    last_sent: datetime | None,
) -> datetime | None:
    if _is_in_quiet_hours(user):
        return last_sent
    topic_ids = await _user_topic_ids(session, user.id)
    if not topic_ids:
        return last_sent
    stmt = (
        select(Item)
        .join(ItemTopic, ItemTopic.item_id == Item.id)
        .where(ItemTopic.topic_id.in_(topic_ids))
        .outerjoin(
            DeliveryMessage,
            and_(
                DeliveryMessage.user_id == user.id,
                DeliveryMessage.item_id == Item.id,
            ),
        )
        .where(DeliveryMessage.id.is_(None))
    )
    if user.only_important:
        stmt = stmt.where(Item.impact == "high")
    if last_sent:
        stmt = stmt.where(Item.created_at >= last_sent)
    stmt = stmt.order_by(Item.published_at.desc().nullslast(), Item.id.desc()).distinct()
    items = (await session.execute(stmt)).scalars().all()
    if not items:
        return datetime.now(timezone.utc)
    for item in items:
        await _send_item(session, user, item)
    return datetime.now(timezone.utc)


async def _deliver_due_digests(session: AsyncSession) -> None:
    result = await session.execute(select(User).where(User.delivery_mode == DeliveryMode.DIGEST))
    users = result.scalars().all()
    now = datetime.now(timezone.utc)
    for user in users:
        last_sent = _last_digest_sent.get(user.id)
        interval = timedelta(hours=max(user.batch_interval_hours, 1))
        if last_sent and now - last_sent < interval:
            continue
        updated = await _deliver_digest_for_user(session, user, last_sent)
        if updated:
            _last_digest_sent[user.id] = updated


async def delivery_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        async with SessionLocal() as session:
            try:
                await _deliver_pending_instants(session)
                await _deliver_due_digests(session)
                await session.commit()
            except Exception:
                logger.exception("Delivery loop failed")
                await session.rollback()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            continue
