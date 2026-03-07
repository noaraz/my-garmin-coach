from __future__ import annotations

from src.garmin.constants import STEP_TYPES
from src.garmin.exceptions import FormatterError


def pace_to_speed(pace_seconds_per_km: float) -> float:
    """Convert pace (seconds per km) to speed (meters per second).

    Garmin uses m/s internally for pace targets.
    Formula: speed = 1000.0 / pace_seconds
    """
    return 1000.0 / pace_seconds_per_km


def speed_to_pace(speed_mps: float) -> float:
    """Convert speed (meters per second) to pace (seconds per km).

    Formula: pace = 1000.0 / speed_mps
    """
    return 1000.0 / speed_mps


def step_type_to_id(step_type: str) -> int:
    """Return the Garmin stepTypeId for a given internal step type name.

    Raises:
        FormatterError: if step_type is not a recognised step type.
    """
    if step_type not in STEP_TYPES:
        raise FormatterError(
            f"Unknown step type: {step_type!r}. "
            f"Valid types: {list(STEP_TYPES.keys())}"
        )
    return int(STEP_TYPES[step_type]["stepTypeId"])
