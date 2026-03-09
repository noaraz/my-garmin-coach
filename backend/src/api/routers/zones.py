from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.api.routers.sync import get_optional_garmin_sync_service, sync_modified_workouts
from src.api.schemas import HRZoneCreate, HRZoneRead, PaceZoneRead
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.services.profile_service import get_or_create_profile
from src.services.sync_orchestrator import SyncOrchestrator
from src.services.zone_service import (
    get_hr_zones,
    get_pace_zones,
    recalculate_hr_zones,
    recalculate_pace_zones,
    set_hr_zones,
)

router = APIRouter(prefix="/api/v1/zones", tags=["zones"])


@router.get("/hr", response_model=list[HRZoneRead])
async def list_hr_zones(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[HRZoneRead]:
    """Return the current HR zones for the authenticated user's profile."""
    profile = await get_or_create_profile(session, user_id=current_user.id)
    zones = await get_hr_zones(session, profile.id)
    return [HRZoneRead.model_validate(z) for z in zones]


@router.put("/hr", response_model=list[HRZoneRead])
async def put_hr_zones(
    body: list[HRZoneCreate],
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    garmin: SyncOrchestrator | None = Depends(get_optional_garmin_sync_service),
) -> list[HRZoneRead]:
    """Replace all HR zones with custom values.

    After saving the new zones, any previously-synced workouts that were
    marked 'modified' by the zone cascade are automatically re-pushed to
    Garmin (best-effort).
    """
    profile = await get_or_create_profile(session, user_id=current_user.id)
    zones_data = [z.model_dump() for z in body]
    zones = await set_hr_zones(session, profile.id, current_user.id, zones_data)
    if garmin is not None:
        await sync_modified_workouts(session, garmin, current_user)
    return [HRZoneRead.model_validate(z) for z in zones]


@router.post("/hr/recalculate", response_model=list[HRZoneRead])
async def recalc_hr_zones(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    garmin: SyncOrchestrator | None = Depends(get_optional_garmin_sync_service),
) -> list[HRZoneRead]:
    """Recalculate HR zones from LTHR using Coggan method.

    After recalculating, any previously-synced workouts that were marked
    'modified' by the zone cascade are automatically re-pushed to Garmin
    (best-effort).
    """
    profile = await get_or_create_profile(session, user_id=current_user.id)
    if not profile.lthr:
        raise HTTPException(
            status_code=422,
            detail="Profile has no LTHR set; cannot recalculate HR zones.",
        )
    await recalculate_hr_zones(session, profile)
    if garmin is not None:
        await sync_modified_workouts(session, garmin, current_user)
    zones = await get_hr_zones(session, profile.id)
    return [HRZoneRead.model_validate(z) for z in zones]


@router.get("/pace", response_model=list[PaceZoneRead])
async def list_pace_zones(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[PaceZoneRead]:
    """Return the current pace zones for the authenticated user's profile."""
    profile = await get_or_create_profile(session, user_id=current_user.id)
    zones = await get_pace_zones(session, profile.id)
    return [PaceZoneRead.model_validate(z) for z in zones]


@router.post("/pace/recalculate", response_model=list[PaceZoneRead])
async def recalc_pace_zones(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    garmin: SyncOrchestrator | None = Depends(get_optional_garmin_sync_service),
) -> list[PaceZoneRead]:
    """Recalculate pace zones from threshold_pace.

    After recalculating, any previously-synced workouts that were marked
    'modified' by the zone cascade are automatically re-pushed to Garmin
    (best-effort).
    """
    profile = await get_or_create_profile(session, user_id=current_user.id)
    if not profile.threshold_pace:
        raise HTTPException(
            status_code=422,
            detail="Profile has no threshold_pace set; cannot recalculate pace zones.",
        )
    await recalculate_pace_zones(session, profile)
    if garmin is not None:
        await sync_modified_workouts(session, garmin, current_user)
    zones = await get_pace_zones(session, profile.id)
    return [PaceZoneRead.model_validate(z) for z in zones]
