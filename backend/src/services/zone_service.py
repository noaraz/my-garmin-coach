from __future__ import annotations

import json
from datetime import date, datetime

from sqlmodel import Session, select

from src.db.models import AthleteProfile, HRZone, PaceZone, ScheduledWorkout, WorkoutTemplate
from src.zone_engine.hr_zones import HRZoneCalculator
from src.zone_engine.models import ZoneConfig
from src.zone_engine.pace_zones import PaceZoneCalculator


def get_hr_zones(session: Session, profile_id: int) -> list[HRZone]:
    """Return HR zones for the given profile, ordered by zone_number."""
    return list(
        session.exec(
            select(HRZone)
            .where(HRZone.profile_id == profile_id)
            .order_by(HRZone.zone_number)
        ).all()
    )


def get_pace_zones(session: Session, profile_id: int) -> list[PaceZone]:
    """Return pace zones for the given profile, ordered by zone_number."""
    return list(
        session.exec(
            select(PaceZone)
            .where(PaceZone.profile_id == profile_id)
            .order_by(PaceZone.zone_number)
        ).all()
    )


def recalculate_hr_zones(session: Session, profile: AthleteProfile) -> list[HRZone]:
    """Recalculate HR zones from the profile's LTHR using Coggan method.

    Deletes existing zones, inserts new ones, then triggers cascade re-resolve
    of all future unfinished ScheduledWorkouts.
    """
    if not profile.lthr:
        return []

    config = ZoneConfig(threshold=float(profile.lthr), method="coggan")
    zone_set = HRZoneCalculator(config).calculate()

    # Delete old zones
    old_zones = session.exec(
        select(HRZone).where(HRZone.profile_id == profile.id)
    ).all()
    for z in old_zones:
        session.delete(z)
    session.commit()

    # Insert new zones
    new_zones: list[HRZone] = []
    for z in zone_set.zones:
        hr_zone = HRZone(
            profile_id=profile.id,
            zone_number=z.zone_number,
            name=z.name,
            lower_bpm=z.lower,
            upper_bpm=z.upper,
            calculation_method="coggan",
            pct_lower=z.pct_lower,
            pct_upper=z.pct_upper,
        )
        session.add(hr_zone)
        new_zones.append(hr_zone)
    session.commit()

    # Cascade: re-resolve future ScheduledWorkouts
    _cascade_re_resolve(session, profile.id)

    return new_zones


def recalculate_pace_zones(
    session: Session, profile: AthleteProfile
) -> list[PaceZone]:
    """Recalculate pace zones from the profile's threshold_pace.

    Deletes existing zones, inserts new ones, then triggers cascade re-resolve.
    """
    if not profile.threshold_pace:
        return []

    config = ZoneConfig(threshold=float(profile.threshold_pace), method="pct_threshold")
    zone_set = PaceZoneCalculator(config).calculate()

    # Delete old zones
    old_zones = session.exec(
        select(PaceZone).where(PaceZone.profile_id == profile.id)
    ).all()
    for z in old_zones:
        session.delete(z)
    session.commit()

    # Insert new zones
    new_zones: list[PaceZone] = []
    for z in zone_set.zones:
        pace_zone = PaceZone(
            profile_id=profile.id,
            zone_number=z.zone_number,
            name=z.name,
            lower_pace=z.lower,
            upper_pace=z.upper,
            calculation_method="pct_threshold",
            pct_lower=z.pct_lower,
            pct_upper=z.pct_upper,
        )
        session.add(pace_zone)
        new_zones.append(pace_zone)
    session.commit()

    # Cascade: re-resolve future ScheduledWorkouts
    _cascade_re_resolve(session, profile.id)

    return new_zones


def set_hr_zones(
    session: Session, profile_id: int, zones_data: list[dict]
) -> list[HRZone]:
    """Replace all HR zones for a profile with custom values."""
    old_zones = session.exec(
        select(HRZone).where(HRZone.profile_id == profile_id)
    ).all()
    for z in old_zones:
        session.delete(z)
    session.commit()

    new_zones: list[HRZone] = []
    for data in zones_data:
        hr_zone = HRZone(
            profile_id=profile_id,
            zone_number=data["zone_number"],
            name=data["name"],
            lower_bpm=data["lower_bpm"],
            upper_bpm=data["upper_bpm"],
            calculation_method=data.get("calculation_method", "custom"),
            pct_lower=data["pct_lower"],
            pct_upper=data["pct_upper"],
        )
        session.add(hr_zone)
        new_zones.append(hr_zone)
    session.commit()

    _cascade_re_resolve(session, profile_id)

    return new_zones


def _cascade_re_resolve(session: Session, profile_id: int) -> None:
    """Re-resolve all future unfinished ScheduledWorkouts after zone change.

    Fetches all future (date >= today) non-completed scheduled workouts,
    re-resolves their steps using current zones, updates resolved_steps JSON,
    and marks sync_status as 'modified'.
    All done in the current session/transaction.
    """
    from src.workout_resolver.resolver import resolve_workout
    from src.workout_resolver.models import WorkoutStep

    today = date.today()

    # Gather current zone maps
    hr_zones_db = session.exec(
        select(HRZone).where(HRZone.profile_id == profile_id)
    ).all()
    pace_zones_db = session.exec(
        select(PaceZone).where(PaceZone.profile_id == profile_id)
    ).all()

    hr_zone_map: dict[int, tuple[float, float]] = {
        z.zone_number: (z.lower_bpm, z.upper_bpm) for z in hr_zones_db
    }
    pace_zone_map: dict[int, tuple[float, float]] = {
        z.zone_number: (z.lower_pace, z.upper_pace) for z in pace_zones_db
    }

    # Fetch future uncompleted scheduled workouts
    future_workouts = session.exec(
        select(ScheduledWorkout).where(
            ScheduledWorkout.date >= today,
            ScheduledWorkout.completed == False,  # noqa: E712
        )
    ).all()

    for sw in future_workouts:
        if sw.workout_template_id is None:
            continue
        template = session.get(WorkoutTemplate, sw.workout_template_id)
        if template is None or not template.steps:
            continue

        raw_steps = json.loads(template.steps)
        try:
            steps = [WorkoutStep.model_validate(s) for s in raw_steps]
            resolved = resolve_workout(
                steps, hr_zones=hr_zone_map, pace_zones=pace_zone_map
            )
            sw.resolved_steps = json.dumps(
                [r.model_dump() for r in resolved]
            )
            sw.sync_status = "modified"
            sw.updated_at = datetime.utcnow()
            session.add(sw)
        except Exception:
            # If resolve fails (e.g. zone not found), skip gracefully
            pass

    session.commit()
