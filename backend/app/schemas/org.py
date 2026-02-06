from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrgCreate(BaseModel):
    name: str
    admin_user_id: int | None = None
    admin_user_tg_id: int | None = None


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    admin_user_id: int
    editor_chat_id: int | None
    created_at: datetime


class OrgPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    editor_chat_id: int | None


class OrgInviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    org_id: int
    token: str
    used_by: int | None
    used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class OrgInviteCreate(BaseModel):
    expires_in_hours: int = 24


class OrgEditorChatRequest(BaseModel):
    editor_chat_id: int


class OrgMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    org_id: int
    user_id: int
    role: str
    joined_at: datetime


class CorpInviteAcceptRequest(BaseModel):
    token: str
