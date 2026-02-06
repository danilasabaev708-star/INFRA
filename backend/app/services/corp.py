from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org import OrgInvite, OrgMember


async def create_invite(session: AsyncSession, org_id: int, expires_in_hours: int = 24) -> OrgInvite:
    token = secrets.token_urlsafe(16)
    invite = OrgInvite(
        org_id=org_id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
    )
    session.add(invite)
    await session.flush()
    return invite


async def accept_invite(session: AsyncSession, token: str, user_id: int) -> OrgInvite:
    result = await session.execute(select(OrgInvite).where(OrgInvite.token == token))
    invite = result.scalar_one_or_none()
    if not invite or invite.used_at:
        raise ValueError("Инвайт недействителен.")
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise ValueError("Срок действия инвайта истёк.")
    invite.used_at = datetime.now(timezone.utc)
    invite.used_by = user_id
    session.add(OrgMember(org_id=invite.org_id, user_id=user_id, role="editor"))
    await session.flush()
    return invite
