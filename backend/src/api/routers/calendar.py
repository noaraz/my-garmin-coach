from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.api.schemas import RescheduleUpdate, ScheduleCreate, ScheduledWorkoutRead
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.services.calendar_service import get_range, reschedule, schedule, unschedule
from src.services.profile_service import get_or_create_profile

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


@router.post("", response_model=ScheduledWorkoutRead, status_code=201)
async def post_schedule(
    body: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScheduledWorkoutRead:
    """Schedule a workout template on a specific date."""
    profile = await get_or_create_profile(session, user_id=current_user.id)
    try:
        sw = await schedule(session, body.template_id, body.date, profile)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ScheduledWorkoutRead.model_validate(sw)


@router.get("", response_model=list[ScheduledWorkoutRead])
async def get_calendar_range(
    start: date,
    end: date,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ScheduledWorkoutRead]:
    """Return scheduled workouts within the given date range."""
    workouts = await get_range(session, start, end)
    return [ScheduledWorkoutRead.model_validate(w) for w in workouts]


@router.patch("/{scheduled_id}", response_model=ScheduledWorkoutRead)
async def patch_reschedule(
    scheduled_id: int,
    body: RescheduleUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScheduledWorkoutRead:
    """Move a scheduled workout to a new date."""
    try:
        sw = await reschedule(session, scheduled_id, body.date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ScheduledWorkoutRead.model_validate(sw)


@router.delete("/{scheduled_id}", status_code=204)
async def delete_schedule(
    scheduled_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete a scheduled workout."""
    try:
        await unschedule(session, scheduled_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(status_code=204)
