from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


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


# GoogleAuthResponse reuses TokenResponse (access_token + refresh_token + token_type).
GoogleAuthResponse = TokenResponse


class BootstrapRequest(BaseModel):
    setup_token: str
    google_access_token: str


class BootstrapResponse(BaseModel):
    invite_codes: list[str]


class ResetAdminsRequest(BaseModel):
    setup_token: str


class ResetAdminsResponse(BaseModel):
    deleted: int


class GarminConnectRequest(BaseModel):
    email: str
    password: str


class GarminStatusResponse(BaseModel):
    connected: bool
    credentials_stored: bool = False
