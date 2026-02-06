from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin import is_admin
from app.core.admin_auth import AdminAuthError, AdminSession, decode_admin_token
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


async def require_admin_session(request: Request) -> AdminSession:
    token = request.cookies.get("admin_session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется вход администратора.")
    try:
        payload = decode_admin_token(token, settings.admin_jwt_secret)
    except AdminAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется вход администратора.") from exc
    sub = payload.get("sub")
    if not isinstance(sub, str) or not secrets.compare_digest(sub, settings.admin_panel_username):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ только для админов.")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Некорректный CSRF-токен.")
    return AdminSession(username=payload["sub"])
