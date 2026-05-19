from __future__ import annotations

from typing import Any

from src.garmin.constants import END_CONDITIONS, SPORT_TYPE, STEP_TYPES, TARGET_TYPES
from src.garmin.converters import pace_to_speed
from src.garmin.exceptions import FormatterError

# Target types whose values (s/km) must be converted to m/s for Garmin.
_PACE_TARGET_TYPES = {"pace_zone", "pace_range"}


def format_step(step: dict[str, Any], step_order: int) -> dict[str, Any]:
    """Format a single workout step into Garmin's JSON representation.

    For repeat groups (step_type == "repeat") this returns a RepeatGroupDTO.
    For all other step types this returns an ExecutableStepDTO.

    Args:
        step: Internal step dict with keys:
            - step_type: str — one of warmup/active/recovery/rest/cooldown/repeat
            - end_condition: str — one of time/distance/lap_button (non-repeat)
            - end_condition_value: int | None
            - target_type: str — one of open/hr_zone/hr_range/pace_zone/pace_range
            - target_value_one: float | None
            - target_value_two: float | None
            For repeat steps additionally:
            - repeat_count: int
            - steps: list[dict] — child steps
        step_order: 1-based position of this step in the parent list.

    Returns:
        A dict matching the Garmin WorkoutStepDTO JSON schema.

    Raises:
        FormatterError: if the step_type is unknown or required keys are missing.
    """
    step_type_key = step.get("step_type", "")

    if step_type_key not in STEP_TYPES:
        raise FormatterError(
            f"Unknown step type: {step_type_key!r}. "
            f"Valid types: {list(STEP_TYPES.keys())}"
        )

    step_type_info = STEP_TYPES[step_type_key]

    if step_type_key == "repeat":
        return _format_repeat_group(step, step_order, step_type_info)

    return _format_executable_step(step, step_order, step_type_info)


def _format_executable_step(
    step: dict[str, Any],
    step_order: int,
    step_type_info: dict[str, int | str],
) -> dict[str, Any]:
    """Format an ExecutableStepDTO (non-repeat step)."""
    end_condition_key = step.get("end_condition", "")
    if end_condition_key not in END_CONDITIONS:
        raise FormatterError(
            f"Unknown end condition: {end_condition_key!r}. "
            f"Valid conditions: {list(END_CONDITIONS.keys())}"
        )
    end_condition_info = END_CONDITIONS[end_condition_key]

    target_type_key = step.get("target_type", "open")
    if target_type_key not in TARGET_TYPES:
        raise FormatterError(
            f"Unknown target type: {target_type_key!r}. "
            f"Valid types: {list(TARGET_TYPES.keys())}"
        )
    target_type_info = TARGET_TYPES[target_type_key]

    raw_value_one = step.get("target_value_one", 0) or 0
    raw_value_two = step.get("target_value_two", 0) or 0

    if target_type_key in _PACE_TARGET_TYPES and raw_value_one:
        # Garmin expects speed in m/s; our input is pace in s/km.
        target_value_one = pace_to_speed(raw_value_one)
        target_value_two = pace_to_speed(raw_value_two) if raw_value_two else 0.0
    else:
        target_value_one = float(raw_value_one)
        target_value_two = float(raw_value_two)

    return {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": dict(step_type_info),
        "endCondition": dict(end_condition_info),
        "endConditionValue": step.get("end_condition_value"),
        "targetType": dict(target_type_info),
        "targetValueOne": target_value_one,
        "targetValueTwo": target_value_two,
    }


def _format_repeat_group(
    step: dict[str, Any],
    step_order: int,
    step_type_info: dict[str, int | str],
) -> dict[str, Any]:
    """Format a RepeatGroupDTO containing child steps."""
    repeat_count = step.get("repeat_count", 1)
    child_steps = step.get("steps", [])

    formatted_children = [
        format_step(child, child_order)
        for child_order, child in enumerate(child_steps, start=1)
    ]

    return {
        "type": "RepeatGroupDTO",
        "stepOrder": step_order,
        "stepType": dict(step_type_info),
        "numberOfIterations": repeat_count,
        "workoutSteps": formatted_children,
    }


def format_workout(
    workout_name: str,
    steps: list[dict[str, Any]],
    workout_description: str = "",
) -> dict[str, Any]:
    """Format a complete workout into Garmin Connect's JSON structure.

    Args:
        workout_name:        Display name of the workout.
        steps:               Ordered list of internal step dicts (see format_step).
        workout_description: Optional notes/description shown in Garmin Connect.

    Returns:
        A dict matching the Garmin Workout JSON schema ready for the API.

    Raises:
        FormatterError: if steps is empty.
    """
    if not steps:
        raise FormatterError("Workout must have at least one step.")

    formatted_steps = [
        format_step(step, step_order)
        for step_order, step in enumerate(steps, start=1)
    ]

    return {
        "workoutName": workout_name,
        "description": workout_description,
        "sportType": dict(SPORT_TYPE),
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": dict(SPORT_TYPE),
                "workoutSteps": formatted_steps,
            }
        ],
    }
