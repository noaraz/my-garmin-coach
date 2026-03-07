from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.api.schemas import HRZoneCreate, HRZoneRead, PaceZoneRead
from src.services.profile_service import get_or_create_profile
from src.services.zone_service import (
    get_hr_zones,
    get_pace_zones,
    recalculate_hr_zones,
    recalculate_pace_zones,
    set_hr_zones,
)

router = APIRouter(prefix="/api/v1/zones", tags=["zones"])


@router.get("/hr", response_model=list[HRZoneRead])
async def list_hr_zones(session: AsyncSession = Depends(get_session)) -> list[HRZoneRead]:
    """Return the current HR zones for the singleton profile."""
    profile = await get_or_create_profile(session)
    zones = await get_hr_zones(session, profile.id)
    return [HRZoneRead.model_validate(z) for z in zones]


@router.put("/hr", response_model=list[HRZoneRead])
async def put_hr_zones(
    body: list[HRZoneCreate],
    session: AsyncSession = Depends(get_session),
) -> list[HRZoneRead]:
    """Replace all HR zones with custom values."""
    profile = await get_or_create_profile(session)
    zones_data = [z.model_dump() for z in body]
    zones = await set_hr_zones(session, profile.id, zones_data)
    return [HRZoneRead.model_validate(z) for z in zones]


@router.post("/hr/recalculate", response_model=list[HRZoneRead])
async def recalc_hr_zones(session: AsyncSession = Depends(get_session)) -> list[HRZoneRead]:
    """Recalculate HR zones from LTHR using Coggan method."""
    profile = await get_or_create_profile(session)
    if not profile.lthr:
        raise HTTPException(
            status_code=422,
            detail="Profile has no LTHR set; cannot recalculate HR zones.",
        )
    await recalculate_hr_zones(session, profile)
    zones = await get_hr_zones(session, profile.id)
    return [HRZoneRead.model_validate(z) for z in zones]


@router.get("/pace", response_model=list[PaceZoneRead])
async def list_pace_zones(session: AsyncSession = Depends(get_session)) -> list[PaceZoneRead]:
    """Return the current pace zones for the singleton profile."""
    profile = await get_or_create_profile(session)
    zones = await get_pace_zones(session, profile.id)
    return [PaceZoneRead.model_validate(z) for z in zones]


@router.post("/pace/recalculate", response_model=list[PaceZoneRead])
async def recalc_pace_zones(session: AsyncSession = Depends(get_session)) -> list[PaceZoneRead]:
    """Recalculate pace zones from threshold_pace."""
    profile = await get_or_create_profile(session)
    if not profile.threshold_pace:
        raise HTTPException(
            status_code=422,
            detail="Profile has no threshold_pace set; cannot recalculate pace zones.",
        )
    await recalculate_pace_zones(session, profile)
    zones = await get_pace_zones(session, profile.id)
    return [PaceZoneRead.model_validate(z) for z in zones]
