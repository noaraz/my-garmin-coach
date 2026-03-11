from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import garminconnect
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.core.config import get_settings
from src.db.models import AthleteProfile, ScheduledWorkout, WorkoutTemplate
from src.garmin.encryption import decrypt_token
from src.garmin.formatter import format_workout
from src.garmin.sync_service import GarminSyncService
from src.repositories.calendar import scheduled_workout_repository
from src.repositories.zones import hr_zone_repository, pace_zone_repository
from src.services.calendar_service import resolve_builder_steps
from src.services.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

# Include "failed" so a re-sync attempt retries previously failed workouts.
_PENDING_STATUSES = ("pending", "modified", "failed")


# ---------------------------------------------------------------------------
# Garmin client adapter
# GarminSyncService expects add_workout() / schedule_workout().
# The installed garminconnect library exposes upload_workout() and a raw
# schedule endpoint instead.  This adapter bridges the gap.
# ---------------------------------------------------------------------------


class _GarminAdapter:
    """Wraps garminconnect.Garmin to match the interface GarminSyncService expects."""

    def __init__(self, client: garminconnect.Garmin) -> None:
        self._client = client

    def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]:
        """Upload a workout and return the Garmin response (contains workoutId)."""
        return self._client.upload_workout(formatted_workout)

    def schedule_workout(self, workout_id: str, workout_date: str) -> None:
        """Schedule a workout on a specific date via the Garmin Connect API."""
        url = f"{self._client.garmin_workouts_schedule_url}/{workout_id}"
        self._client.garth.post(
            "connectapi", url, json={"date": workout_date}, api=True
        )

    def update_workout(
        self, workout_id: str, formatted_workout: dict[str, Any]
    ) -> None:
        """Update an existing Garmin workout in-place."""
        url = f"/workout-service/workout/{workout_id}"
        self._client.garth.put(
            "connectapi", url, json=formatted_workout, api=True
        )

    def delete_workout(self, workout_id: str) -> None:
        """Permanently delete a workout from Garmin Connect."""
        url = f"/workout-service/workout/{workout_id}"
        self._client.garth.delete("connectapi", url, api=True)


# ---------------------------------------------------------------------------
# Garmin sync service dependency (auth-aware, avoids circular import)
# ---------------------------------------------------------------------------


async def _get_garmin_sync_service(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SyncOrchestrator:
    """Return a SyncOrchestrator wired to the user's stored Garmin token.

    Raises:
        HTTPException 403: if the user has not connected their Garmin account.
    """
    settings = get_settings()

    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == current_user.id)
        )
    ).first()

    if (
        profile is None
        or not profile.garmin_connected
        or not profile.garmin_oauth_token_encrypted
    ):
        raise HTTPException(
            status_code=403,
            detail="Garmin account not connected. Connect via Settings → Garmin Connect.",
        )

    token_json = decrypt_token(
        current_user.id,
        settings.garmincoach_secret_key,
        profile.garmin_oauth_token_encrypted,
    )

    # Restore the garth session from the stored token and inject into garminconnect
    garmin_client = garminconnect.Garmin()
    garmin_client.garth.loads(token_json)

    def _resolver(steps: list[Any], **_: Any) -> list[Any]:
        return steps

    return SyncOrchestrator(
        sync_service=GarminSyncService(_GarminAdapter(garmin_client)),
        formatter=format_workout,
        resolver=_resolver,
    )


async def sync_modified_workouts(
    session: AsyncSession,
    sync_service: SyncOrchestrator,
    current_user: User,
) -> None:
    """Sync all 'modified' and 'failed' workouts.  Best-effort — never raises.

    Called automatically after zone changes so that synced Garmin workouts are
    updated with the new zone targets without requiring the user to click
    Sync All manually.  'pending' (never-synced) workouts are intentionally
    excluded so as not to push workouts the user hasn't chosen to sync yet.
    """
    try:
        hr_zone_map, pace_zone_map = await _get_zone_maps(session, current_user)
        workouts = await scheduled_workout_repository.get_by_status(
            session, ("modified", "failed"), current_user.id
        )
        for w in workouts:
            await _sync_and_persist(session, sync_service, w, hr_zone_map, pace_zone_map)
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Auto-sync after zone change failed (continuing): %s", exc)


async def get_optional_garmin_sync_service(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SyncOrchestrator | None:
    """Like _get_garmin_sync_service but returns None when Garmin is not connected.

    Used by endpoints that perform a best-effort Garmin cleanup without
    requiring the user to have Garmin connected (e.g. DELETE /calendar/{id}).
    """
    try:
        return await _get_garmin_sync_service(current_user=current_user, session=session)
    except HTTPException:
        return None


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


async def _get_zone_maps(
    session: AsyncSession,
    current_user: User,
) -> tuple[dict[int, tuple[float, float]], dict[int, tuple[float, float]]]:
    """Return (hr_zone_map, pace_zone_map) for the current user's profile."""
    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == current_user.id)
        )
    ).first()
    if profile is None:
        return {}, {}
    hr_zones = await hr_zone_repository.get_by_profile(session, profile.id)
    pace_zones = await pace_zone_repository.get_by_profile(session, profile.id)
    return (
        {z.zone_number: (z.lower_bpm, z.upper_bpm) for z in hr_zones},
        {z.zone_number: (z.lower_pace, z.upper_pace) for z in pace_zones},
    )


