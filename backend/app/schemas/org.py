from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrgCreate(BaseModel):
    name: str
    admin_user_id: int


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    admin_user_id: int
    editor_chat_id: int | None
    created_at: datetime


class OrgInviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    org_id: int
    token: str
    used_by: int | None
    used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
