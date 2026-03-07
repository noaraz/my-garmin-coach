from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.api.schemas import ProfileRead, ProfileUpdate
from src.services.profile_service import get_or_create_profile, update_profile

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
async def get_profile(session: AsyncSession = Depends(get_session)) -> ProfileRead:
    """Return the singleton athlete profile, creating it if necessary."""
    profile = await get_or_create_profile(session)
    return ProfileRead.model_validate(profile)


@router.put("", response_model=ProfileRead)
async def put_profile(
    body: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProfileRead:
    """Update the singleton athlete profile."""
    data = body.model_dump(exclude_none=True)
    profile = await update_profile(session, data)
    return ProfileRead.model_validate(profile)
