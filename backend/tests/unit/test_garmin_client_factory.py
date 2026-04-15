"""Tests for the Garmin client factory — centralized Chrome TLS session creation."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import garth
import requests

from src.garmin.client_factory import CHROME_VERSION


class TestChromeTLSSession:
    """ChromeTLSSession must have requests.Session compatibility attributes."""

    def test_adapters_when_created_returns_dict(self) -> None:
        from src.garmin.client_factory import ChromeTLSSession

        session = ChromeTLSSession(impersonate=CHROME_VERSION)
        assert hasattr(session, "adapters")
        assert isinstance(session.adapters, dict)

    def test_hooks_when_created_matches_requests_session(self) -> None:
        from src.garmin.client_factory import ChromeTLSSession

        session = ChromeTLSSession(impersonate=CHROME_VERSION)
        assert hasattr(session, "hooks")
        rs = requests.Session()
        assert set(session.hooks.keys()) == set(rs.hooks.keys())


class TestCreateApiClient:
    """create_api_client must return a GarminAdapter with Chrome TLS session."""

    @patch("src.garmin.client_factory.garminconnect")
    def test_create_api_client_when_called_returns_garmin_adapter(self, mock_gc: MagicMock) -> None:
        from src.garmin.adapter import GarminAdapter
        from src.garmin.client_factory import create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        adapter = create_api_client('{"token": "fake"}')
        assert isinstance(adapter, GarminAdapter)

    @patch("src.garmin.client_factory.garminconnect")
    def test_create_api_client_when_called_loads_token_json(self, mock_gc: MagicMock) -> None:
        from src.garmin.client_factory import create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        create_api_client('{"token": "test123"}')
        mock_client.garth.loads.assert_called_once_with('{"token": "test123"}')

    @patch("src.garmin.client_factory.garminconnect")
    def test_create_api_client_when_called_injects_chrome_tls_session(self, mock_gc: MagicMock) -> None:
        from src.garmin.client_factory import ChromeTLSSession, create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        create_api_client('{"token": "fake"}')
        assert isinstance(mock_client.garth.sess, ChromeTLSSession)

    @patch("src.garmin.client_factory.garminconnect")
    def test_refresh_oauth2_when_client_created_not_overridden(self, mock_gc: MagicMock) -> None:
        """Native garth refresh_oauth2 must NOT be overridden.

        garth's sso.exchange() via GarminOAuth1Session(parent=ChromeTLSSession)
        uses standard Python TLS which Akamai allows — proven by login flow.
        """
        from src.garmin.client_factory import create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        create_api_client('{"token": "fake"}')

        # refresh_oauth2 should NOT have been replaced
        garth_client = mock_client.garth
        # MagicMock auto-creates attributes, so check it wasn't explicitly set
        assert "refresh_oauth2" not in garth_client.__dict__


class TestCreateAdapterVersionRouting:
    """create_adapter must route to V1 or V2 based on auth_version param."""

    @patch("src.garmin.client_factory.garminconnect")
    def test_create_adapter_v1_when_garth_token_parses_correctly(self, mock_gc: MagicMock) -> None:
        from src.garmin.adapter_v1 import GarminAdapter
        from src.garmin.client_factory import create_adapter

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        adapter = create_adapter('{"token": "garth_format"}', auth_version="v1")
        assert isinstance(adapter, GarminAdapter)
        mock_client.garth.loads.assert_called_once_with('{"token": "garth_format"}')

    @patch("src.garmin.client_factory.garminconnect")
    def test_create_adapter_v2_when_json_token_parses_correctly(self, mock_gc: MagicMock) -> None:
        from src.garmin.adapter_v2 import GarminAdapterV2
        from src.garmin.client_factory import create_adapter

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        adapter = create_adapter('{"oauth1": "tok", "oauth2": "tok2"}', auth_version="v2")
        assert isinstance(adapter, GarminAdapterV2)

    def test_create_adapter_v2_when_garth_token_raises_json_error(self) -> None:
        """V1 garth tokens are not valid JSON dicts — V2 adapter must fail.

        This is the real-world bug: global flag switched to v2 but existing users
        still have V1 garth tokens stored. The adapter must be created with the
        profile's auth_version, not the global flag.
        """
        import json

        from src.garmin.client_factory import create_adapter

        garth_style_token = "not-a-json-dict"  # garth.dumps() produces non-JSON
        with __import__("pytest").raises(json.JSONDecodeError):
            create_adapter(garth_style_token, auth_version="v2")


class TestCreateLoginClient:
    """create_login_client must return a garth.Client with Chrome TLS session."""

    def test_create_login_client_when_called_returns_garth_client(self) -> None:
        from src.garmin.client_factory import create_login_client

        client = create_login_client()
        assert isinstance(client, garth.Client)

    def test_create_login_client_when_called_has_chrome_tls_session(self) -> None:
        from src.garmin.client_factory import ChromeTLSSession, create_login_client

        client = create_login_client()
        assert isinstance(client.sess, ChromeTLSSession)

    def test_create_login_client_when_no_proxy_has_empty_proxies(self) -> None:
        from src.garmin.client_factory import create_login_client

        client = create_login_client()
        assert not getattr(client.sess, "proxies", None)

    def test_create_login_client_when_proxy_provided_sets_proxies(self) -> None:
        from src.garmin.client_factory import create_login_client

        client = create_login_client(proxy_url="https://proxy.example.com")
        assert client.sess.proxies == {"https": "https://proxy.example.com"}

    def test_create_login_client_when_fingerprint_provided_uses_it(self) -> None:
        from src.garmin.client_factory import create_login_client

        client = create_login_client(fingerprint="safari15_5")
        assert client.sess.impersonate == "safari15_5"
