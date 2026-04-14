"""Admin-only endpoints for runtime configuration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import SystemConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class AuthVersionRequest(BaseModel):
    version: Literal["v1", "v2"]


class AuthVersionResponse(BaseModel):
    version: str


def _require_admin(user: User) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/garmin-auth-version", response_model=AuthVersionResponse)
async def set_garmin_auth_version(
    body: AuthVersionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AuthVersionResponse:
    """Switch Garmin auth version at runtime. Admin-only."""
    _require_admin(current_user)

    row = await session.get(SystemConfig, "garmin_auth_version")
    if row is None:
        row = SystemConfig(
            key="garmin_auth_version",
            value=body.version,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(row)
    else:
        row.value = body.version
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(row)

    await session.commit()
    logger.info("Garmin auth version switched to %s by user %s", body.version, current_user.id)
    return AuthVersionResponse(version=body.version)


@router.get("/garmin-auth-version", response_model=AuthVersionResponse)
async def get_garmin_auth_version(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AuthVersionResponse:
    """Read current Garmin auth version. Admin-only."""
    _require_admin(current_user)

    row = await session.get(SystemConfig, "garmin_auth_version")
    version = row.value if row else "v1"
    return AuthVersionResponse(version=version)
