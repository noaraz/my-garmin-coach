from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session, get_sync_service
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import ScheduledWorkout, WorkoutTemplate
from src.repositories.calendar import scheduled_workout_repository
from src.services.sync_orchestrator import SyncOrchestrator

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

_PENDING_STATUSES = ("pending", "modified")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class SyncSingleResponse(BaseModel):
    id: int
    sync_status: str
    garmin_workout_id: str | None = None


class SyncAllResponse(BaseModel):
    synced: int
    failed: int


class SyncStatusItem(BaseModel):
    id: int
    date: date
    sync_status: str
    garmin_workout_id: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _sync_and_persist(
    session: AsyncSession,
    sync_service: SyncOrchestrator,
    workout: ScheduledWorkout,
) -> str | None:
    """Sync one workout against Garmin and update its status fields in-place.

    Loads resolved_steps from the workout's JSON field and the display name
    from the linked WorkoutTemplate. Caller is responsible for committing.

    Returns:
        Garmin workout ID on success, None on failure.
    """
    resolved_steps: list = (
        json.loads(workout.resolved_steps) if workout.resolved_steps else []
    )
    workout_name = ""
    if workout.workout_template_id is not None:
        template = await session.get(WorkoutTemplate, workout.workout_template_id)
        workout_name = template.name if template else ""

    try:
        garmin_id: str = sync_service.sync_workout(
            resolved_steps=resolved_steps,
            workout_name=workout_name,
            date=str(workout.date),
        )
        workout.garmin_workout_id = garmin_id
        workout.sync_status = "synced"
        return garmin_id
    except Exception:  # noqa: BLE001
        workout.sync_status = "failed"
        return None


# ---------------------------------------------------------------------------
# Routes — literal path "/all" MUST be registered before "/{workout_id}"
# ---------------------------------------------------------------------------


@router.post("/all", response_model=SyncAllResponse)
async def sync_all(
    session: AsyncSession = Depends(get_session),
    sync_service: SyncOrchestrator = Depends(get_sync_service),
    current_user: User = Depends(get_current_user),
) -> SyncAllResponse:
    """Sync all workouts whose status is 'pending' or 'modified'.

    Returns:
        Counts of workouts that were successfully synced or failed.
    """
    workouts = await scheduled_workout_repository.get_by_status(session, _PENDING_STATUSES)
    results = [await _sync_and_persist(session, sync_service, w) for w in workouts]
    await session.commit()
    synced = sum(1 for r in results if r is not None)
    return SyncAllResponse(synced=synced, failed=len(results) - synced)


@router.post("/{workout_id}", response_model=SyncSingleResponse)
async def sync_single(
    workout_id: int,
    session: AsyncSession = Depends(get_session),
    sync_service: SyncOrchestrator = Depends(get_sync_service),
    current_user: User = Depends(get_current_user),
) -> SyncSingleResponse:
    """Sync a single scheduled workout by id.

    Returns:
        The workout id, updated sync_status, and garmin_workout_id.

    Raises:
        HTTPException 404: if no ScheduledWorkout with the given id exists.
    """
    workout = await scheduled_workout_repository.get(session, workout_id)
    if workout is None:
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    await _sync_and_persist(session, sync_service, workout)
    session.add(workout)
    await session.commit()
    await session.refresh(workout)

    return SyncSingleResponse(
        id=workout.id,  # type: ignore[arg-type]
        sync_status=workout.sync_status,
        garmin_workout_id=workout.garmin_workout_id,
    )


@router.get("/status", response_model=list[SyncStatusItem])
async def sync_status(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[SyncStatusItem]:
    """Return all scheduled workouts with their sync status.

    Returns:
        List of items with id, date, sync_status, and garmin_workout_id.
    """
    workouts = await scheduled_workout_repository.get_all(session)
    return [SyncStatusItem.model_validate(w) for w in workouts]
