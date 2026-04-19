from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.garmin.adapter_protocol import (
    GarminAdapterProtocol,
    GarminAuthError,
    GarminNotFoundError,
    GarminRateLimitError,
)


class TestGarminAdapterV2:
    """Test GarminAdapterV2 wrapping garminconnect 0.3.x client."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        client = MagicMock()
        client.get_activities_by_date.return_value = []
        client.get_workouts.return_value = []
        client.connectapi.return_value = {"calendarItems": []}
        return client

    @pytest.fixture
    def adapter(self, mock_client: MagicMock):
        from src.garmin.adapter_v2 import GarminAdapterV2
        return GarminAdapterV2(mock_client)

    def test_implements_protocol(self, adapter) -> None:
        assert isinstance(adapter, GarminAdapterProtocol)

    def test_add_workout_delegates(self, adapter, mock_client: MagicMock) -> None:
        mock_client.client.post.return_value = {"workoutId": "123"}
        result = adapter.add_workout({"workoutName": "Test"})
        mock_client.client.post.assert_called_once_with(
            "connect", "/workout-service/workout", json={"workoutName": "Test"}, api=True,
        )
        assert result["workoutId"] == "123"

    def test_delete_workout_delegates(self, adapter, mock_client: MagicMock) -> None:
        adapter.delete_workout("123")
        mock_client.delete_workout.assert_called_once_with("123")

    def test_unschedule_workout_delegates(self, adapter, mock_client: MagicMock) -> None:
        adapter.unschedule_workout("456")
        mock_client.unschedule_workout.assert_called_once_with("456")

    def test_get_activities_by_date_delegates(self, adapter, mock_client: MagicMock) -> None:
        adapter.get_activities_by_date("2026-01-01", "2026-01-31")
        mock_client.get_activities_by_date.assert_called_once_with("2026-01-01", "2026-01-31")

    def test_get_workouts_delegates(self, adapter, mock_client: MagicMock) -> None:
        adapter.get_workouts()
        mock_client.get_workouts.assert_called_once()

    def test_get_calendar_items_converts_month(self, adapter, mock_client: MagicMock) -> None:
        """Garmin uses 0-indexed months. Adapter converts 1-indexed → 0-indexed."""
        mock_client.connectapi.return_value = {"calendarItems": [{"id": 1}]}
        result = adapter.get_calendar_items(2026, 3)
        mock_client.connectapi.assert_called_once_with("/calendar-service/year/2026/month/2")
        assert result == [{"id": 1}]

    def test_dump_token_serializes(self, adapter, mock_client: MagicMock) -> None:
        mock_client.client.dumps.return_value = '{"di_token": "abc", "di_refresh_token": "xyz"}'
        result = adapter.dump_token()
        parsed = json.loads(result)
        assert parsed["di_token"] == "abc"

    def test_auth_error_translated(self, adapter, mock_client: MagicMock) -> None:
        from garminconnect import GarminConnectAuthenticationError
        mock_client.delete_workout.side_effect = GarminConnectAuthenticationError("bad creds")
        with pytest.raises(GarminAuthError):
            adapter.delete_workout("123")

    def test_rate_limit_translated(self, adapter, mock_client: MagicMock) -> None:
        from garminconnect import GarminConnectTooManyRequestsError
        mock_client.get_workouts.side_effect = GarminConnectTooManyRequestsError("429")
        with pytest.raises(GarminRateLimitError):
            adapter.get_workouts()

    def test_404_translated(self, adapter, mock_client: MagicMock) -> None:
        from garminconnect import GarminConnectConnectionError
        exc = GarminConnectConnectionError("404 Not Found")
        exc.status_code = 404
        mock_client.delete_workout.side_effect = exc
        with pytest.raises(GarminNotFoundError):
            adapter.delete_workout("123")
