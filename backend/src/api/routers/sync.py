from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from garth.exc import GarthHTTPError

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.core.config import get_settings
from src.db.models import AthleteProfile, ScheduledWorkout, WorkoutTemplate
from src.garmin.adapter import GarminAdapter
from src.garmin import client_cache
from src.garmin.auto_reconnect import attempt_auto_reconnect
from src.garmin.client_factory import create_api_client
from src.garmin.encryption import decrypt_token
from src.garmin.formatter import format_workout
from src.garmin.sync_service import GarminSyncService
from src.garmin.token_persistence import persist_refreshed_token
from src.repositories.calendar import scheduled_workout_repository
from src.repositories.zones import hr_zone_repository, pace_zone_repository
from src.services.calendar_service import resolve_builder_steps
from src.services.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

# Include "failed" so a re-sync attempt retries previously failed workouts.
_PENDING_STATUSES = ("pending", "modified", "failed")

# ---------------------------------------------------------------------------
# Exchange 429 detection + module-level cooldown
# ---------------------------------------------------------------------------

# Per-user exchange cooldown: {user_id: cooldown_until_monotonic}
_exchange_cooldowns: dict[int, float] = {}
_EXCHANGE_COOLDOWN_SECONDS = 1800  # 30 minutes


def _is_exchange_429(exc: Exception) -> bool:
    """Return True when exc indicates a Garmin OAuth exchange 429."""
    msg = str(exc).lower()
    return "429" in msg and "exchange" in msg


def _set_exchange_cooldown(user_id: int) -> None:
    """Set a 30-minute exchange cooldown for a user."""
    _exchange_cooldowns[user_id] = time.monotonic() + _EXCHANGE_COOLDOWN_SECONDS


def _exchange_on_cooldown(user_id: int) -> bool:
    """Check if exchange is on cooldown for a user."""
    until = _exchange_cooldowns.get(user_id)
    if until is None:
        return False
    if time.monotonic() >= until:
        del _exchange_cooldowns[user_id]
        return False
    return True


# ---------------------------------------------------------------------------
# Garmin sync service dependency (auth-aware, avoids circular import)
# ---------------------------------------------------------------------------


async def _get_garmin_adapter(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminAdapter:
    """Return a GarminAdapter wired to the user's stored Garmin token.

    Uses the in-process client cache when available (avoids re-decrypting
    and re-creating the adapter on every request within the same process).

    Raises:
        HTTPException 403: if the user has not connected their Garmin account.
    """
    # Check in-process cache first
    cached = client_cache.get(current_user.id)
    if cached is not None:
        return cached

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

    adapter = create_api_client(token_json)
    client_cache.put(current_user.id, adapter)
    return adapter


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


# NOTE: Calendar reconciliation via GET /workout-service/schedule/{id} is not feasible.
# The garminconnect library's get_scheduled_workout_by_id() expects a schedule ENTRY ID,
# but Garmin returns 404 for GET on schedule entry IDs (write-only endpoint) and 403 for
# GET using template IDs. There is no accessible Garmin API endpoint to check whether a
# specific workout template is still on the calendar without pushing a new schedule entry.


def _is_garmin_404(exc: Exception) -> bool:
    """Return True when exc is a Garmin 404 (resource not found on Connect).

    Two cases:
    - GarthHTTPError: garth wrapped a requests.HTTPError → check exc.error.response
    - curl_cffi HTTPError: garth only catches requests.HTTPError, so curl_cffi's own
      HTTPError bubbles up unwrapped → check exc.response directly
    """
    if isinstance(exc, GarthHTTPError):
        return (
            exc.error.response is not None
            and exc.error.response.status_code == 404
        )
    # curl_cffi raises its own HTTPError (not requests.HTTPError); garth's except clause
    # doesn't catch it, so it arrives here unwrapped with a .response attribute.
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None) == 404
    # Final fallback: some HTTP client variants surface the status only in the message
    # (e.g. requests.exceptions.HTTPError("404 Client Error: ...")).
    return "404" in str(exc)


