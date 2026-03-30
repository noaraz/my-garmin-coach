from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool


class InviteResponse(BaseModel):
    code: str


class GoogleAuthRequest(BaseModel):
    access_token: str
    invite_code: Optional[str] = None


# GoogleAuthResponse reuses AccessTokenResponse (access_token + token_type only).
GoogleAuthResponse = AccessTokenResponse


class BootstrapRequest(BaseModel):
    setup_token: str
    google_access_token: str


class BootstrapResponse(BaseModel):
    invite_codes: list[str]


class ResetAdminsRequest(BaseModel):
    setup_token: str


class ResetAdminsResponse(BaseModel):
    deleted: int


class LogoutResponse(BaseModel):
    ok: bool = True


class LogoutAllResponse(BaseModel):
    revoked: int


class GarminConnectRequest(BaseModel):
    email: str
    password: str


class GarminStatusResponse(BaseModel):
    connected: bool
    credentials_stored: bool = False
