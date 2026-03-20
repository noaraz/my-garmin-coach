from __future__ import annotations

from unittest.mock import MagicMock

from src.garmin.adapter import GarminAdapter


class TestGarminAdapter:
    def test_add_workout_delegates(self):
        mock_client = MagicMock()
        mock_client.upload_workout.return_value = {"workoutId": "123"}
        adapter = GarminAdapter(mock_client)
        result = adapter.add_workout({"workoutName": "Test"})
        mock_client.upload_workout.assert_called_once_with({"workoutName": "Test"})
        assert result == {"workoutId": "123"}

    def test_get_activities_by_date_delegates(self):
        mock_client = MagicMock()
        mock_client.get_activities_by_date.return_value = [
            {"activityId": "1", "activityType": {"typeKey": "running"}},
        ]
        adapter = GarminAdapter(mock_client)
        result = adapter.get_activities_by_date("2026-03-01", "2026-03-19")
        mock_client.get_activities_by_date.assert_called_once_with("2026-03-01", "2026-03-19")
        assert len(result) == 1

    def test_schedule_workout_delegates(self):
        mock_client = MagicMock()
        adapter = GarminAdapter(mock_client)
        adapter.schedule_workout("123", "2026-03-19")
        mock_client.garth.post.assert_called_once()

    def test_delete_workout_delegates(self):
        mock_client = MagicMock()
        adapter = GarminAdapter(mock_client)
        adapter.delete_workout("456")
        mock_client.garth.delete.assert_called_once()

    def test_update_workout_delegates(self):
        mock_client = MagicMock()
        adapter = GarminAdapter(mock_client)
        adapter.update_workout("789", {"workoutName": "Updated"})
        mock_client.garth.put.assert_called_once()