async def _persist_refreshed_token(
    sync_service: SyncOrchestrator,
    user_id: int,
    session: AsyncSession,
) -> None:
    """Persist garth's current token state back to the DB.

    Delegates to the shared token_persistence module.
    """
    await persist_refreshed_token(sync_service, user_id, session)


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
            # Persist any OAuth2 token refresh that occurred during sync.
            # Without this, each background sync re-exchanges the same expired
            # token and hits Garmin's rate limit on the exchange endpoint (429).
            await _persist_refreshed_token(orchestrator, user_id, session)
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
    garmin_workouts: list[dict[str, Any]] | None = None,
) -> str | None:
    """Sync one workout against Garmin and update its status fields in-place.

    Loads resolved_steps from the workout's JSON field.  If resolved_steps is
    missing (e.g. legacy workouts), translates the linked template's builder
    steps on-the-fly using the provided zone maps.

    If the workout was already synced (garmin_workout_id is set), the old
    Garmin workout is deleted first so re-syncing produces a clean update
    rather than a duplicate.

    When *garmin_workouts* is provided and the workout has no garmin_workout_id,
    a name-based dedup check is performed first.  If a matching Garmin workout
    is found, its ID is linked so the subsequent delete+push cycle replaces it
    instead of creating a duplicate.

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
            workout.garmin_workout_id = None
        except Exception as exc:  # noqa: BLE001
            if _is_garmin_404(exc):
                # Workout already gone from Garmin — clear stale ID and proceed with push.
                logger.info(
                    "Old Garmin workout %s already deleted (404) — clearing ID and re-pushing",
                    workout.garmin_workout_id,
                )
                workout.garmin_workout_id = None
            else:
                # Real error (network, auth, rate limit) — keep ID so we can retry next sync.
                # Pushing a new workout now would orphan the old one on Garmin.
                logger.warning(
                    "Could not delete old Garmin workout %s — skipping re-push to avoid duplicate: %s",
                    workout.garmin_workout_id,
                    exc,
                )
                workout.sync_status = "failed"
                session.add(workout)
                return None

    # Load the template (from pre-loaded dict if available, else single fetch)
    template: WorkoutTemplate | None = None
    if workout.workout_template_id is not None:
        if templates is not None:
            template = templates.get(workout.workout_template_id)
        else:
            template = await session.get(WorkoutTemplate, workout.workout_template_id)

    workout_name = template.name if template else ""
    workout_description = (template.description or "") if template else ""

    # Dedup: if we don't have a garmin_workout_id but a matching workout exists
    # on Garmin, link it so the delete+push cycle replaces it cleanly.
    if not workout.garmin_workout_id and garmin_workouts and workout_name:
        from src.garmin.dedup import find_matching_garmin_workout

        match_id = find_matching_garmin_workout(workout_name, garmin_workouts)
        if match_id:
            logger.info(
                "Dedup: linked workout '%s' to existing Garmin workout %s",
                workout_name,
                match_id,
            )
            workout.garmin_workout_id = match_id
            # Now the delete-before-push block above already ran and found no ID,
            # so we must delete this matched workout before pushing the new one.
            try:
                sync_service.delete_workout(match_id)
                workout.garmin_workout_id = None
            except Exception as exc:  # noqa: BLE001
                if _is_garmin_404(exc):
                    # Already gone — proceed with push
                    logger.info("Matched Garmin workout %s already deleted (404)", match_id)
                    workout.garmin_workout_id = None
                else:
                    logger.warning(
                        "Could not delete matched Garmin workout %s — skipping push: %s",
                        match_id,
                        exc,
                    )
                    workout.sync_status = "failed"
                    session.add(workout)
                    return None

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
        garmin_id, _ = await sync_service.sync_workout(
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
    fetch_days: int = Query(30, ge=1, le=365),
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
    # Exchange cooldown: if we recently hit a 429, skip sync entirely.
    if _exchange_on_cooldown(current_user.id):
        return SyncAllResponse(
            synced=0,
            failed=0,
            fetch_error="Garmin sync temporarily paused (exchange rate limit). Will retry automatically.",
        )

    hr_zone_map, pace_zone_map = await _get_zone_maps(session, current_user)

    # Fetch Garmin workouts first — used for dedup.
    # This is also the first Garmin API call — if it triggers an exchange 429,
    # attempt auto-reconnect before giving up.
    garmin_workouts: list[dict[str, Any]] | None = None
    try:
        garmin_workouts = sync_service.get_workouts()
    except Exception as exc:  # noqa: BLE001
        if _is_exchange_429(exc):
            logger.warning("Exchange 429 on get_workouts — attempting auto-reconnect for user %s", current_user.id)
            adapter = await attempt_auto_reconnect(current_user.id, session)
            if adapter is None:
                _set_exchange_cooldown(current_user.id)
                return SyncAllResponse(
                    synced=0,
                    failed=0,
                    fetch_error="Garmin credentials expired. Please reconnect in Settings.",
                )
            # Rebuild orchestrator with fresh adapter and retry
            sync_service = SyncOrchestrator(
                sync_service=GarminSyncService(adapter),
                formatter=format_workout,
                resolver=lambda steps, **_: steps,
            )
            try:
                garmin_workouts = sync_service.get_workouts()
            except Exception as retry_exc:  # noqa: BLE001
                logger.warning("Retry after auto-reconnect also failed: %s", retry_exc)
                _set_exchange_cooldown(current_user.id)
                return SyncAllResponse(
                    synced=0, failed=0,
                    fetch_error="Garmin sync failed after reconnect. Please try again later.",
                )
        else:
            logger.warning("Could not fetch Garmin workouts for dedup (continuing): %s", exc)

    workouts = await scheduled_workout_repository.get_by_status(session, _PENDING_STATUSES, current_user.id)
    templates = await _preload_templates(session, workouts)

    results = [
        await _sync_and_persist(
            session, sync_service, w, hr_zone_map, pace_zone_map, templates, garmin_workouts
        )
        for w in workouts
    ]
    await session.commit()
    synced = sum(1 for r in results if r is not None)
    failed = len(results) - synced

    # Compute date window once — used by both fetch and cleanup steps.
    from datetime import timedelta

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=fetch_days)

    # Fetch activities (best-effort)
    activities_fetched = 0
    activities_matched = 0
    fetch_error = None
    try:
        from src.services.activity_fetch_service import activity_fetch_service

        # Reuse the adapter from the orchestrator (avoid second token decrypt)
        adapter = sync_service.adapter

        fetch_result = await activity_fetch_service.fetch_and_store(
            adapter, session, current_user.id, str(start_date), str(end_date)
        )
        activities_fetched = fetch_result.fetched

        activities_matched = await activity_fetch_service.match_activities(
            session, current_user.id, start_date, end_date
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        if _is_exchange_429(exc):
            # Exchange 429 during activity fetch — early-exit, don't continue to cleanup
            _set_exchange_cooldown(current_user.id)
            fetch_error = "Garmin exchange rate-limited — skipping activity fetch"
        else:
            fetch_error = "Activity fetch failed — please retry"
            logger.warning("Activity fetch failed (continuing): %s", exc)

    # Best-effort cleanup: delete Garmin scheduled workouts for all completed workouts
    # in the sync window that still have garmin_workout_id set.
    # Handles both newly-paired workouts and pre-existing ones (retroactive fix).
    try:
        paired_with_garmin = (
            await session.exec(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.user_id == current_user.id,
                    ScheduledWorkout.completed == True,  # noqa: E712
                    ScheduledWorkout.garmin_workout_id.is_not(None),  # type: ignore[union-attr]
                    ScheduledWorkout.date >= start_date,
                    ScheduledWorkout.date <= end_date,
                )
            )
        ).all()

        for workout in paired_with_garmin:
            garmin_id = workout.garmin_workout_id
            try:
                sync_service.delete_workout(garmin_id)
                workout.garmin_workout_id = None
                session.add(workout)
                logger.info("Cleared paired Garmin workout %s from calendar", garmin_id)
            except Exception as exc:  # noqa: BLE001
                if _is_garmin_404(exc):
                    # Already gone from Garmin — still clear our ID so we don't retry
                    workout.garmin_workout_id = None
                    session.add(workout)
                else:
                    logger.warning("Could not delete paired Garmin workout %s: %s", garmin_id, exc)

        if paired_with_garmin:
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Garmin paired-workout cleanup failed (continuing): %s", exc)

    # Best-effort orphan cleanup: delete Garmin workouts that match our
    # template names but are not tracked by any ScheduledWorkout in our DB.
    # These are leftovers from failed deletes or lost garmin_workout_id links.
    if garmin_workouts is not None:
        try:
            from src.garmin.dedup import find_orphaned_garmin_workouts

            all_sws = await scheduled_workout_repository.get_all(session, current_user.id)
            known_ids = {sw.garmin_workout_id for sw in all_sws if sw.garmin_workout_id}

            template_names = {t.name for t in templates.values()} if templates else set()
            # Also include templates not in the preloaded set (preload only covers pending workouts)
            all_templates_result = await session.exec(
                select(WorkoutTemplate.name).where(WorkoutTemplate.user_id == current_user.id)
            )
            template_names.update(all_templates_result.all())

            orphan_ids = find_orphaned_garmin_workouts(garmin_workouts, known_ids, template_names)
            for orphan_id in orphan_ids:
                try:
                    sync_service.delete_workout(orphan_id)
                    logger.info("Deleted orphaned Garmin workout %s", orphan_id)
                except Exception as exc:  # noqa: BLE001
                    # 404 is expected when the ID was already deleted during this sync
                    # (reconciliation marks workouts modified → re-push deletes old template).
                    if not _is_garmin_404(exc):
                        logger.warning("Could not delete orphaned Garmin workout %s: %s", orphan_id, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Orphan cleanup failed (continuing): %s", exc)

    # Persist any OAuth2 token refresh that occurred during sync.
    await _persist_refreshed_token(sync_service, current_user.id, session)

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

    await _persist_refreshed_token(sync_service, current_user.id, session)

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
