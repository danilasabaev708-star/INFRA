from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.alert import Alert
from app.services.alerts import create_alert, resolve_alert


@pytest.mark.asyncio
async def test_resolved_alert_emitted_even_when_muted(session) -> None:
    alert = await create_alert(session, "dedup-key", "Title", "Message")
    alert.muted_until = datetime.now(timezone.utc) + timedelta(hours=1)
    await session.commit()

    resolved = await resolve_alert(session, "dedup-key", "Resolved message")
    await session.commit()

    result = await session.execute(select(Alert).where(Alert.dedup_key == "dedup-key"))
    alerts = result.scalars().all()
    assert len(alerts) == 2
    assert resolved.status == "resolved"
