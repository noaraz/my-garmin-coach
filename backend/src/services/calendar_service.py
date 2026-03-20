from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, timezone

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile, ScheduledWorkout, WorkoutTemplate
from src.repositories.calendar import scheduled_workout_repository
from src.repositories.zones import hr_zone_repository, pace_zone_repository
from src.repositories.workouts import workout_template_repository


# Maps the builder's step type to the formatter's step_type key.
# The builder uses "interval"; the formatter uses "active".
_STEP_TYPE_MAP: dict[str, str] = {
    "warmup": "warmup",
    "interval": "active",
    "active": "active",
    "recovery": "recovery",
    "rest": "rest",
    "cooldown": "cooldown",
    "repeat": "repeat",
}


def _builder_steps_to_formatter(
    raw_steps: list[dict],
    hr_zone_map: dict[int, tuple[float, float]],
    pace_zone_map: dict[int, tuple[float, float]],
) -> list[dict]:
    """Translate builder-format steps to formatter-ready dicts.

    The builder stores steps with keys like ``duration_sec`` and ``zone``.
    The Garmin formatter expects ``step_type``, ``end_condition``,
    ``end_condition_value``, ``target_type``, ``target_value_one/two``.

    Zone targets fall back to ``"open"`` when the user has no zones configured.
    """
    result: list[dict] = []
    for step in raw_steps:
        raw_type = step.get("type", "active")
        step_type = _STEP_TYPE_MAP.get(raw_type, "active")

        if step_type == "repeat":
            result.append({
                "step_type": "repeat",
                "repeat_count": step.get("repeat_count", 1),
                "steps": _builder_steps_to_formatter(
                    step.get("steps", []), hr_zone_map, pace_zone_map
                ),
            })
            continue

        # End condition — accept both builder keys (duration_sec / duration_distance_m)
        # and resolver keys. Plan-imported steps use duration_distance_m without
        # setting duration_type, so detect by key presence.
        duration_type = step.get("duration_type")
        has_distance = step.get("duration_distance_m") or step.get("duration_m")

        if duration_type == "distance" or (duration_type is None and has_distance):
            end_condition = "distance"
            end_condition_value = (
                step.get("duration_distance_m")
                or step.get("duration_m")
                or step.get("duration_value")
            )
        elif duration_type == "time" or step.get("duration_sec") or step.get("duration_value"):
            end_condition = "time"
            end_condition_value = step.get("duration_sec") or step.get("duration_value")
        else:
            end_condition = "lap_button"
            end_condition_value = None

        # Target — accept builder keys (zone + target_type) and plan-import keys
        # (zone only, no target_type). Infer target_type from whichever zone map
        # has the zone number (pace for running, HR for others).
        target_type = step.get("target_type")
        zone = step.get("zone") or step.get("target_zone")
        target_value_one = 0.0
        target_value_two = 0.0

        if target_type is None and zone:
            if zone in pace_zone_map:
                target_type = "pace_zone"
            elif zone in hr_zone_map:
                target_type = "hr_zone"

        if target_type == "hr_zone" and zone and zone in hr_zone_map:
            target_value_one, target_value_two = hr_zone_map[zone]
        elif target_type == "pace_zone" and zone and zone in pace_zone_map:
            target_value_one, target_value_two = pace_zone_map[zone]
        else:
            target_type = "open"

        result.append({
            "step_type": step_type,
            "end_condition": end_condition,
            "end_condition_value": end_condition_value,
            "target_type": target_type,
            "target_value_one": target_value_one,
            "target_value_two": target_value_two,
        })
    return result


def resolve_builder_steps(
    template: WorkoutTemplate,
    hr_zone_map: dict[int, tuple[float, float]],
    pace_zone_map: dict[int, tuple[float, float]],
) -> list[dict]:
    """Return formatter-ready step dicts for a template.  Empty list if no steps."""
    if not template.steps:
        return []
    raw_steps = json.loads(template.steps)
    if not raw_steps:
        return []
    return _builder_steps_to_formatter(raw_steps, hr_zone_map, pace_zone_map)


def _resolve_template_steps(
    template: WorkoutTemplate,
    hr_zone_map: dict[int, tuple[float, float]],
    pace_zone_map: dict[int, tuple[float, float]],
) -> str | None:
    """Translate a template's builder-format steps to formatter-ready JSON."""
    steps = resolve_builder_steps(template, hr_zone_map, pace_zone_map)
    return json.dumps(steps) if steps else None


