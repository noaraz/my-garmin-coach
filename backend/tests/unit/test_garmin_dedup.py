"""Tests for Garmin workout deduplication logic."""
from __future__ import annotations

from src.garmin.dedup import (
    find_matching_garmin_workout,
    find_orphaned_garmin_workouts,
    find_unscheduled_workouts,
)


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


class TestFindUnscheduledWorkouts:
    """Tests for find_unscheduled_workouts — calendar-based reconciliation."""

    def test_all_scheduled_returns_empty(self) -> None:
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
            {"garmin_workout_id": "200", "date": "2026-04-03"},
        ]
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-01"},
            {"workoutId": 200, "date": "2026-04-03"},
        ]
        result = find_unscheduled_workouts(db_workouts, calendar_items)
        assert result == []

    def test_missing_from_calendar_returns_unscheduled(self) -> None:
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
            {"garmin_workout_id": "200", "date": "2026-04-03"},
        ]
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-01"},
        ]
        result = find_unscheduled_workouts(db_workouts, calendar_items)
        assert len(result) == 1
        assert result[0]["garmin_workout_id"] == "200"
        assert result[0]["date"] == "2026-04-03"

    def test_different_date_counts_as_unscheduled(self) -> None:
        """Same workoutId but different date = not a match."""
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
        ]
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-05"},
        ]
        result = find_unscheduled_workouts(db_workouts, calendar_items)
        assert len(result) == 1

    def test_empty_calendar_returns_all(self) -> None:
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
        ]
        result = find_unscheduled_workouts(db_workouts, [])
        assert len(result) == 1

    def test_empty_db_returns_empty(self) -> None:
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-01"},
        ]
        result = find_unscheduled_workouts([], calendar_items)
        assert result == []

    def test_workoutId_string_vs_int_handled(self) -> None:
        """Garmin returns workoutId as int, DB stores as string."""
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
        ]
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-01"},
        ]
        result = find_unscheduled_workouts(db_workouts, calendar_items)
        assert result == []
