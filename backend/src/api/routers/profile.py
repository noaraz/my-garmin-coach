from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.api.dependencies import get_session
from src.api.schemas import ProfileRead, ProfileUpdate
from src.services.profile_service import get_or_create_profile, update_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
def get_profile(session: Session = Depends(get_session)) -> ProfileRead:
    """Return the singleton athlete profile, creating it if necessary."""
    profile = get_or_create_profile(session)
    return ProfileRead.model_validate(profile)


@router.put("", response_model=ProfileRead)
def put_profile(
    body: ProfileUpdate,
    session: Session = Depends(get_session),
) -> ProfileRead:
    """Update the singleton athlete profile."""
    data = body.model_dump(exclude_none=True)
    profile = update_profile(session, data)
    return ProfileRead.model_validate(profile)
