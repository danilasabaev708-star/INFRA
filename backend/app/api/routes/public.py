from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rate_limits import PlanTier
from app.db.session import get_session
from app.models.item import Item
from app.models.org import Org
from app.models.topic import Topic
from app.models.user import User
from app.schemas import (
    AiRequest,
    AiResponse,
    AuthResponse,
    CorpInviteAcceptRequest,
    InitDataRequest,
    ItemOut,
    OrgPublicOut,
    TopicOut,
    UserOut,
    UserSettingsUpdate,
    UserTopicsUpdate,
)
from app.services.ai_assistant import generate_bulleted_answer
from app.services.ai_usage import RateLimitError, check_and_record_usage
from app.services.corp import accept_invite
from app.services.jobs import JobsAccessError, ensure_jobs_access

router = APIRouter()


async def _apply_user_settings(
    update: UserSettingsUpdate, user: User, session: AsyncSession
) -> UserOut:
    if update.jobs_enabled is not None:
        if user.plan_tier != PlanTier.PRO:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Jobs доступны только на PRO.")
        user.jobs_enabled = update.jobs_enabled
    for field, value in update.model_dump(exclude={"jobs_enabled"}, exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user)

@router.post("/auth/telegram", response_model=AuthResponse)
async def auth_telegram(
    payload: InitDataRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    user = await get_current_user(init_data=payload.init_data, session=session)
    await session.commit()
    return AuthResponse(user=UserOut.model_validate(user), message="Добро пожаловать!")


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me/settings", response_model=UserOut)
async def update_settings(
    update: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    return await _apply_user_settings(update, user, session)


@router.patch("/profile", response_model=UserOut)
async def update_profile(
    update: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    return await _apply_user_settings(update, user, session)


@router.get("/topics", response_model=list[TopicOut])
async def list_topics(session: AsyncSession = Depends(get_session)) -> list[TopicOut]:
    result = await session.execute(select(Topic))
    return [TopicOut.model_validate(topic) for topic in result.scalars().all()]


@router.put("/me/topics", response_model=UserOut)
async def update_topics(
    payload: UserTopicsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    result = await session.execute(select(Topic).where(Topic.id.in_(payload.topic_ids)))
    topics = result.scalars().all()
    user.topics = topics
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user)


@router.get("/jobs")
async def list_jobs(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        ensure_jobs_access(user)
    except JobsAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc
    result = await session.execute(
        select(Item)
        .where(Item.is_job.is_(True))
        .order_by(Item.published_at.desc().nullslast(), Item.id.desc())
        .limit(50)
    )
    items = result.scalars().all()
    return {
        "items": [ItemOut.model_validate(item) for item in items],
        "message": f"Найдено {len(items)} вакансий",
    }


@router.post("/ai/ask", response_model=AiResponse)
async def ai_ask(
    payload: AiRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AiResponse:
    try:
        await check_and_record_usage(session, user, payload.purpose)
        await session.commit()
    except RateLimitError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message) from exc
    answer = await generate_bulleted_answer(payload.prompt)
    return AiResponse(message=answer)


@router.post("/corp/invites/{token}")
async def accept_corp_invite(
    token: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        invite = await accept_invite(session, token, user.id)
        await session.commit()
        return {"message": "Вы добавлены в редакцию.", "invite_id": invite.id}
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/corp/accept-invite", response_model=OrgPublicOut)
async def accept_corp_invite_public(
    payload: CorpInviteAcceptRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrgPublicOut:
    try:
        invite = await accept_invite(session, payload.token, user.id)
        result = await session.execute(select(Org).where(Org.id == invite.org_id))
        org = result.scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена.")
        await session.commit()
        return OrgPublicOut.model_validate(org)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/studio")
async def studio_info(user: User = Depends(get_current_user)) -> dict:
    if user.plan_tier != PlanTier.CORP:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Студия доступна только CORP.")
    return {"message": "Студия редакции в разработке.", "queue": []}
