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


class TestWorkoutFacadeStrength:
    """WorkoutFacade handles strength workouts via format_strength."""

    def test_format_strength_returns_strength_training_sport_type(self) -> None:
        from src.garmin.workout_facade import WorkoutFacade

        class MockTemplate:
            name = "Test Strength"
            sport = "strength"
            steps = [
                {
                    "kind": "strength_exercise",
                    "exercise_key": "back_squat",
                    "garmin_category": "SQUAT",
                    "garmin_name": "BARBELL_BACK_SQUAT",
                    "sets": [{"reps": 5, "load": {"type": "kg", "value": 80}}],
                    "note": None,
                }
            ]

        facade = WorkoutFacade(auth_version="v2")
        out = facade.format_strength(MockTemplate())
        assert out["sportType"]["sportTypeKey"] == "strength_training"

    def test_v1_and_v2_produce_identical_strength_json(self) -> None:
        from src.garmin.workout_facade import WorkoutFacade

        class MockTemplate:
            name = "Test Strength"
            sport = "strength"
            steps = [
                {
                    "kind": "strength_exercise",
                    "exercise_key": "back_squat",
                    "garmin_category": "SQUAT",
                    "garmin_name": "BARBELL_BACK_SQUAT",
                    "sets": [{"reps": 5, "load": {"type": "kg", "value": 80}}],
                    "note": None,
                }
            ]

        v1 = WorkoutFacade(auth_version="v1").format_strength(MockTemplate())
        v2 = WorkoutFacade(auth_version="v2").format_strength(MockTemplate())
        assert v1 == v2
