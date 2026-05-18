from src.services.plan_step_parser import parse_strength_steps


class TestUniformSets:
    def test_single_exercise_kg(self):
        result = parse_strength_steps("Squat 3x5@80kg")
        assert result.errors == []
        assert len(result.steps) == 1
        step = result.steps[0]
        assert step["kind"] == "strength_exercise"
        assert step["exercise_key"] == "back_squat"
        assert step["garmin_category"] == "SQUAT"
        assert step["garmin_name"] == "BARBELL_BACK_SQUAT"
        assert step["sets"] == [
            {"reps": 5, "load": {"type": "kg", "value": 80}},
            {"reps": 5, "load": {"type": "kg", "value": 80}},
            {"reps": 5, "load": {"type": "kg", "value": 80}},
        ]

    def test_rpe_load(self):
        result = parse_strength_steps("RDL 3x8@RPE8")
        assert result.errors == []
        assert result.steps[0]["sets"][0]["load"] == {"type": "rpe", "value": 8}

    def test_bodyweight_load(self):
        result = parse_strength_steps("Walking Lunge 3x10@bw")
        assert result.errors == []
        assert result.steps[0]["sets"][0]["load"] == {"type": "bodyweight"}

    def test_duration_no_load(self):
        result = parse_strength_steps("Plank 3x45s")
        assert result.errors == []
        assert result.steps[0]["sets"] == [
            {"duration_sec": 45},
            {"duration_sec": 45},
            {"duration_sec": 45},
        ]


class TestMultiExercise:
    def test_semicolon_separated(self):
        result = parse_strength_steps("Squat 3x5@80kg; RDL 3x8@RPE8; Plank 3x45s")
        assert result.errors == []
        assert len(result.steps) == 3
        assert result.steps[0]["exercise_key"] == "back_squat"
        assert result.steps[1]["exercise_key"] == "romanian_deadlift"
        assert result.steps[2]["exercise_key"] == "front_plank"


class TestPerSetVariance:
    def test_kg_variance(self):
        result = parse_strength_steps("Squat 3x5@60kg,70kg,80kg")
        assert result.errors == []
        assert [s["load"] for s in result.steps[0]["sets"]] == [
            {"type": "kg", "value": 60},
            {"type": "kg", "value": 70},
            {"type": "kg", "value": 80},
        ]

    def test_mixed_variance(self):
        result = parse_strength_steps("Front Squat 3x5@60kg,RPE7,RPE8")
        assert result.errors == []
        loads = [s["load"] for s in result.steps[0]["sets"]]
        assert loads == [
            {"type": "kg", "value": 60},
            {"type": "rpe", "value": 7},
            {"type": "rpe", "value": 8},
        ]


class TestErrors:
    def test_unknown_exercise(self):
        result = parse_strength_steps("Nordic Curl 3x6@bw")
        assert result.steps == []
        assert any(e["code"] == "unknown_exercise" for e in result.errors)
        assert any("Nordic Curl" in e["message"] for e in result.errors)

    def test_unparseable_load(self):
        result = parse_strength_steps("Squat 3x5@???")
        assert any(e["code"] == "unparseable_load" for e in result.errors)

    def test_load_required(self):
        result = parse_strength_steps("Squat 3x5")
        assert any(e["code"] == "load_required" for e in result.errors)

    def test_load_count_mismatch(self):
        result = parse_strength_steps("Squat 3x5@60kg,70kg")  # 2 loads for 3 sets
        assert any(e["code"] == "load_count_mismatch" for e in result.errors)

    def test_duration_with_load(self):
        result = parse_strength_steps("Plank 3x45s@bw")
        assert any(e["code"] == "duration_with_load" for e in result.errors)
