from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.garmin.adapter_protocol import (
    GarminAdapterProtocol,
    GarminNotFoundError,
    GarminRateLimitError,
)
from src.garmin.adapter_v1 import GarminAdapter
from src.garmin.adapter_v2 import GarminAdapterV2


class TestGetActivitySplitsProtocol:
    def test_protocol_declares_get_activity_splits(self):
        assert hasattr(GarminAdapterProtocol, "get_activity_splits")

    def test_v1_satisfies_protocol(self):
        mock_client = MagicMock()
        adapter = GarminAdapter(mock_client)
        assert isinstance(adapter, GarminAdapterProtocol)

    def test_v2_satisfies_protocol(self):
        mock_client = MagicMock()
        adapter = GarminAdapterV2(mock_client)
        assert isinstance(adapter, GarminAdapterProtocol)


class TestV1GetActivitySplits:
    def test_returns_laps_list_on_success(self):
        mock_client = MagicMock()
        mock_client.get_activity_splits.return_value = {
            "lapDTOs": [
                {"lapIndex": 0, "distance": 1000.0, "duration": 300.0},
                {"lapIndex": 1, "distance": 1000.0, "duration": 310.0},
            ]
        }
        adapter = GarminAdapter(mock_client)
        result = adapter.get_activity_splits("12345")
        assert len(result) == 2
        assert result[0]["lapIndex"] == 0
        mock_client.get_activity_splits.assert_called_once_with("12345")

    def test_returns_empty_list_when_no_laps(self):
        mock_client = MagicMock()
        mock_client.get_activity_splits.return_value = {"lapDTOs": []}
        adapter = GarminAdapter(mock_client)
        result = adapter.get_activity_splits("12345")
        assert result == []

    def test_returns_empty_list_when_lapDTOs_missing(self):
        mock_client = MagicMock()
        mock_client.get_activity_splits.return_value = {}
        adapter = GarminAdapter(mock_client)
        result = adapter.get_activity_splits("12345")
        assert result == []

    def test_translates_404_to_not_found_error(self):
        from garth.exc import GarthHTTPError
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_inner = MagicMock()
        mock_inner.response = mock_response
        exc = GarthHTTPError("404 Not Found", error=mock_inner)
        mock_client = MagicMock()
        mock_client.get_activity_splits.side_effect = exc
        adapter = GarminAdapter(mock_client)
        with pytest.raises(GarminNotFoundError):
            adapter.get_activity_splits("missing-id")

    def test_translates_429_to_rate_limit_error(self):
        from garth.exc import GarthHTTPError
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_inner = MagicMock()
        mock_inner.response = mock_response
        exc = GarthHTTPError("429 Too Many Requests", error=mock_inner)
        mock_client = MagicMock()
        mock_client.get_activity_splits.side_effect = exc
        adapter = GarminAdapter(mock_client)
        with pytest.raises(GarminRateLimitError):
            adapter.get_activity_splits("some-id")


class TestV2GetActivitySplits:
    def test_returns_laps_list_on_success(self):
        mock_client = MagicMock()
        mock_client.get_activity_splits.return_value = {
            "lapDTOs": [
                {"lapIndex": 0, "distance": 2000.0, "duration": 600.0},
                {"lapIndex": 1, "distance": 2000.0, "duration": 605.0},
                {"lapIndex": 2, "distance": 2000.0, "duration": 610.0},
            ]
        }
        adapter = GarminAdapterV2(mock_client)
        result = adapter.get_activity_splits("67890")
        assert len(result) == 3
        assert result[1]["lapIndex"] == 1
        mock_client.get_activity_splits.assert_called_once_with("67890")

    def test_returns_empty_list_when_no_laps(self):
        mock_client = MagicMock()
        mock_client.get_activity_splits.return_value = {"lapDTOs": []}
        adapter = GarminAdapterV2(mock_client)
        result = adapter.get_activity_splits("67890")
        assert result == []

    def test_returns_empty_list_when_lapDTOs_missing(self):
        mock_client = MagicMock()
        mock_client.get_activity_splits.return_value = {}
        adapter = GarminAdapterV2(mock_client)
        result = adapter.get_activity_splits("67890")
        assert result == []

    def test_translates_404_string_to_not_found_error(self):
        import garminconnect
        exc = garminconnect.GarminConnectConnectionError("404 Not Found")
        exc.status_code = 404
        mock_client = MagicMock()
        mock_client.get_activity_splits.side_effect = exc
        adapter = GarminAdapterV2(mock_client)
        with pytest.raises(GarminNotFoundError):
            adapter.get_activity_splits("missing-id")

    def test_translates_too_many_requests_to_rate_limit_error(self):
        import garminconnect
        exc = garminconnect.GarminConnectTooManyRequestsError("429")
        mock_client = MagicMock()
        mock_client.get_activity_splits.side_effect = exc
        adapter = GarminAdapterV2(mock_client)
        with pytest.raises(GarminRateLimitError):
            adapter.get_activity_splits("some-id")
