from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.api.routers.sync import get_optional_garmin_sync_service
from src.api.schemas import (
    CalendarResponse,
    GarminActivityRead,
    RescheduleUpdate,
    ScheduleCreate,
    ScheduledWorkoutRead,
    ScheduledWorkoutWithActivity,
)
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import GarminActivity, ScheduledWorkout
from src.services.calendar_service import get_range, reschedule, schedule, unschedule
from src.services.profile_service import get_or_create_profile
from src.services.sync_orchestrator import SyncOrchestrator

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


@router.get("", response_model=CalendarResponse)
async def get_calendar_range(
    start: date,
    end: date,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CalendarResponse:
    """Return scheduled workouts and unplanned activities within the given date range."""
    workouts = await get_range(session, start, end, current_user.id)

    # Batch-load matched activities by matched_activity_id
    activity_ids = {w.matched_activity_id for w in workouts if w.matched_activity_id is not None}
    activities_map: dict[int, GarminActivity] = {}
    if activity_ids:
        result = await session.exec(
            select(GarminActivity).where(
                GarminActivity.id.in_(activity_ids)  # type: ignore[union-attr]
            )
        )
        activities_map = {a.id: a for a in result.all() if a.id is not None}  # type: ignore[union-attr]

    # Build ScheduledWorkoutWithActivity objects
    workout_responses = [
        ScheduledWorkoutWithActivity(
            **ScheduledWorkoutRead.model_validate(w).model_dump(),
            matched_activity_id=w.matched_activity_id,
            activity=GarminActivityRead.model_validate(activities_map[w.matched_activity_id])
            if w.matched_activity_id in activities_map
            else None,
        )
        for w in workouts
    ]

    # Query for unplanned activities (all GarminActivity in date range that are NOT matched to any workout)
    paired_activity_ids_result = await session.exec(
        select(ScheduledWorkout.matched_activity_id).where(
            ScheduledWorkout.matched_activity_id.is_not(None),  # type: ignore[union-attr]
            ScheduledWorkout.user_id == current_user.id,
        )
    )
    paired_activity_ids = set(paired_activity_ids_result.all())

    unplanned_result = await session.exec(
        select(GarminActivity).where(
            GarminActivity.user_id == current_user.id,
            GarminActivity.date >= start,
            GarminActivity.date <= end,
        )
    )
    unplanned_activities = [
        GarminActivityRead.model_validate(a)
        for a in unplanned_result.all()
        if a.id not in paired_activity_ids
    ]

    return CalendarResponse(
        workouts=workout_responses,
        unplanned_activities=unplanned_activities,
    )


@router.post("/{scheduled_id}/pair/{activity_id}", response_model=ScheduledWorkoutWithActivity)
async def pair_activity(
    scheduled_id: int,
    activity_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScheduledWorkoutWithActivity:
    """Manually pair a scheduled workout with a Garmin activity."""
    workout = await session.get(ScheduledWorkout, scheduled_id)
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workout not found")

    activity = await session.get(GarminActivity, activity_id)
    if activity is None or activity.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Activity not found")

    if workout.matched_activity_id is not None:
        raise HTTPException(status_code=409, detail="Workout already paired")

    # Check if activity is already paired with another workout
    existing_pair = (
        await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.matched_activity_id == activity_id,
                ScheduledWorkout.id != scheduled_id,
            )
        )
    ).first()
    if existing_pair is not None:
        raise HTTPException(status_code=409, detail="Activity is already paired with another workout")

    workout.matched_activity_id = activity.id
    workout.completed = True
    workout.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(workout)
    await session.commit()
    await session.refresh(workout)

    return ScheduledWorkoutWithActivity(
        **ScheduledWorkoutRead.model_validate(workout).model_dump(),
        matched_activity_id=workout.matched_activity_id,
        activity=GarminActivityRead.model_validate(activity),
    )


@router.post("/{scheduled_id}/unpair", response_model=ScheduledWorkoutWithActivity)
async def unpair_activity(
    scheduled_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScheduledWorkoutWithActivity:
    """Remove the pairing between a scheduled workout and its matched activity."""
    workout = await session.get(ScheduledWorkout, scheduled_id)
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workout not found")

    if workout.matched_activity_id is None:
        raise HTTPException(status_code=400, detail="Workout is not paired")

    workout.matched_activity_id = None
    workout.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(workout)
    await session.commit()
    await session.refresh(workout)

    return ScheduledWorkoutWithActivity(
        **ScheduledWorkoutRead.model_validate(workout).model_dump(),
        matched_activity_id=None,
        activity=None,
    )


@router.patch("/{scheduled_id}", response_model=ScheduledWorkoutRead)
async def patch_reschedule(
    scheduled_id: int,
    body: RescheduleUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScheduledWorkoutRead:
    """Move a scheduled workout to a new date and/or update notes."""
    try:
        sw = await reschedule(session, scheduled_id, body.date, current_user.id, notes=body.notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ScheduledWorkoutRead.model_validate(sw)


@router.delete("/{scheduled_id}", status_code=204)
async def delete_schedule(
    scheduled_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    garmin: SyncOrchestrator | None = Depends(get_optional_garmin_sync_service),
) -> Response:
    """Delete a scheduled workout.

    If the workout was previously synced to Garmin, the corresponding Garmin
    workout is also deleted (best-effort — local deletion always succeeds even
    if the Garmin call fails).
    """
    try:
        await unschedule(
            session,
            scheduled_id,
            current_user.id,
            garmin_deleter=garmin.delete_workout if garmin is not None else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(status_code=204)