class CalendarService:
    async def schedule(
        self,
        session: AsyncSession,
        template_id: int,
        workout_date: date,
        profile: AthleteProfile,
    ) -> ScheduledWorkout:
        """Schedule a workout template on a specific date.

        Resolves template steps using current zone maps.
        Raises ValueError if the template is not found.
        """
        template = await workout_template_repository.get(session, template_id)
        if template is None or template.user_id != profile.user_id:
            raise ValueError(f"WorkoutTemplate {template_id} not found")

        hr_zones = await hr_zone_repository.get_by_profile(session, profile.id)
        pace_zones = await pace_zone_repository.get_by_profile(session, profile.id)

        hr_zone_map: dict[int, tuple[float, float]] = {
            z.zone_number: (z.lower_bpm, z.upper_bpm) for z in hr_zones
        }
        pace_zone_map: dict[int, tuple[float, float]] = {
            z.zone_number: (z.lower_pace, z.upper_pace) for z in pace_zones
        }

        resolved_steps_json: str | None = None
        try:
            resolved_steps_json = _resolve_template_steps(template, hr_zone_map, pace_zone_map)
        except Exception:  # noqa: BLE001
            pass

        scheduled = ScheduledWorkout(
            user_id=profile.user_id,
            date=workout_date,
            workout_template_id=template_id,
            resolved_steps=resolved_steps_json,
            sync_status="pending",
        )
        return await scheduled_workout_repository.create(session, scheduled)

    async def get_range(
        self, session: AsyncSession, start: date, end: date, user_id: int
    ) -> list[ScheduledWorkout]:
        return await scheduled_workout_repository.get_range(session, start, end, user_id)

    async def reschedule(
        self, session: AsyncSession, scheduled_id: int, new_date: date | None, user_id: int, notes: str | None = None
    ) -> ScheduledWorkout:
        """Update a ScheduledWorkout date and/or notes. Raises ValueError if not found or not owned."""
        scheduled = await scheduled_workout_repository.get(session, scheduled_id)
        if scheduled is None or scheduled.user_id != user_id:
            raise ValueError(f"ScheduledWorkout {scheduled_id} not found")

        if new_date is not None:
            scheduled.date = new_date
        if notes is not None:
            scheduled.notes = notes
        scheduled.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)
        return scheduled

    async def unschedule(
        self,
        session: AsyncSession,
        scheduled_id: int,
        user_id: int,
        garmin_deleter: Callable[[str], None] | None = None,
    ) -> None:
        """Delete a ScheduledWorkout by id. Raises ValueError if not found or not owned.

        If *garmin_deleter* is provided and the workout has a garmin_workout_id,
        the corresponding Garmin workout is deleted first (best-effort — a
        failure does not prevent the local record from being removed).
        """
        scheduled = await scheduled_workout_repository.get(session, scheduled_id)
        if scheduled is None or scheduled.user_id != user_id:
            raise ValueError(f"ScheduledWorkout {scheduled_id} not found")

        if garmin_deleter is not None and scheduled.garmin_workout_id:
            try:
                garmin_deleter(scheduled.garmin_workout_id)
            except Exception:  # noqa: BLE001
                pass  # best-effort; local delete always proceeds

        await scheduled_workout_repository.delete(session, scheduled)


calendar_service = CalendarService()

# ---------------------------------------------------------------------------
# Module-level shims for backward compatibility with existing router imports
# ---------------------------------------------------------------------------


async def schedule(
    session: AsyncSession,
    template_id: int,
    workout_date: date,
    profile: AthleteProfile,
) -> ScheduledWorkout:
    return await calendar_service.schedule(session, template_id, workout_date, profile)


async def get_range(
    session: AsyncSession, start: date, end: date, user_id: int
) -> list[ScheduledWorkout]:
    return await calendar_service.get_range(session, start, end, user_id)


async def reschedule(
    session: AsyncSession, scheduled_id: int, new_date: date | None, user_id: int, notes: str | None = None
) -> ScheduledWorkout:
    return await calendar_service.reschedule(session, scheduled_id, new_date, user_id, notes=notes)


async def unschedule(
    session: AsyncSession,
    scheduled_id: int,
    user_id: int,
    garmin_deleter: Callable[[str], None] | None = None,
) -> None:
    return await calendar_service.unschedule(session, scheduled_id, user_id, garmin_deleter=garmin_deleter)
