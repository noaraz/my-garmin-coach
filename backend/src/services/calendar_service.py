from __future__ import annotations

import json
from datetime import date, datetime

from sqlmodel import Session, select

from src.db.models import AthleteProfile, HRZone, PaceZone, ScheduledWorkout, WorkoutTemplate


def _build_zone_maps(
    session: Session, profile_id: int
) -> tuple[dict[int, tuple[float, float]], dict[int, tuple[float, float]]]:
    """Build HR and pace zone maps from database for the given profile."""
    hr_zones = session.exec(
        select(HRZone).where(HRZone.profile_id == profile_id)
    ).all()
    pace_zones = session.exec(
        select(PaceZone).where(PaceZone.profile_id == profile_id)
    ).all()

    hr_zone_map: dict[int, tuple[float, float]] = {
        z.zone_number: (z.lower_bpm, z.upper_bpm) for z in hr_zones
    }
    pace_zone_map: dict[int, tuple[float, float]] = {
        z.zone_number: (z.lower_pace, z.upper_pace) for z in pace_zones
    }
    return hr_zone_map, pace_zone_map


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


def schedule(
    session: Session,
    template_id: int,
    workout_date: date,
    profile: AthleteProfile,
) -> ScheduledWorkout:
    """Schedule a workout template on a specific date.

    Resolves the template steps using current zone maps and persists the
    resolved_steps JSON on the ScheduledWorkout.

    Raises ValueError if the template is not found.
    """
    template = session.get(WorkoutTemplate, template_id)
    if template is None:
        raise ValueError(f"WorkoutTemplate {template_id} not found")

    hr_zone_map, pace_zone_map = _build_zone_maps(session, profile.id)

    resolved_steps_json: str | None = None
    try:
        resolved_steps_json = _resolve_template_steps(
            template, hr_zone_map, pace_zone_map
        )
    except Exception:
        pass  # If resolution fails, store None

    scheduled = ScheduledWorkout(
        date=workout_date,
        workout_template_id=template_id,
        resolved_steps=resolved_steps_json,
        sync_status="pending",
    )
    session.add(scheduled)
    session.commit()
    session.refresh(scheduled)
    return scheduled


def get_range(
    session: Session, start: date, end: date
) -> list[ScheduledWorkout]:
    """Return ScheduledWorkouts within the given date range (inclusive)."""
    return list(
        session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.date >= start,
                ScheduledWorkout.date <= end,
            )
        ).all()
    )


def reschedule(
    session: Session, scheduled_id: int, new_date: date
) -> ScheduledWorkout:
    """Move a ScheduledWorkout to a new date.

    Raises ValueError if the scheduled workout is not found.
    """
    scheduled = session.get(ScheduledWorkout, scheduled_id)
    if scheduled is None:
        raise ValueError(f"ScheduledWorkout {scheduled_id} not found")

    scheduled.date = new_date
    scheduled.updated_at = datetime.utcnow()
    session.add(scheduled)
    session.commit()
    session.refresh(scheduled)
    return scheduled


def unschedule(session: Session, scheduled_id: int) -> None:
    """Delete a ScheduledWorkout by id.

    Raises ValueError if the scheduled workout is not found.
    """
    scheduled = session.get(ScheduledWorkout, scheduled_id)
    if scheduled is None:
        raise ValueError(f"ScheduledWorkout {scheduled_id} not found")
    session.delete(scheduled)
    session.commit()
