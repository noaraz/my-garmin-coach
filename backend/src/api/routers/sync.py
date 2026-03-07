from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from src.api.dependencies import get_session, get_sync_service
from src.db.models import ScheduledWorkout
from src.services.sync_orchestrator import SyncOrchestrator

router = APIRouter(prefix="/api/sync", tags=["sync"])

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
# Routes — literal path "/all" MUST be registered before "/{workout_id}"
# ---------------------------------------------------------------------------


@router.post("/all", response_model=SyncAllResponse)
def sync_all(
    session: Session = Depends(get_session),
    sync_service: SyncOrchestrator = Depends(get_sync_service),
) -> SyncAllResponse:
    """Sync all workouts whose status is 'pending' or 'modified'.

    Returns:
        Counts of workouts that were successfully synced or failed.
    """
    statement = select(ScheduledWorkout).where(
        ScheduledWorkout.sync_status.in_(_PENDING_STATUSES)  # type: ignore[attr-defined]
    )
    workouts = session.exec(statement).all()

    synced = 0
    failed = 0

    for workout in workouts:
        try:
            garmin_id: str = sync_service.sync_workout(
                resolved_steps=[],
                workout_name="",
                date=str(workout.date),
            )
            workout.garmin_workout_id = garmin_id
            workout.sync_status = "synced"
            session.add(workout)
            synced += 1
        except Exception:  # noqa: BLE001
            workout.sync_status = "failed"
            session.add(workout)
            failed += 1

    session.commit()
    return SyncAllResponse(synced=synced, failed=failed)


@router.post("/{workout_id}", response_model=SyncSingleResponse)
def sync_single(
    workout_id: int,
    session: Session = Depends(get_session),
    sync_service: SyncOrchestrator = Depends(get_sync_service),
) -> SyncSingleResponse:
    """Sync a single scheduled workout by id.

    Fetches the scheduled workout, calls the sync service, and persists
    the resulting status and Garmin workout ID.

    Returns:
        The workout id, updated sync_status, and garmin_workout_id.

    Raises:
        HTTPException 404: if no ScheduledWorkout with the given id exists.
    """
    workout = session.get(ScheduledWorkout, workout_id)
    if workout is None:
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    try:
        garmin_id: str = sync_service.sync_workout(
            resolved_steps=[],
            workout_name="",
            date=str(workout.date),
        )
        workout.garmin_workout_id = garmin_id
        workout.sync_status = "synced"
    except Exception:  # noqa: BLE001
        workout.sync_status = "failed"

    session.add(workout)
    session.commit()
    session.refresh(workout)

    return SyncSingleResponse(
        id=workout.id,  # type: ignore[arg-type]
        sync_status=workout.sync_status,
        garmin_workout_id=workout.garmin_workout_id,
    )


@router.get("/status", response_model=list[SyncStatusItem])
def sync_status(
    session: Session = Depends(get_session),
) -> list[SyncStatusItem]:
    """Return all scheduled workouts with their sync status.

    Returns:
        List of items with id, date, sync_status, and garmin_workout_id.
    """
    workouts = session.exec(select(ScheduledWorkout)).all()
    return [SyncStatusItem.model_validate(w) for w in workouts]
