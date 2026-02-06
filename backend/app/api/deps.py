from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin import is_admin
from app.core.config import get_settings
from app.core.security import validate_init_data
from app.db.session import get_session
from app.models.user import User

settings = get_settings()


async def _get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalars().first()


async def get_current_user(
    init_data: str | None = Header(default=None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not init_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Необходим initData.")
    try:
        init = validate_init_data(init_data, settings.bot_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    user = await _get_user_by_tg_id(session, init.user_id)
    if not user:
        user = User(tg_id=init.user_id, username=init.user.get("username"))
        session.add(user)
        await session.flush()
    return user


async def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not is_admin(user.tg_id, settings.admin_id_list):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ только для админов.")
    return user
