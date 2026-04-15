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

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.core.config import get_settings
from src.db.models import AthleteProfile, ScheduledWorkout, SystemConfig, WorkoutTemplate
from src.garmin.adapter_protocol import (
    GarminAdapterProtocol,
    GarminNotFoundError,
    GarminRateLimitError,
)
from src.garmin import client_cache
from src.garmin.auto_reconnect import attempt_auto_reconnect
from src.garmin.client_factory import create_adapter
from src.garmin.encryption import decrypt_token
from src.garmin.sync_service import GarminSyncService
from src.garmin.workout_facade import WorkoutFacade
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


def clear_exchange_cooldown(user_id: int) -> None:
    """Clear exchange cooldown for a user (e.g. after successful reconnect)."""
    _exchange_cooldowns.pop(user_id, None)


# ---------------------------------------------------------------------------
# Garmin sync service dependency (auth-aware, avoids circular import)
# ---------------------------------------------------------------------------


async def _get_garmin_adapter(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminAdapterProtocol:
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

    auth_version_row = await session.get(SystemConfig, "garmin_auth_version")
    auth_version = auth_version_row.value if auth_version_row else "v1"

    adapter = create_adapter(token_json, auth_version=auth_version)
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

    auth_version_row = await session.get(SystemConfig, "garmin_auth_version")
    auth_version = auth_version_row.value if auth_version_row else "v1"
    facade = WorkoutFacade(auth_version=auth_version)

    def _resolver(steps: list[Any], **_: Any) -> list[Any]:
        return steps

    return SyncOrchestrator(
        sync_service=GarminSyncService(adapter),
        formatter=facade.build_workout,
        resolver=_resolver,
    )



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
        logger.warning("Auto-sync after zone change failed (continuing): %s", type(exc).__name__)


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
            auth_version_row = await session.get(SystemConfig, "garmin_auth_version")
            auth_version = auth_version_row.value if auth_version_row else "v1"
            facade = WorkoutFacade(auth_version=auth_version)
            orchestrator = SyncOrchestrator(
                sync_service=GarminSyncService(adapter),
                formatter=facade.build_workout,
                resolver=lambda steps, **_: steps,
            )
            await sync_modified_workouts(session, orchestrator, user)
            # Persist any OAuth2 token refresh that occurred during sync.
            # Without this, each background sync re-exchanges the same expired
            # token and hits Garmin's rate limit on the exchange endpoint (429).
            await _persist_refreshed_token(orchestrator, user_id, session)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Background sync failed (user_id=%s): %s", user_id, type(exc).__name__)


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
    reconciled: int = 0
    rescheduled: int = 0
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
        except GarminNotFoundError:
            # Workout already gone from Garmin — clear stale ID and proceed with push.
            logger.info(
                "Old Garmin workout %s already deleted (404) — clearing ID and re-pushing",
                workout.garmin_workout_id,
            )
            workout.garmin_workout_id = None
        except Exception as exc:  # noqa: BLE001
            # Real error (network, auth, rate limit) — keep ID so we can retry next sync.
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
            except GarminNotFoundError:
                # Already gone — proceed with push
                logger.info("Matched Garmin workout %s already deleted (404)", match_id)
                workout.garmin_workout_id = None
            except Exception as exc:  # noqa: BLE001
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

    logger.info("sync_all started for user %s", current_user.id)
    hr_zone_map, pace_zone_map = await _get_zone_maps(session, current_user)

    # Fetch Garmin workouts first — used for dedup.
    # This is also the first Garmin API call — if it triggers an exchange 429,
    # attempt auto-reconnect before giving up.
    garmin_workouts: list[dict[str, Any]] | None = None
    try:
        garmin_workouts = sync_service.get_workouts()
        logger.info("Fetched %d Garmin workouts for user %s", len(garmin_workouts), current_user.id)
    except GarminRateLimitError:
        logger.warning("Rate limit on get_workouts — attempting auto-reconnect for user %s", current_user.id)
        adapter = await attempt_auto_reconnect(current_user.id, session)
        if adapter is None:
            _set_exchange_cooldown(current_user.id)
            return SyncAllResponse(
                synced=0,
                failed=0,
                fetch_error="Garmin credentials expired. Please reconnect in Settings.",
            )
        # Rebuild orchestrator with fresh adapter and retry
        auth_version_row = await session.get(SystemConfig, "garmin_auth_version")
        auth_version = auth_version_row.value if auth_version_row else "v1"
        facade = WorkoutFacade(auth_version=auth_version)
        sync_service = SyncOrchestrator(
            sync_service=GarminSyncService(adapter),
            formatter=facade.build_workout,
            resolver=lambda steps, **_: steps,
        )
        try:
            garmin_workouts = sync_service.get_workouts()
        except Exception as retry_exc:  # noqa: BLE001
            logger.warning("Retry after auto-reconnect also failed: %s", type(retry_exc).__name__)
            _set_exchange_cooldown(current_user.id)
            return SyncAllResponse(
                synced=0, failed=0,
                fetch_error="Garmin sync failed after reconnect. Please try again later.",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch Garmin workouts for dedup (continuing): %s", type(exc).__name__)

    # ── Reconciliation: detect synced workouts not on Garmin calendar ────
    reconciled = 0
    rescheduled = 0
    garmin_id_set = (
        {str(gw.get("workoutId", "")) for gw in garmin_workouts}
        if garmin_workouts else set()
    )

    try:
        synced_with_ids = (
            await session.exec(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.user_id == current_user.id,
                    ScheduledWorkout.sync_status == "synced",
                    ScheduledWorkout.completed == False,  # noqa: E712
                    ScheduledWorkout.garmin_workout_id.is_not(None),  # type: ignore[union-attr]
                )
            )
        ).all()

        logger.info(
            "Reconciliation check: %d synced workouts with garmin_workout_id for user %s",
            len(synced_with_ids),
            current_user.id,
        )

        if synced_with_ids:
            # Determine which months to fetch from Garmin calendar.
            # NOTE: Each Garmin "month" spans ~5 weeks (includes partial
            # weeks from adjacent months), so items may appear in multiple
            # month responses.  This is fine — find_unscheduled_workouts
            # uses set membership, and find_duplicate_calendar_entries
            # deduplicates by entry ID.
            dates = [sw.date for sw in synced_with_ids if sw.date]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                months_to_fetch: set[tuple[int, int]] = set()
                current_month = min_date.replace(day=1)
                while current_month <= max_date:
                    months_to_fetch.add((current_month.year, current_month.month))
                    if current_month.month == 12:
                        current_month = current_month.replace(year=current_month.year + 1, month=1)
                    else:
                        current_month = current_month.replace(month=current_month.month + 1)

                calendar_items: list[dict[str, Any]] = []
                for year, month in months_to_fetch:
                    try:
                        items = sync_service.get_calendar_items(year, month)
                        calendar_items.extend(items)
                    except Exception as cal_exc:  # noqa: BLE001
                        logger.warning(
                            "Could not fetch Garmin calendar for %d-%02d: %s",
                            year, month, type(cal_exc).__name__,
                        )

                logger.info(
                    "Fetched %d Garmin calendar items across %d months for user %s",
                    len(calendar_items),
                    len(months_to_fetch),
                    current_user.id,
                )

                # ── Duplicate cleanup: remove extra calendar entries ──
                from src.garmin.dedup import (
                    find_duplicate_calendar_entries,
                    find_unscheduled_workouts,
                )

                duplicate_schedule_ids = find_duplicate_calendar_entries(calendar_items)
                if duplicate_schedule_ids:
                    logger.info(
                        "Found %d duplicate calendar entries for user %s — cleaning up",
                        len(duplicate_schedule_ids),
                        current_user.id,
                    )
                    for sched_id in duplicate_schedule_ids:
                        try:
                            sync_service.unschedule_workout(sched_id)
                            logger.info("Removed duplicate calendar entry %s", sched_id)
                        except Exception as dup_exc:  # noqa: BLE001
                            logger.warning(
                                "Failed to remove duplicate calendar entry %s: %s",
                                sched_id,
                                type(dup_exc).__name__,
                            )

                db_workouts_for_check = [
                    {"garmin_workout_id": sw.garmin_workout_id, "date": str(sw.date)}
                    for sw in synced_with_ids
                    if sw.garmin_workout_id and sw.date
                ]
                unscheduled = find_unscheduled_workouts(db_workouts_for_check, calendar_items)

                logger.info(
                    "Reconciliation: %d unscheduled out of %d checked for user %s",
                    len(unscheduled),
                    len(db_workouts_for_check),
                    current_user.id,
                )

                if unscheduled:
                    # NOTE: reschedule_workout is additive — it creates a new
                    # calendar entry.  If the original entry was actually there
                    # (e.g. on a month boundary we didn't fetch), this creates
                    # a duplicate.  The duplicate cleanup runs BEFORE this loop,
                    # so any new duplicates will be cleaned up on the next
                    # sync_all invocation (idempotent).
                    unscheduled_ids = {u["garmin_workout_id"] for u in unscheduled}
                    for sw in synced_with_ids:
                        if sw.garmin_workout_id not in unscheduled_ids:
                            continue
                        # Template still on Garmin? → just re-schedule (cheap)
                        if sw.garmin_workout_id in garmin_id_set:
                            try:
                                sync_service.reschedule_workout(
                                    sw.garmin_workout_id, str(sw.date)
                                )
                                rescheduled += 1
                                logger.info(
                                    "Re-scheduled workout %s on %s (template existed)",
                                    sw.garmin_workout_id,
                                    sw.date,
                                )
                            except Exception as sched_exc:  # noqa: BLE001
                                logger.warning(
                                    "Re-schedule failed for %s: %s — falling back to re-push",
                                    sw.garmin_workout_id,
                                    type(sched_exc).__name__,
                                )
                                sw.sync_status = "modified"
                                sw.garmin_workout_id = None
                                session.add(sw)
                                reconciled += 1
                        else:
                            # Template also gone → full re-push
                            sw.sync_status = "modified"
                            sw.garmin_workout_id = None
                            session.add(sw)
                            reconciled += 1

                    if rescheduled or reconciled:
                        await session.commit()
                        logger.info(
                            "Reconciliation for user %s: %d re-scheduled, %d queued for re-push",
                            current_user.id,
                            rescheduled,
                            reconciled,
                        )
    except Exception as recon_exc:  # noqa: BLE001
        logger.warning("Reconciliation failed (continuing): %s", type(recon_exc).__name__)

    workouts = await scheduled_workout_repository.get_by_status(session, _PENDING_STATUSES, current_user.id)
    logger.info("Push loop: %d workouts in pending/modified/failed for user %s", len(workouts), current_user.id)
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
    except GarminRateLimitError:
        _set_exchange_cooldown(current_user.id)
        fetch_error = "Garmin exchange rate-limited — skipping activity fetch"
    except Exception as exc:  # noqa: BLE001
        fetch_error = "Activity fetch failed — please retry"
        logger.warning("Activity fetch failed (continuing): %s", type(exc).__name__)

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
            except GarminNotFoundError:
                # Already gone from Garmin — still clear our ID so we don't retry
                workout.garmin_workout_id = None
                session.add(workout)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not delete paired Garmin workout %s: %s", garmin_id, type(exc).__name__)

        if paired_with_garmin:
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Garmin paired-workout cleanup failed (continuing): %s", type(exc).__name__)

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
                except GarminNotFoundError:
                    pass  # Already deleted during this sync (e.g. reconciliation re-push)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not delete orphaned Garmin workout %s: %s", orphan_id, type(exc).__name__)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Orphan cleanup failed (continuing): %s", type(exc).__name__)

    # Persist any OAuth2 token refresh that occurred during sync.
    await _persist_refreshed_token(sync_service, current_user.id, session)

    logger.info(
        "sync_all completed for user %s: synced=%d failed=%d reconciled=%d rescheduled=%d activities=%d matched=%d",
        current_user.id, synced, failed, reconciled, rescheduled, activities_fetched, activities_matched,
    )
    return SyncAllResponse(
        synced=synced,
        failed=failed,
        reconciled=reconciled,
        rescheduled=rescheduled,
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
