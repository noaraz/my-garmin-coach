from __future__ import annotations

import garth as garth
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.schemas import GarminConnectRequest, GarminStatusResponse
from src.core.config import get_settings
from src.db.models import AthleteProfile
from src.garmin.encryption import encrypt_token

router = APIRouter(prefix="/api/v1/garmin", tags=["garmin"])


async def _get_or_create_profile(user: User, session: AsyncSession) -> AthleteProfile:
    """Return existing AthleteProfile for user, or create one."""
    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == user.id)
        )
    ).first()
    if profile is None:
        profile = AthleteProfile(user_id=user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


@router.post("/connect", response_model=GarminStatusResponse)
async def connect_garmin(
    request: GarminConnectRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminStatusResponse:
    """Connect Garmin account by authenticating with garth.

    The user's email and password are discarded immediately after use.
    The OAuth token is encrypted at rest using a per-user Fernet key.
    """
    settings = get_settings()

    # Authenticate with Garmin via garth
    try:
        client = garth.Client()
        client.login(request.email, request.password)
        token_json: str = client.dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Garmin authentication failed: {exc}") from exc
    finally:
        # Discard credentials immediately
        del request

    # Encrypt and store token
    encrypted = encrypt_token(current_user.id, settings.garmincoach_secret_key, token_json)

    profile = await _get_or_create_profile(current_user, session)
    profile.garmin_oauth_token_encrypted = encrypted
    profile.garmin_connected = True
    session.add(profile)
    await session.commit()

    return GarminStatusResponse(connected=True)


@router.get("/status", response_model=GarminStatusResponse)
async def garmin_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminStatusResponse:
    """Return whether the current user has a connected Garmin account."""
    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == current_user.id)
        )
    ).first()
    connected = profile is not None and profile.garmin_connected
    return GarminStatusResponse(connected=connected)


@router.post("/disconnect", response_model=GarminStatusResponse)
async def disconnect_garmin(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminStatusResponse:
    """Remove stored Garmin token and mark account as disconnected."""
    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == current_user.id)
        )
    ).first()
    if profile is not None:
        profile.garmin_oauth_token_encrypted = None
        profile.garmin_connected = False
        session.add(profile)
        await session.commit()

    return GarminStatusResponse(connected=False)
