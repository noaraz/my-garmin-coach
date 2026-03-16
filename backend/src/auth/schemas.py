from __future__ import annotations

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    email: str
    password: str
    invite_code: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


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


class RegisterResponse(BaseModel):
    id: int
    email: str


class InviteResponse(BaseModel):
    code: str


class BootstrapRequest(BaseModel):
    setup_token: str
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class BootstrapResponse(BaseModel):
    invite_codes: list[str]


class GarminConnectRequest(BaseModel):
    email: str
    password: str


class GarminStatusResponse(BaseModel):
    connected: bool
