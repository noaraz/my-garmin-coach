from __future__ import annotations

import json
from datetime import date, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile, ScheduledWorkout, WorkoutTemplate
from src.repositories.calendar import scheduled_workout_repository
from src.repositories.zones import hr_zone_repository, pace_zone_repository
from src.repositories.workouts import workout_template_repository


def _resolve_template_steps(
    template: WorkoutTemplate,
    hr_zone_map: dict[int, tuple[float, float]],
    pace_zone_map: dict[int, tuple[float, float]],
) -> str | None:
    """Resolve a template's steps JSON to a resolved steps JSON string."""
    if not template.steps:
        return None

    from src.workout_resolver.models import WorkoutStep
    from src.workout_resolver.resolver import resolve_workout

    raw_steps = json.loads(template.steps)
    steps = [WorkoutStep.model_validate(s) for s in raw_steps]
    resolved = resolve_workout(steps, hr_zones=hr_zone_map, pace_zones=pace_zone_map)
    return json.dumps([r.model_dump() for r in resolved])


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
        if template is None:
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
            date=workout_date,
            workout_template_id=template_id,
            resolved_steps=resolved_steps_json,
            sync_status="pending",
        )
        return await scheduled_workout_repository.create(session, scheduled)

    async def get_range(
        self, session: AsyncSession, start: date, end: date
    ) -> list[ScheduledWorkout]:
        return await scheduled_workout_repository.get_range(session, start, end)

    async def reschedule(
        self, session: AsyncSession, scheduled_id: int, new_date: date
    ) -> ScheduledWorkout:
        """Move a ScheduledWorkout to a new date. Raises ValueError if not found."""
        scheduled = await scheduled_workout_repository.get(session, scheduled_id)
        if scheduled is None:
            raise ValueError(f"ScheduledWorkout {scheduled_id} not found")

        scheduled.date = new_date
        scheduled.updated_at = datetime.utcnow()
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)
        return scheduled

    async def unschedule(self, session: AsyncSession, scheduled_id: int) -> None:
        """Delete a ScheduledWorkout by id. Raises ValueError if not found."""
        scheduled = await scheduled_workout_repository.get(session, scheduled_id)
        if scheduled is None:
            raise ValueError(f"ScheduledWorkout {scheduled_id} not found")
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
    session: AsyncSession, start: date, end: date
) -> list[ScheduledWorkout]:
    return await calendar_service.get_range(session, start, end)


async def reschedule(
    session: AsyncSession, scheduled_id: int, new_date: date
) -> ScheduledWorkout:
    return await calendar_service.reschedule(session, scheduled_id, new_date)


async def unschedule(session: AsyncSession, scheduled_id: int) -> None:
    return await calendar_service.unschedule(session, scheduled_id)
