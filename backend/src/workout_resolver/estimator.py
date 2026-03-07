from __future__ import annotations

from src.workout_resolver.models import WorkoutStep


def _step_duration(step: WorkoutStep) -> float | None:
    """Return the duration in seconds for a single step.

    Returns None if the step uses lap_button (indeterminate duration).
    For repeat steps, returns count * sum of children durations, or None if any
    child is indeterminate.
    """
    if step.type == "repeat":
        count = step.repeat_count or 1
        total: float = 0.0
        for child in step.steps:
            child_dur = _step_duration(child)
            if child_dur is None:
                return None
            total += child_dur
        return count * total

    if step.duration_type == "lap_button":
        return None

    if step.duration_type == "time" and step.duration_value is not None:
        return step.duration_value

    # distance steps don't contribute to duration estimation
    return None


def _step_distance(step: WorkoutStep) -> float | None:
    """Return the distance in meters for a single step, or None if unknown."""
    if step.type == "repeat":
        count = step.repeat_count or 1
        total: float = 0.0
        for child in step.steps:
            child_dist = _step_distance(child)
            if child_dist is None:
                return None
            total += child_dist
        return count * total

    if step.duration_type == "distance" and step.duration_value is not None:
        return step.duration_value

    return None


def estimate_duration(steps: list[WorkoutStep]) -> float | None:
    """Estimate total workout duration in seconds.

    Returns None if any step has an indeterminate duration (lap_button).
    """
    total: float = 0.0
    for step in steps:
        dur = _step_duration(step)
        if dur is None:
            return None
        total += dur
    return total


def estimate_distance(steps: list[WorkoutStep]) -> float | None:
    """Estimate total workout distance in meters.

    Returns None if any step has indeterminate distance.
    """
    total: float = 0.0
    for step in steps:
        dist = _step_distance(step)
        if dist is None:
            return None
        total += dist
    return total
