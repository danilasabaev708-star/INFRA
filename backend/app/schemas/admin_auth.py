from __future__ import annotations

from pydantic import BaseModel


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminMeResponse(BaseModel):
    authenticated: bool
    username: str
