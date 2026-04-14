from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.garmin.adapter_protocol import GarminAdapterProtocol


class TestClientFactoryV2:
    """Test factory functions branch correctly on auth version."""

    @patch("src.garmin.client_factory._get_auth_version", return_value="v2")
    @patch("src.garmin.client_factory.garminconnect.Garmin")
    def test_create_adapter_v2(self, mock_garmin_cls, mock_version) -> None:
        from src.garmin.client_factory import create_adapter
        mock_client = MagicMock()
        mock_garmin_cls.return_value = mock_client
        adapter = create_adapter('{"access_token": "test"}')
        assert isinstance(adapter, GarminAdapterProtocol)

    @patch("src.garmin.client_factory._get_auth_version", return_value="v1")
    def test_create_adapter_v1(self, mock_version) -> None:
        from src.garmin.client_factory import create_adapter
        with patch("src.garmin.client_factory.garminconnect.Garmin") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            adapter = create_adapter('{"oauth1": "test"}')
            assert isinstance(adapter, GarminAdapterProtocol)

    @patch("src.garmin.client_factory._get_auth_version", return_value="v2")
    @patch("src.garmin.client_factory.garminconnect.Garmin")
    def test_login_v2(self, mock_garmin_cls, mock_version) -> None:
        from src.garmin.client_factory import login_and_get_token
        mock_client = MagicMock()
        mock_client.garmin_tokens = {"access_token": "fresh"}
        mock_garmin_cls.return_value = mock_client
        token = login_and_get_token("user@test.com", "pass123")
        mock_client.login.assert_called_once()
        assert "fresh" in token

    @patch("src.garmin.client_factory._get_auth_version", return_value="v1")
    def test_create_adapter_explicit_version_override(self, mock_version) -> None:
        """Explicit auth_version parameter overrides settings."""
        from src.garmin.client_factory import create_adapter
        with patch("src.garmin.client_factory.garminconnect.Garmin") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            adapter = create_adapter('{"access_token": "test"}', auth_version="v2")
            # Should use V2 even though settings says V1
            from src.garmin.adapter_v2 import GarminAdapterV2
            assert isinstance(adapter, GarminAdapterV2)
