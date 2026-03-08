from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.api.schemas import ProfileRead, ProfileUpdate
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.services.profile_service import get_or_create_profile, update_profile

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


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
) -> ProfileRead:
    """Update the athlete profile for the authenticated user."""
    data = body.model_dump(exclude_none=True)
    profile = await update_profile(session, data, user_id=current_user.id)
    return ProfileRead.model_validate(profile)
