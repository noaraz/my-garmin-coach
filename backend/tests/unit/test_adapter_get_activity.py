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


class TestGetActivityProtocol:
    def test_protocol_declares_get_activity(self):
        assert hasattr(GarminAdapterProtocol, "get_activity")

    def test_v1_satisfies_protocol(self):
        mock_client = MagicMock()
        adapter = GarminAdapter(mock_client)
        assert isinstance(adapter, GarminAdapterProtocol)

    def test_v2_satisfies_protocol(self):
        mock_client = MagicMock()
        adapter = GarminAdapterV2(mock_client)
        assert isinstance(adapter, GarminAdapterProtocol)


class TestV1GetActivity:
    def test_returns_raw_dict_on_success(self):
        mock_client = MagicMock()
        mock_client.get_activity.return_value = {
            "activityId": "12345",
            "activityName": "Morning Run",
            "summaryDTO": {"distance": 10000.0, "duration": 3600.0},
        }
        adapter = GarminAdapter(mock_client)
        result = adapter.get_activity("12345")
        assert result["activityId"] == "12345"
        mock_client.get_activity.assert_called_once_with("12345")

    def test_translates_404_to_not_found_error(self):
        from garth.exc import GarthHTTPError
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_inner = MagicMock()
        mock_inner.response = mock_response
        exc = GarthHTTPError("404 Not Found", error=mock_inner)
        mock_client = MagicMock()
        mock_client.get_activity.side_effect = exc
        adapter = GarminAdapter(mock_client)
        with pytest.raises(GarminNotFoundError):
            adapter.get_activity("missing-id")

    def test_translates_429_to_rate_limit_error(self):
        from garth.exc import GarthHTTPError
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_inner = MagicMock()
        mock_inner.response = mock_response
        exc = GarthHTTPError("429 Too Many Requests", error=mock_inner)
        mock_client = MagicMock()
        mock_client.get_activity.side_effect = exc
        adapter = GarminAdapter(mock_client)
        with pytest.raises(GarminRateLimitError):
            adapter.get_activity("some-id")


class TestV2GetActivity:
    def test_returns_raw_dict_on_success(self):
        mock_client = MagicMock()
        mock_client.get_activity.return_value = {
            "activityId": "67890",
            "activityName": "Evening Run",
            "distance": 5000.0,
        }
        adapter = GarminAdapterV2(mock_client)
        result = adapter.get_activity("67890")
        assert result["activityId"] == "67890"
        mock_client.get_activity.assert_called_once_with("67890")

    def test_translates_404_string_to_not_found_error(self):
        import garminconnect
        exc = garminconnect.GarminConnectConnectionError("404 Not Found")
        exc.status_code = 404
        mock_client = MagicMock()
        mock_client.get_activity.side_effect = exc
        adapter = GarminAdapterV2(mock_client)
        with pytest.raises(GarminNotFoundError):
            adapter.get_activity("missing-id")

    def test_translates_too_many_requests_to_rate_limit_error(self):
        import garminconnect
        exc = garminconnect.GarminConnectTooManyRequestsError("429")
        mock_client = MagicMock()
        mock_client.get_activity.side_effect = exc
        adapter = GarminAdapterV2(mock_client)
        with pytest.raises(GarminRateLimitError):
            adapter.get_activity("some-id")
