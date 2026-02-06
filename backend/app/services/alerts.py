from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.alert import Alert

settings = get_settings()


async def _send_telegram_message(text: str) -> None:
    if not settings.bot_token or not settings.alerts_tg_group_id:
        return
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    payload = {"chat_id": settings.alerts_tg_group_id, "text": text}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)


async def create_alert(
    session: AsyncSession,
    dedup_key: str,
    title: str,
    message: str,
    severity: str = "warning",
    status: str = "open",
) -> Alert:
    now = datetime.now(timezone.utc)
    recent_query = select(Alert).where(Alert.dedup_key == dedup_key).order_by(Alert.created_at.desc())
    result = await session.execute(recent_query)
    last_alert = result.scalars().first()

    if last_alert and last_alert.muted_until and last_alert.muted_until > now:
        return last_alert

    if last_alert and last_alert.last_sent_at and now - last_alert.last_sent_at < timedelta(minutes=15):
        return last_alert

    alert = Alert(
        dedup_key=dedup_key,
        title=title,
        message=message,
        severity=severity,
        status=status,
        last_sent_at=now,
    )
    session.add(alert)
    await session.flush()
    await _send_telegram_message(f"{title}\n{message}")
    return alert


async def resolve_alert(session: AsyncSession, dedup_key: str, message: str) -> Alert:
    now = datetime.now(timezone.utc)
    alert = Alert(
        dedup_key=dedup_key,
        title="RESOLVED",
        message=message,
        severity="info",
        status="resolved",
        last_sent_at=now,
    )
    session.add(alert)
    await session.flush()
    await _send_telegram_message(f"RESOLVED\n{message}")
    return alert
