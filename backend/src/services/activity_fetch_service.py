"""Service for fetching Garmin activities and matching them to scheduled workouts."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import GarminActivity, ScheduledWorkout
from src.garmin.converters import speed_to_pace

logger = logging.getLogger(__name__)

_RUNNING_TYPES = ("running", "trail_running", "treadmill_running", "track_running")


@dataclass
class FetchResult:
    fetched: int = 0
    stored: int = 0
    updated: int = 0


class ActivityFetchService:
    def _update_activity(
        self, existing: GarminActivity, parsed: GarminActivity
    ) -> bool:
        """Update mutable fields on existing. Returns True if any field changed.

        NOTE: 'date' is intentionally NOT updated — it drives match_activities
        pairing and changing it would silently detach paired ScheduledWorkouts.
        """
        changed = False
        for field in (
            "distance_m", "duration_sec", "avg_pace_sec_per_km",
            "avg_hr", "max_hr", "calories", "name", "start_time",
        ):
            old_val = getattr(existing, field)
            new_val = getattr(parsed, field)
            if old_val != new_val:
                setattr(existing, field, new_val)
                changed = True
        if changed:
            existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return changed

    def _parse_activity(
        self, raw: dict[str, Any], user_id: int
    ) -> GarminActivity | None:
        """Parse a raw Garmin activity dict into a GarminActivity model.

        Returns None if the activity is not a running type.
        """
        type_key = raw.get("activityType", {}).get("typeKey", "")
        if type_key not in _RUNNING_TYPES:
            return None

        avg_speed = raw.get("averageSpeed", 0.0) or 0.0
        avg_pace = speed_to_pace(avg_speed) if avg_speed > 0 else None

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        start_time_local = raw.get("startTimeLocal", "")
        try:
            local_dt = datetime.fromisoformat(start_time_local)
            activity_date = local_dt.date()
            activity_start = local_dt.replace(tzinfo=None)
        except (ValueError, TypeError):
            activity_date = datetime.now(timezone.utc).date()
            activity_start = now

        return GarminActivity(
            user_id=user_id,
            garmin_activity_id=str(raw["activityId"]),
            activity_type=type_key,
            name=raw.get("activityName", "Activity"),
            start_time=activity_start,
            date=activity_date,
            duration_sec=float(raw.get("duration", 0)),
            distance_m=float(raw.get("distance", 0)),
            avg_hr=raw.get("averageHR"),
            max_hr=raw.get("maxHR"),
            avg_pace_sec_per_km=avg_pace,
            calories=raw.get("calories"),
        )

    def _pick_best_match(
        self, candidates: list[GarminActivity]
    ) -> GarminActivity | None:
        """Pick the longest-duration activity from candidates."""
        if not candidates:
            return None
        return max(candidates, key=lambda a: a.duration_sec)

    async def fetch_and_store(
        self,
        garmin_adapter: Any,
        session: AsyncSession,
        user_id: int,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """Fetch activities from Garmin; upsert existing ones, insert new ones."""
        raw_activities = garmin_adapter.get_activities_by_date(start_date, end_date)
        result = FetchResult(fetched=len(raw_activities))

        # Bounded query: only load activities in the fetch window (not all-time)
        existing_rows = (
            await session.exec(
                select(GarminActivity).where(
                    GarminActivity.user_id == user_id,
                    GarminActivity.date >= date.fromisoformat(start_date),
                    GarminActivity.date <= date.fromisoformat(end_date),
                )
            )
        ).all()
        existing_map: dict[str, GarminActivity] = {
            a.garmin_activity_id: a for a in existing_rows
        }

        for raw in raw_activities:
            parsed = self._parse_activity(raw, user_id)
            if parsed is None:
                continue

            existing = existing_map.get(parsed.garmin_activity_id)
            if existing is not None:
                if self._update_activity(existing, parsed):
                    session.add(existing)
                    result.updated += 1
            else:
                session.add(parsed)
                existing_map[parsed.garmin_activity_id] = parsed
                result.stored += 1

        if result.stored > 0 or result.updated > 0:
            await session.flush()

        return result

    async def match_activities(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> int:
        """Auto-pair unmatched activities with scheduled workouts. Returns match count."""
        unmatched_workouts = (
            await session.exec(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.user_id == user_id,
                    ScheduledWorkout.date >= start_date,
                    ScheduledWorkout.date <= end_date,
                    ScheduledWorkout.matched_activity_id.is_(None),  # type: ignore[union-attr]
                )
            )
        ).all()

        if not unmatched_workouts:
            return 0

        paired_ids_result = await session.exec(
            select(ScheduledWorkout.matched_activity_id).where(
                ScheduledWorkout.matched_activity_id.is_not(None),  # type: ignore[union-attr]
                ScheduledWorkout.user_id == user_id,
            )
        )
        paired_ids = set(paired_ids_result.all())

        all_activities = (
            await session.exec(
                select(GarminActivity).where(
                    GarminActivity.user_id == user_id,
                    GarminActivity.date >= start_date,
                    GarminActivity.date <= end_date,
                )
            )
        ).all()

        activities_by_date: dict[date, list[GarminActivity]] = {}
        for a in all_activities:
            if a.id in paired_ids:
                continue
            activities_by_date.setdefault(a.date, []).append(a)

        match_count = 0
        for workout in unmatched_workouts:
            candidates = activities_by_date.get(workout.date, [])
            best = self._pick_best_match(candidates)
            if best is not None:
                workout.matched_activity_id = best.id
                workout.completed = True
                workout.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                session.add(workout)
                candidates.remove(best)
                paired_ids.add(best.id)
                match_count += 1

        return match_count


activity_fetch_service = ActivityFetchService()
