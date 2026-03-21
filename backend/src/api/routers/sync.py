from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timezone
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
from src.garmin.adapter import GarminAdapter
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
# Garmin sync service dependency (auth-aware, avoids circular import)
# ---------------------------------------------------------------------------


async def _get_garmin_adapter(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminAdapter:
    """Return a GarminAdapter wired to the user's stored Garmin token.

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

    return GarminAdapter(garmin_client)


async def _get_garmin_sync_service(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SyncOrchestrator:
    """Return a SyncOrchestrator wired to the user's stored Garmin token.

    Raises:
        HTTPException 403: if the user has not connected their Garmin account.
    """
    adapter = await _get_garmin_adapter(current_user=current_user, session=session)

    def _resolver(steps: list[Any], **_: Any) -> list[Any]:
        return steps

    return SyncOrchestrator(
        sync_service=GarminSyncService(adapter),
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
        templates = await _preload_templates(session, workouts)
        # SQLAlchemy AsyncSession is NOT concurrency-safe — use sequential loop
        for w in workouts:
            await _sync_and_persist(session, sync_service, w, hr_zone_map, pace_zone_map, templates)
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Auto-sync after zone change failed (continuing): %s", exc)


async def background_sync(user_id: int) -> None:
    """Fire-and-forget: open a fresh session, rebuild the Garmin service, and sync.

    Intended for use with FastAPI BackgroundTasks so zone-change endpoints can
    return immediately while Garmin sync happens after the response is sent.
    Self-exits silently when Garmin is not connected.
    """
    try:
        from src.db.database import async_session_factory  # avoid circular import at module level

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if user is None:
                return
            try:
                adapter = await _get_garmin_adapter(current_user=user, session=session)
            except HTTPException:
                return  # Garmin not connected — nothing to do
            orchestrator = SyncOrchestrator(
                sync_service=GarminSyncService(adapter),
                formatter=format_workout,
                resolver=lambda steps, **_: steps,
            )
            await sync_modified_workouts(session, orchestrator, user)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Background sync failed (user_id=%s): %s", user_id, exc)


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
    activities_fetched: int = 0
    activities_matched: int = 0
    fetch_error: str | None = None


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
    hr_zones, pace_zones = await asyncio.gather(
        hr_zone_repository.get_by_profile(session, profile.id),
        pace_zone_repository.get_by_profile(session, profile.id),
    )
    return (
        {z.zone_number: (z.lower_bpm, z.upper_bpm) for z in hr_zones},
        {z.zone_number: (z.lower_pace, z.upper_pace) for z in pace_zones},
    )


async def _preload_templates(
    session: AsyncSession, workouts: list[ScheduledWorkout]
) -> dict[int, WorkoutTemplate]:
    """Batch-load all WorkoutTemplates referenced by the given workouts."""
    ids = {w.workout_template_id for w in workouts if w.workout_template_id is not None}
    if not ids:
        return {}
    result = await session.exec(
        select(WorkoutTemplate).where(
            WorkoutTemplate.id.in_(ids)  # type: ignore[union-attr]
        )
    )
    return {t.id: t for t in result.all()}  # type: ignore[union-attr]


async def _sync_and_persist(
    session: AsyncSession,
    sync_service: SyncOrchestrator,
    workout: ScheduledWorkout,
    hr_zone_map: dict[int, tuple[float, float]] | None = None,
    pace_zone_map: dict[int, tuple[float, float]] | None = None,
    templates: dict[int, WorkoutTemplate] | None = None,
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

    # Load the template (from pre-loaded dict if available, else single fetch)
    template: WorkoutTemplate | None = None
    if workout.workout_template_id is not None:
        if templates is not None:
            template = templates.get(workout.workout_template_id)
        else:
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
        garmin_id: str = await sync_service.sync_workout(
            resolved_steps=resolved_steps,
            workout_name=workout_name,
            workout_description=workout_description,
            date=str(workout.date),
        )
        workout.garmin_workout_id = garmin_id
        workout.sync_status = "synced"
        session.add(workout)
        return garmin_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Sync failed for workout %s: %s", workout.id, exc, exc_info=True)
        workout.sync_status = "failed"
        session.add(workout)
        return None


# ---------------------------------------------------------------------------
# Routes — literal path "/all" MUST be registered before "/{workout_id}"
# ---------------------------------------------------------------------------


@router.post("/all", response_model=SyncAllResponse)
async def sync_all(
    fetch_days: int = 30,
    session: AsyncSession = Depends(get_session),
    sync_service: SyncOrchestrator = Depends(_get_garmin_sync_service),
    current_user: User = Depends(get_current_user),
) -> SyncAllResponse:
    """Sync all workouts whose status is 'pending' or 'modified', then fetch activities.

    Args:
        fetch_days: Number of days to fetch activities for (default 30).

    Returns:
        Counts of workouts synced/failed, activities fetched/matched, and any fetch error.
    """
    hr_zone_map, pace_zone_map = await _get_zone_maps(session, current_user)
    workouts = await scheduled_workout_repository.get_by_status(session, _PENDING_STATUSES, current_user.id)
    templates = await _preload_templates(session, workouts)
    results = [
        await _sync_and_persist(session, sync_service, w, hr_zone_map, pace_zone_map, templates)
        for w in workouts
    ]
    await session.commit()
    synced = sum(1 for r in results if r is not None)
    failed = len(results) - synced

    # Fetch activities (best-effort)
    activities_fetched = 0
    activities_matched = 0
    fetch_error = None
    try:
        from datetime import timedelta

        from src.services.activity_fetch_service import activity_fetch_service

        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=fetch_days)

        # Reuse the adapter from the orchestrator (avoid second token decrypt)
        adapter = sync_service.adapter

        fetch_result = await activity_fetch_service.fetch_and_store(
            adapter, session, current_user.id, str(start_date), str(end_date)
        )
        activities_fetched = fetch_result.stored

        activities_matched = await activity_fetch_service.match_activities(
            session, current_user.id, start_date, end_date
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        fetch_error = str(exc)
        logger.warning("Activity fetch failed (continuing): %s", exc)

    return SyncAllResponse(
        synced=synced,
        failed=failed,
        activities_fetched=activities_fetched,
        activities_matched=activities_matched,
        fetch_error=fetch_error,
    )


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
    await session.commit()

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
