"""Tests for the Garmin client factory — centralized Chrome TLS session creation."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests


class TestChromeTLSSession:
    """ChromeTLSSession must have requests.Session compatibility attributes."""

    def test_has_adapters_attribute(self) -> None:
        from src.garmin.client_factory import ChromeTLSSession

        session = ChromeTLSSession(impersonate="chrome120")
        assert hasattr(session, "adapters")
        assert isinstance(session.adapters, dict)

    def test_has_hooks_attribute(self) -> None:
        from src.garmin.client_factory import ChromeTLSSession

        session = ChromeTLSSession(impersonate="chrome120")
        assert hasattr(session, "hooks")
        rs = requests.Session()
        assert set(session.hooks.keys()) == set(rs.hooks.keys())


class TestCreateApiClient:
    """create_api_client must return a GarminAdapter with Chrome TLS session."""

    @patch("src.garmin.client_factory.garminconnect")
    def test_returns_garmin_adapter(self, mock_gc: MagicMock) -> None:
        from src.garmin.adapter import GarminAdapter
        from src.garmin.client_factory import create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        adapter = create_api_client('{"token": "fake"}')
        assert isinstance(adapter, GarminAdapter)

    @patch("src.garmin.client_factory.garminconnect")
    def test_loads_token_json(self, mock_gc: MagicMock) -> None:
        from src.garmin.client_factory import create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        create_api_client('{"token": "test123"}')
        mock_client.garth.loads.assert_called_once_with('{"token": "test123"}')

    @patch("src.garmin.client_factory.garminconnect")
    def test_injects_chrome_tls_session(self, mock_gc: MagicMock) -> None:
        from src.garmin.client_factory import ChromeTLSSession, create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        create_api_client('{"token": "fake"}')
        assert isinstance(mock_client.garth.sess, ChromeTLSSession)


class TestCreateLoginClient:
    """create_login_client must return a garth.Client with Chrome TLS session."""

    def test_returns_garth_client(self) -> None:
        import garth

        from src.garmin.client_factory import create_login_client

        client = create_login_client()
        assert isinstance(client, garth.Client)

    def test_has_chrome_tls_session(self) -> None:
        from src.garmin.client_factory import ChromeTLSSession, create_login_client

        client = create_login_client()
        assert isinstance(client.sess, ChromeTLSSession)

    def test_no_proxy_by_default(self) -> None:
        from src.garmin.client_factory import create_login_client

        client = create_login_client()
        assert not getattr(client.sess, "proxies", None)

    def test_sets_proxy_when_provided(self) -> None:
        from src.garmin.client_factory import create_login_client

        client = create_login_client(proxy_url="https://proxy.example.com")
        assert client.sess.proxies == {"https": "https://proxy.example.com"}
