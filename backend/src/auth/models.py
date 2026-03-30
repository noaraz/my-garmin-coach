from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class RefreshToken(SQLModel, table=True):
    """DB-backed opaque refresh token for sliding window rotation."""

    __tablename__ = "refreshtoken"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, index=True)  # SHA-256 of raw token
    user_id: int = Field(foreign_key="user.id", index=True)
    expires_at: datetime  # reset to now+7d on each rotation
    revoked: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class User(SQLModel, table=True):
    """Application user — Google OAuth only."""

    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    google_oauth_sub: Optional[str] = Field(default=None, unique=True)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class InviteCode(SQLModel, table=True):
    """Single-use invite code for invite-only registration."""

    __tablename__ = "invitecode"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    created_by: int = Field(foreign_key="user.id")
    used_by: Optional[int] = Field(default=None, foreign_key="user.id")
    used_at: Optional[datetime] = Field(default=None)
