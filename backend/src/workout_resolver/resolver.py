from __future__ import annotations

from src.workout_resolver.exceptions import WorkoutResolveError
from src.workout_resolver.models import ResolvedStep, WorkoutStep

# Zone mapping: zone_number -> (low, high)
ZoneMap = dict[int, tuple[float, float]]


def resolve_step(
    step: WorkoutStep,
    *,
    hr_zones: ZoneMap,
    pace_zones: ZoneMap,
) -> ResolvedStep:
    """Resolve a single WorkoutStep into a ResolvedStep with absolute targets.

    - hr_zone / pace_zone: look up zone boundaries and populate target_low/high.
    - open / hr_range / pace_range: pass through unchanged.
    - repeat: recursively resolve all child steps.
    - Never mutates the original step.

    Raises:
        WorkoutResolveError: when a referenced zone number is not in the zone map.
    """
    target_low = step.target_low
    target_high = step.target_high

    if step.target_type == "hr_zone":
        zone_num = step.target_zone
        if zone_num not in hr_zones:
            available = sorted(hr_zones.keys())
            raise WorkoutResolveError(
                f"HR zone {zone_num} not found. Available zones: {available}"
            )
        target_low, target_high = hr_zones[zone_num]

    elif step.target_type == "pace_zone":
        zone_num = step.target_zone
        if zone_num not in pace_zones:
            available = sorted(pace_zones.keys())
            raise WorkoutResolveError(
                f"Pace zone {zone_num} not found. Available zones: {available}"
            )
        target_low, target_high = pace_zones[zone_num]

    # Recursively resolve children for repeat steps
    resolved_children: list[ResolvedStep] = []
    if step.type == "repeat" and step.steps:
        resolved_children = [
            resolve_step(child, hr_zones=hr_zones, pace_zones=pace_zones)
            for child in step.steps
        ]

    return ResolvedStep(
        order=step.order,
        type=step.type,
        duration_type=step.duration_type,
        duration_value=step.duration_value,
        duration_unit=step.duration_unit,
        target_type=step.target_type,
        target_zone=step.target_zone,
        target_low=target_low,
        target_high=target_high,
        notes=step.notes,
        repeat_count=step.repeat_count,
        steps=resolved_children,
    )


def resolve_workout(
    steps: list[WorkoutStep],
    *,
    hr_zones: ZoneMap,
    pace_zones: ZoneMap,
) -> list[ResolvedStep]:
    """Resolve all steps in a workout.

    Returns a new list of ResolvedStep objects. Original steps are not mutated.

    Raises:
        WorkoutResolveError: when any step references a zone that doesn't exist.
    """
    return [
        resolve_step(step, hr_zones=hr_zones, pace_zones=pace_zones)
        for step in steps
    ]
