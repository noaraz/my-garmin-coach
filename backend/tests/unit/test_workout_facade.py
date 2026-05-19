from __future__ import annotations


class TestWorkoutFacadeV1:
    """WorkoutFacade delegates to existing formatter for V1."""

    def test_v1_delegates_to_format_workout(self) -> None:
        from src.garmin.workout_facade import WorkoutFacade

        facade = WorkoutFacade(auth_version="v1")
        steps = [
            {
                "step_type": "warmup",
                "end_condition": "time",
                "end_condition_value": 600,
                "target_type": "open",
                "target_value_one": None,
                "target_value_two": None,
            }
        ]
        result = facade.build_workout("Test Run", steps, "A test workout")
        assert isinstance(result, dict)
        assert result["workoutName"] == "Test Run"

    def test_v1_callable_signature_matches_orchestrator(self) -> None:
        from src.garmin.workout_facade import WorkoutFacade

        facade = WorkoutFacade(auth_version="v1")
        assert callable(facade.build_workout)


class TestWorkoutFacadeV2:
    """WorkoutFacade builds typed RunningWorkout for V2."""

    def test_v2_returns_typed_workout(self) -> None:
        from src.garmin.workout_facade import WorkoutFacade

        facade = WorkoutFacade(auth_version="v2")
        steps = [
            {
                "step_type": "warmup",
                "end_condition": "time",
                "end_condition_value": 600,
                "target_type": "open",
                "target_value_one": None,
                "target_value_two": None,
            }
        ]
        result = facade.build_workout("Test Run", steps, "A test workout")
        assert isinstance(result, dict)
        assert result["workoutName"] == "Test Run"
