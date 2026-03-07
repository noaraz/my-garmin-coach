from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from src.api.dependencies import get_session
from src.api.schemas import RescheduleUpdate, ScheduleCreate, ScheduledWorkoutRead
from src.services.calendar_service import get_range, reschedule, schedule, unschedule
from src.services.profile_service import get_or_create_profile

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.post("", response_model=ScheduledWorkoutRead, status_code=201)
def post_schedule(
    body: ScheduleCreate,
    session: Session = Depends(get_session),
) -> ScheduledWorkoutRead:
    """Schedule a workout template on a specific date."""
    profile = get_or_create_profile(session)
    try:
        sw = schedule(session, body.template_id, body.date, profile)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ScheduledWorkoutRead.model_validate(sw)


@router.get("", response_model=list[ScheduledWorkoutRead])
def get_calendar_range(
    start: date,
    end: date,
    session: Session = Depends(get_session),
) -> list[ScheduledWorkoutRead]:
    """Return scheduled workouts within the given date range."""
    workouts = get_range(session, start, end)
    return [ScheduledWorkoutRead.model_validate(w) for w in workouts]


@router.patch("/{scheduled_id}", response_model=ScheduledWorkoutRead)
def patch_reschedule(
    scheduled_id: int,
    body: RescheduleUpdate,
    session: Session = Depends(get_session),
) -> ScheduledWorkoutRead:
    """Move a scheduled workout to a new date."""
    try:
        sw = reschedule(session, scheduled_id, body.date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ScheduledWorkoutRead.model_validate(sw)


@router.delete("/{scheduled_id}", status_code=204)
def delete_schedule(
    scheduled_id: int,
    session: Session = Depends(get_session),
) -> Response:
    """Delete a scheduled workout."""
    try:
        unschedule(session, scheduled_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(status_code=204)
