from src.garmin.exercise_catalog import resolve


class TestResolve:
    def test_resolve_returns_garmin_pair_for_catalog_key(self):
        assert resolve("back_squat") == ("SQUAT", "BARBELL_BACK_SQUAT")

    def test_resolve_is_case_insensitive(self):
        assert resolve("BACK_SQUAT") == ("SQUAT", "BARBELL_BACK_SQUAT")
        assert resolve("Back_Squat") == ("SQUAT", "BARBELL_BACK_SQUAT")

    def test_resolve_strips_whitespace(self):
        assert resolve("  back_squat  ") == ("SQUAT", "BARBELL_BACK_SQUAT")

    def test_resolve_handles_alias(self):
        assert resolve("squat") == ("SQUAT", "BARBELL_BACK_SQUAT")
        assert resolve("RDL") == ("DEADLIFT", "ROMANIAN_DEADLIFT")
        assert resolve("plank") == ("PLANK", "FRONT_PLANK")

    def test_resolve_handles_alias_with_spaces(self):
        assert resolve("split squat") == ("LUNGE", "BULGARIAN_SPLIT_SQUAT")
        assert resolve("hip thrust") == ("HIP_RAISE", "BARBELL_HIP_THRUST")

    def test_resolve_returns_none_for_unknown(self):
        assert resolve("nordic curl") is None
        assert resolve("") is None
        assert resolve("   ") is None
