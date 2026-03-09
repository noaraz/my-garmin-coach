from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.api.routers.sync import get_optional_garmin_sync_service, sync_modified_workouts
from src.api.schemas import ProfileRead, ProfileUpdate
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.services.profile_service import get_or_create_profile, update_profile
from src.services.sync_orchestrator import SyncOrchestrator

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

# Fields that trigger zone recalculation and therefore warrant auto-sync.
_ZONE_TRIGGER_FIELDS = frozenset({"lthr", "threshold_pace"})


@router.get("", response_model=ProfileRead)
async def get_profile(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProfileRead:
    """Return the athlete profile for the authenticated user, creating it if necessary."""
    profile = await get_or_create_profile(session, user_id=current_user.id)
    return ProfileRead.model_validate(profile)


@router.put("", response_model=ProfileRead)
async def put_profile(
    body: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    garmin: SyncOrchestrator | None = Depends(get_optional_garmin_sync_service),
) -> ProfileRead:
    """Update the athlete profile for the authenticated user.

    If a zone-threshold field (lthr, threshold_pace) changed, and Garmin is
    connected, any previously-synced workouts that were marked 'modified' by
    the zone cascade are automatically re-pushed to Garmin (best-effort).
    """
    data = body.model_dump(exclude_none=True)
    profile = await update_profile(session, data, user_id=current_user.id)

    # Auto-sync only when a zone-threshold changed — avoids unnecessary Garmin
    # calls when the user is just editing their name or other profile fields.
    if garmin is not None and _ZONE_TRIGGER_FIELDS & data.keys():
        await sync_modified_workouts(session, garmin, current_user)

    return ProfileRead.model_validate(profile)
