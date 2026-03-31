"""Tests for Garmin workout deduplication logic."""
from __future__ import annotations

from src.garmin.dedup import find_matching_garmin_workout, find_missing_from_garmin, find_orphaned_garmin_workouts


class TestFindMatchingGarminWorkout:
    def test_returns_id_when_name_matches(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-123", "workoutName": "Easy Run"},
            {"workoutId": "gw-456", "workoutName": "Tempo Run"},
        ]
        result = find_matching_garmin_workout("Easy Run", garmin_workouts)
        assert result == "gw-123"

    def test_returns_none_when_no_match(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-123", "workoutName": "Easy Run"},
        ]
        result = find_matching_garmin_workout("Long Run", garmin_workouts)
        assert result is None

    def test_is_case_insensitive(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-123", "workoutName": "easy run"},
        ]
        result = find_matching_garmin_workout("Easy Run", garmin_workouts)
        assert result == "gw-123"

    def test_returns_none_for_empty_list(self) -> None:
        result = find_matching_garmin_workout("Easy Run", [])
        assert result is None

    def test_returns_first_match_when_duplicates_exist(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-111", "workoutName": "Easy Run"},
            {"workoutId": "gw-222", "workoutName": "Easy Run"},
        ]
        result = find_matching_garmin_workout("Easy Run", garmin_workouts)
        assert result == "gw-111"

    def test_handles_missing_workoutName_gracefully(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-123"},  # no workoutName key
        ]
        result = find_matching_garmin_workout("Easy Run", garmin_workouts)
        assert result is None


class TestFindOrphanedGarminWorkouts:
    def test_returns_untracked_workouts_matching_our_names(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-111", "workoutName": "Easy Run"},
            {"workoutId": "gw-222", "workoutName": "Tempo Run"},
        ]
        known_garmin_ids: set[str] = set()  # none tracked
        known_template_names = {"Easy Run", "Tempo Run"}

        result = find_orphaned_garmin_workouts(
            garmin_workouts, known_garmin_ids, known_template_names
        )
        assert set(result) == {"gw-111", "gw-222"}

    def test_does_not_return_tracked_workouts(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-111", "workoutName": "Easy Run"},
            {"workoutId": "gw-222", "workoutName": "Tempo Run"},
        ]
        known_garmin_ids = {"gw-111"}  # gw-111 is tracked
        known_template_names = {"Easy Run", "Tempo Run"}

        result = find_orphaned_garmin_workouts(
            garmin_workouts, known_garmin_ids, known_template_names
        )
        assert result == ["gw-222"]

    def test_does_not_return_user_created_garmin_workouts(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-111", "workoutName": "Easy Run"},       # ours
            {"workoutId": "gw-999", "workoutName": "My Custom Run"},  # user's
        ]
        known_garmin_ids: set[str] = set()
        known_template_names = {"Easy Run"}  # only "Easy Run" is ours

        result = find_orphaned_garmin_workouts(
            garmin_workouts, known_garmin_ids, known_template_names
        )
        assert result == ["gw-111"]

    def test_returns_empty_when_all_tracked(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-111", "workoutName": "Easy Run"},
        ]
        known_garmin_ids = {"gw-111"}
        known_template_names = {"Easy Run"}

        result = find_orphaned_garmin_workouts(
            garmin_workouts, known_garmin_ids, known_template_names
        )
        assert result == []

    def test_name_matching_is_case_insensitive(self) -> None:
        garmin_workouts = [
            {"workoutId": "gw-111", "workoutName": "easy run"},
        ]
        known_garmin_ids: set[str] = set()
        known_template_names = {"Easy Run"}

        result = find_orphaned_garmin_workouts(
            garmin_workouts, known_garmin_ids, known_template_names
        )
        assert result == ["gw-111"]


class TestFindMissingFromGarmin:
    def test_returns_ids_not_on_garmin(self) -> None:
        """DB IDs not found in Garmin workout list are returned."""
        garmin_workouts = [
            {"workoutId": "aaa", "workoutName": "Run 1"},
            {"workoutId": "bbb", "workoutName": "Run 2"},
        ]
        db_garmin_ids = {"aaa", "bbb", "ccc", "ddd"}

        result = find_missing_from_garmin(db_garmin_ids, garmin_workouts)

        assert result == {"ccc", "ddd"}

    def test_returns_empty_when_all_present(self) -> None:
        """When every DB ID exists on Garmin, nothing is missing."""
        garmin_workouts = [
            {"workoutId": "aaa", "workoutName": "Run 1"},
            {"workoutId": "bbb", "workoutName": "Run 2"},
        ]
        db_garmin_ids = {"aaa", "bbb"}

        result = find_missing_from_garmin(db_garmin_ids, garmin_workouts)

        assert result == set()

    def test_returns_all_when_garmin_list_empty(self) -> None:
        """When Garmin has no workouts, all DB IDs are missing."""
        db_garmin_ids = {"aaa", "bbb"}

        result = find_missing_from_garmin(db_garmin_ids, [])

        assert result == {"aaa", "bbb"}

    def test_returns_empty_when_db_ids_empty(self) -> None:
        """When DB has no synced IDs, nothing is missing."""
        garmin_workouts = [{"workoutId": "aaa", "workoutName": "Run 1"}]

        result = find_missing_from_garmin(set(), garmin_workouts)

        assert result == set()

    def test_coerces_workout_id_to_string(self) -> None:
        """Garmin workoutId may be int — must compare as string."""
        garmin_workouts = [{"workoutId": 12345, "workoutName": "Run"}]
        db_garmin_ids = {"12345", "99999"}

        result = find_missing_from_garmin(db_garmin_ids, garmin_workouts)

        assert result == {"99999"}
