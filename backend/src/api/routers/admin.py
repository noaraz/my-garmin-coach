"""Admin-only endpoints for runtime configuration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import SystemConfig
from src.garmin import client_cache
from src.garmin.auth_version import SYSTEM_CONFIG_KEY, GarminAuthVersion, get_db_auth_version

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class AuthVersionRequest(BaseModel):
    version: GarminAuthVersion


class AuthVersionResponse(BaseModel):
    version: GarminAuthVersion


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

    row = await session.get(SystemConfig, SYSTEM_CONFIG_KEY)
    if row is None:
        row = SystemConfig(
            key=SYSTEM_CONFIG_KEY,
            value=body.version.value,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(row)
    else:
        row.value = body.version.value
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(row)

    await session.commit()
    # Cached adapters from the old version must not survive the switch —
    # otherwise sync._get_garmin_adapter's version-mismatch check is bypassed
    # on cache hits until the 1h TTL expires.
    client_cache.clear()
    logger.info("Garmin auth version switched to %s by user %s", body.version, current_user.id)
    return AuthVersionResponse(version=body.version)


@router.get("/garmin-auth-version", response_model=AuthVersionResponse)
async def get_garmin_auth_version(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AuthVersionResponse:
    """Read current Garmin auth version. Admin-only."""
    _require_admin(current_user)

    version = await get_db_auth_version(session)
    return AuthVersionResponse(version=version)
