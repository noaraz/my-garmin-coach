from __future__ import annotations

import pytest

from src.garmin.exceptions import FormatterError
from src.garmin.formatter import format_step, format_workout


class TestWarmupTimeOpen:
    def test_warmup_time_open_returns_correct_json_structure(self) -> None:
        # Arrange
        step = {
            "step_type": "warmup",
            "end_condition": "time",
            "end_condition_value": 600,
            "target_type": "open",
        }

        # Act
        result = format_step(step, step_order=1)

        # Assert
        assert result["type"] == "ExecutableStepDTO"
        assert result["stepOrder"] == 1
        assert result["stepType"]["stepTypeId"] == 1
        assert result["stepType"]["stepTypeKey"] == "warmup"
        assert result["endCondition"]["conditionTypeKey"] == "time"
        assert result["endConditionValue"] == 600
        assert result["targetType"]["workoutTargetTypeKey"] == "no.target"
        assert result["targetValueOne"] == 0
        assert result["targetValueTwo"] == 0


class TestIntervalTimeHr:
    def test_interval_time_hr_returns_correct_targets(self) -> None:
        # Arrange
        step = {
            "step_type": "active",
            "end_condition": "time",
            "end_condition_value": 300,
            "target_type": "hr_range",
            "target_value_one": 155,
            "target_value_two": 170,
        }

        # Act
        result = format_step(step, step_order=2)

        # Assert
        assert result["type"] == "ExecutableStepDTO"
        assert result["stepOrder"] == 2
        assert result["stepType"]["stepTypeKey"] == "interval"
        assert result["endCondition"]["conditionTypeKey"] == "time"
        assert result["endConditionValue"] == 300
        assert result["targetType"]["workoutTargetTypeKey"] == "heart.rate.zone"
        assert result["targetValueOne"] == 155
        assert result["targetValueTwo"] == 170


class TestIntervalDistancePace:
    def test_interval_distance_pace_applies_speed_conversion(self) -> None:
        # Arrange: pace zone with pace values in s/km → should be stored as m/s
        step = {
            "step_type": "active",
            "end_condition": "distance",
            "end_condition_value": 1000,
            "target_type": "pace_range",
            "target_value_one": 300,  # 5:00/km in s/km → will be converted to m/s
            "target_value_two": 330,  # 5:30/km in s/km → will be converted to m/s
        }

        # Act
        result = format_step(step, step_order=3)

        # Assert
        assert result["endCondition"]["conditionTypeKey"] == "distance"
        assert result["endConditionValue"] == 1000
        assert result["targetType"]["workoutTargetTypeKey"] == "pace.zone"
        # Pace values must be converted to m/s: 1000/300 ≈ 3.333, 1000/330 ≈ 3.030
        assert abs(result["targetValueOne"] - 3.333) < 0.001
        assert abs(result["targetValueTwo"] - 3.030) < 0.001


class TestCooldownLapButton:
    def test_cooldown_lap_button_sets_condition_type_key(self) -> None:
        # Arrange
        step = {
            "step_type": "cooldown",
            "end_condition": "lap_button",
            "end_condition_value": None,
            "target_type": "open",
        }

        # Act
        result = format_step(step, step_order=4)

        # Assert
        assert result["stepType"]["stepTypeKey"] == "cool_down"
        assert result["endCondition"]["conditionTypeKey"] == "lap.button"


class TestRepeatGroup:
    def test_repeat_group_returns_repeat_group_dto_structure(self) -> None:
        # Arrange
        child_step = {
            "step_type": "active",
            "end_condition": "time",
            "end_condition_value": 60,
            "target_type": "open",
        }
        step = {
            "step_type": "repeat",
            "repeat_count": 4,
            "steps": [child_step],
        }

        # Act
        result = format_step(step, step_order=2)

        # Assert
        assert result["type"] == "RepeatGroupDTO"
        assert result["stepOrder"] == 2
        assert result["numberOfIterations"] == 4
        assert result["stepType"]["stepTypeKey"] == "repeat"
        assert len(result["workoutSteps"]) == 1
        assert result["workoutSteps"][0]["type"] == "ExecutableStepDTO"


class TestFullWorkout:
    def test_full_workout_returns_complete_garmin_json_structure(self) -> None:
        # Arrange
        steps = [
            {
                "step_type": "warmup",
                "end_condition": "time",
                "end_condition_value": 600,
                "target_type": "open",
            },
            {
                "step_type": "active",
                "end_condition": "time",
                "end_condition_value": 1800,
                "target_type": "open",
            },
            {
                "step_type": "cooldown",
                "end_condition": "time",
                "end_condition_value": 300,
                "target_type": "open",
            },
        ]

        # Act
        result = format_workout("Easy 10K", steps)

        # Assert
        assert result["workoutName"] == "Easy 10K"
        assert result["sportType"]["sportTypeId"] == 1
        assert result["sportType"]["sportTypeKey"] == "running"
        assert len(result["workoutSegments"]) == 1
        segment = result["workoutSegments"][0]
        assert segment["segmentOrder"] == 1
        assert segment["sportType"]["sportTypeKey"] == "running"
        assert len(segment["workoutSteps"]) == 3


class TestPreservesStepOrder:
    def test_preserves_step_order_5_steps_numbered_1_to_5(self) -> None:
        # Arrange
        steps = [
            {
                "step_type": "warmup",
                "end_condition": "time",
                "end_condition_value": 600,
                "target_type": "open",
            },
            {
                "step_type": "active",
                "end_condition": "time",
                "end_condition_value": 300,
                "target_type": "open",
            },
            {
                "step_type": "recovery",
                "end_condition": "time",
                "end_condition_value": 120,
                "target_type": "open",
            },
            {
                "step_type": "active",
                "end_condition": "time",
                "end_condition_value": 300,
                "target_type": "open",
            },
            {
                "step_type": "cooldown",
                "end_condition": "time",
                "end_condition_value": 300,
                "target_type": "open",
            },
        ]

        # Act
        result = format_workout("Interval Run", steps)

        # Assert
        workout_steps = result["workoutSegments"][0]["workoutSteps"]
        assert len(workout_steps) == 5
        for i, ws in enumerate(workout_steps, start=1):
            assert ws["stepOrder"] == i


class TestEmptyRaises:
    def test_empty_steps_raises_formatter_error(self) -> None:
        # Arrange
        steps: list = []

        # Act & Assert
        with pytest.raises(FormatterError):
            format_workout("Empty Workout", steps)