async def _sync_and_persist(
    session: AsyncSession,
    sync_service: SyncOrchestrator,
    workout: ScheduledWorkout,
    hr_zone_map: dict[int, tuple[float, float]] | None = None,
    pace_zone_map: dict[int, tuple[float, float]] | None = None,
) -> str | None:
    """Sync one workout against Garmin and update its status fields in-place.

    Loads resolved_steps from the workout's JSON field.  If resolved_steps is
    missing (e.g. legacy workouts), translates the linked template's builder
    steps on-the-fly using the provided zone maps.

    If the workout was already synced (garmin_workout_id is set), the old
    Garmin workout is deleted first so re-syncing produces a clean update
    rather than a duplicate.

    Returns:
        Garmin workout ID on success, None on failure.
    """
    # If previously synced, delete the old Garmin workout before re-pushing
    # so we don't leave orphaned duplicates on Garmin Connect.
    if workout.garmin_workout_id:
        try:
            sync_service.delete_workout(workout.garmin_workout_id)
            logger.info(
                "Deleted old Garmin workout %s before re-sync", workout.garmin_workout_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not delete old Garmin workout %s (continuing): %s",
                workout.garmin_workout_id,
                exc,
            )
        workout.garmin_workout_id = None

    # Load the template once (needed for name + possible fallback translation)
    template: WorkoutTemplate | None = None
    if workout.workout_template_id is not None:
        template = await session.get(WorkoutTemplate, workout.workout_template_id)

    workout_name = template.name if template else ""
    workout_description = (template.description or "") if template else ""

    resolved_steps: list = (
        json.loads(workout.resolved_steps) if workout.resolved_steps else []
    )

    # Fallback: translate builder-format steps when resolved_steps is missing
    if not resolved_steps and template is not None:
        try:
            resolved_steps = resolve_builder_steps(
                template, hr_zone_map or {}, pace_zone_map or {}
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Step translation failed for template %s: %s", template.id, exc
            )

    try:
        garmin_id: str = sync_service.sync_workout(
            resolved_steps=resolved_steps,
            workout_name=workout_name,
            workout_description=workout_description,
            date=str(workout.date),
        )
        workout.garmin_workout_id = garmin_id
        workout.sync_status = "synced"
        return garmin_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Sync failed for workout %s: %s", workout.id, exc, exc_info=True)
        workout.sync_status = "failed"
        return None


# ---------------------------------------------------------------------------
# Routes — literal path "/all" MUST be registered before "/{workout_id}"
# ---------------------------------------------------------------------------


@router.post("/all", response_model=SyncAllResponse)
async def sync_all(
    session: AsyncSession = Depends(get_session),
    sync_service: SyncOrchestrator = Depends(_get_garmin_sync_service),
    current_user: User = Depends(get_current_user),
) -> SyncAllResponse:
    """Sync all workouts whose status is 'pending' or 'modified'.

    Returns:
        Counts of workouts that were successfully synced or failed.
    """
    hr_zone_map, pace_zone_map = await _get_zone_maps(session, current_user)
    workouts = await scheduled_workout_repository.get_by_status(session, _PENDING_STATUSES, current_user.id)
    results = [
        await _sync_and_persist(session, sync_service, w, hr_zone_map, pace_zone_map)
        for w in workouts
    ]
    await session.commit()
    synced = sum(1 for r in results if r is not None)
    return SyncAllResponse(synced=synced, failed=len(results) - synced)


@router.post("/{workout_id}", response_model=SyncSingleResponse)
async def sync_single(
    workout_id: int,
    session: AsyncSession = Depends(get_session),
    sync_service: SyncOrchestrator = Depends(_get_garmin_sync_service),
    current_user: User = Depends(get_current_user),
) -> SyncSingleResponse:
    """Sync a single scheduled workout by id.

    Returns:
        The workout id, updated sync_status, and garmin_workout_id.

    Raises:
        HTTPException 404: if no ScheduledWorkout with the given id exists.
    """
    workout = await scheduled_workout_repository.get(session, workout_id)
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    hr_zone_map, pace_zone_map = await _get_zone_maps(session, current_user)
    await _sync_and_persist(session, sync_service, workout, hr_zone_map, pace_zone_map)
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
    workouts = await scheduled_workout_repository.get_all(session, current_user.id)
    return [SyncStatusItem.model_validate(w) for w in workouts]
