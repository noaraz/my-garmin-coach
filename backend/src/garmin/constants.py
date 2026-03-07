from __future__ import annotations

# Maps our internal step type names to Garmin's stepTypeId and stepTypeKey.
# Note: our "active" maps to Garmin's "interval" (id=3).
STEP_TYPES: dict[str, dict[str, int | str]] = {
    "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup"},
    "active": {"stepTypeId": 3, "stepTypeKey": "interval"},
    "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery"},
    "rest": {"stepTypeId": 5, "stepTypeKey": "rest"},
    "cooldown": {"stepTypeId": 2, "stepTypeKey": "cool_down"},
    "repeat": {"stepTypeId": 6, "stepTypeKey": "repeat"},
}

END_CONDITIONS: dict[str, dict[str, int | str]] = {
    "time": {"conditionTypeId": 2, "conditionTypeKey": "time"},
    "distance": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
    "lap_button": {"conditionTypeId": 1, "conditionTypeKey": "lap.button"},
}

TARGET_TYPES: dict[str, dict[str, int | str]] = {
    "open": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
    "hr_zone": {"workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone"},
    "hr_range": {"workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone"},
    "pace_zone": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
    "pace_range": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
}

SPORT_TYPE: dict[str, int | str] = {"sportTypeId": 1, "sportTypeKey": "running"}
