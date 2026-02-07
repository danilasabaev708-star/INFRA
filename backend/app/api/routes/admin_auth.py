from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_admin_session
from app.core.admin_auth import (
    AdminAuthError,
    create_admin_token,
    generate_csrf_token,
    verify_admin_password,
)
from app.core.config import get_settings
from app.schemas import AdminLoginRequest, AdminMeResponse

router = APIRouter()
settings = get_settings()


def _is_prod() -> bool:
    return settings.app_env.lower() in {"prod", "production"}


def _cookie_secure() -> bool:
    return _is_prod()


@router.post("/login")
async def login(payload: AdminLoginRequest, response: Response) -> dict:
    if _is_prod() and not settings.admin_panel_password_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Админская авторизация не настроена.",
        )
    if _is_prod() and len(settings.admin_jwt_secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Админская авторизация не настроена.",
        )
    if payload.username != settings.admin_panel_username or not verify_admin_password(
        payload.password, settings.admin_panel_password_hash, settings.admin_panel_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль."
        )
    try:
        token = create_admin_token(
            settings.admin_panel_username, settings.admin_jwt_secret, settings.admin_jwt_ttl_min
        )
    except AdminAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Админская авторизация не настроена.",
        ) from exc
    csrf_token = generate_csrf_token()
    max_age = settings.admin_jwt_ttl_min * 60
    response.set_cookie(
        "admin_session",
        token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=False,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie("admin_session", path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"ok": True}


@router.get("/me", response_model=AdminMeResponse)
async def me(session=Depends(require_admin_session)) -> AdminMeResponse:
    return AdminMeResponse(authenticated=True, username=session.username)
