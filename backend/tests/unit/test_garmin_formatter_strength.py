import json
import pytest
from src.garmin.formatter import format_strength_workout


@pytest.fixture
def template():
    """Single-exercise template: 3x5 back squat @ 80kg."""
    class T:
        name = "Lower body strength"
        sport = "strength"
        steps = [
            {
                "kind": "strength_exercise",
                "exercise_key": "back_squat",
                "garmin_category": "SQUAT",
                "garmin_name": "BARBELL_BACK_SQUAT",
                "sets": [
                    {"reps": 5, "load": {"type": "kg", "value": 80}},
                    {"reps": 5, "load": {"type": "kg", "value": 80}},
                    {"reps": 5, "load": {"type": "kg", "value": 80}},
                ],
                "note": None,
            }
        ]
    return T()


class TestFormatStrengthWorkout:
    def test_top_level_sport_type(self, template):
        out = format_strength_workout(template)
        assert out["sportType"]["sportTypeKey"] == "strength_training"
        assert out["workoutName"] == "Lower body strength"

    def test_segment_sport_type(self, template):
        out = format_strength_workout(template)
        seg = out["workoutSegments"][0]
        assert seg["sportType"]["sportTypeKey"] == "strength_training"

    def test_uniform_sets_use_repetition_group(self, template):
        out = format_strength_workout(template)
        steps = out["workoutSegments"][0]["workoutSteps"]
        assert steps[0]["type"] == "RepeatGroupDTO"
        assert steps[0]["numberOfIterations"] == 3
        inner = steps[0]["workoutSteps"][0]
        assert inner["category"] == "SQUAT"
        assert inner["exerciseName"] == "BARBELL_BACK_SQUAT"
        assert inner["weightValue"] == 80
        assert inner["weightUnit"]["unitKey"] == "kilogram"
        assert inner["endCondition"]["conditionTypeKey"] == "reps"
        assert inner["endConditionValue"] == 5

    def test_per_set_variance_emits_individual_steps(self):
        class T:
            name = "Front Squat Day"
            sport = "strength"
            steps = [{
                "kind": "strength_exercise",
                "exercise_key": "front_squat",
                "garmin_category": "SQUAT",
                "garmin_name": "BARBELL_FRONT_SQUAT",
                "sets": [
                    {"reps": 5, "load": {"type": "kg", "value": 60}},
                    {"reps": 5, "load": {"type": "kg", "value": 70}},
                    {"reps": 5, "load": {"type": "kg", "value": 80}},
                ],
                "note": None,
            }]
        out = format_strength_workout(T())
        steps = out["workoutSegments"][0]["workoutSteps"]
        non_rest = [s for s in steps if s.get("stepType", {}).get("stepTypeKey") != "rest"]
        assert len(non_rest) == 3
        assert [s["weightValue"] for s in non_rest] == [60, 70, 80]

    def test_rpe_set_omits_weight(self):
        class T:
            name = "RPE day"
            sport = "strength"
            steps = [{
                "kind": "strength_exercise", "exercise_key": "romanian_deadlift",
                "garmin_category": "DEADLIFT", "garmin_name": "ROMANIAN_DEADLIFT",
                "sets": [{"reps": 8, "load": {"type": "rpe", "value": 8}}],
                "note": None,
            }]
        out = format_strength_workout(T())
        inner = out["workoutSegments"][0]["workoutSteps"][0]
        assert "weightValue" not in inner or inner.get("weightValue") is None
        assert "RPE 8" in (inner.get("description") or "")

    def test_bodyweight_set_omits_weight(self):
        class T:
            name = "Lunge day"
            sport = "strength"
            steps = [{
                "kind": "strength_exercise", "exercise_key": "walking_lunge",
                "garmin_category": "LUNGE", "garmin_name": "WALKING_LUNGE",
                "sets": [{"reps": 10, "load": {"type": "bodyweight"}}],
                "note": None,
            }]
        out = format_strength_workout(T())
        inner = out["workoutSegments"][0]["workoutSteps"][0]
        assert inner.get("weightValue") in (None, 0)

    def test_duration_set_uses_time_condition(self):
        class T:
            name = "Plank day"
            sport = "strength"
            steps = [{
                "kind": "strength_exercise", "exercise_key": "front_plank",
                "garmin_category": "PLANK", "garmin_name": "FRONT_PLANK",
                "sets": [{"duration_sec": 45}, {"duration_sec": 45}, {"duration_sec": 45}],
                "note": None,
            }]
        out = format_strength_workout(T())
        inner = out["workoutSegments"][0]["workoutSteps"][0]["workoutSteps"][0]
        assert inner["endCondition"]["conditionTypeKey"] == "time"
        assert inner["endConditionValue"] == 45

    def test_steps_as_json_string_is_parsed(self, template):
        """ORM stores steps as a JSON string — formatter must parse it."""
        class T:
            name = template.name
            sport = template.sport
            steps = json.dumps(template.steps)  # simulate DB ORM column value

        out = format_strength_workout(T())
        assert out["sportType"]["sportTypeKey"] == "strength_training"
        assert len(out["workoutSegments"][0]["workoutSteps"]) > 0
