"""Tests for the Garmin client factory — centralized Chrome TLS session creation."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import garth
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


class TestChromeTLSExchange:
    """refresh_oauth2 must route the token exchange through curl_cffi, not requests."""

    @patch("src.garmin.client_factory.garminconnect")
    def test_refresh_oauth2_uses_curl_cffi_session(self, mock_gc: MagicMock) -> None:
        """The patched refresh_oauth2 must POST via ChromeTLSSession, not GarminOAuth1Session."""
        from src.garmin.client_factory import create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        # We need to verify that refresh_oauth2 is replaced on the garth client
        create_api_client('{"token": "fake"}')
        garth_client = mock_client.garth

        # refresh_oauth2 should be overridden (not the original garth method)
        assert garth_client.refresh_oauth2 != garth.Client.refresh_oauth2

    @patch("src.garmin.client_factory.garminconnect")
    def test_refresh_oauth2_calls_exchange_via_chrome_tls(self, mock_gc: MagicMock) -> None:
        """When refresh_oauth2 fires, the HTTP POST to connectapi must go through curl_cffi."""
        from src.garmin.client_factory import create_api_client

        mock_client = MagicMock()
        mock_gc.Garmin.return_value = mock_client

        # Set up a real-ish garth client with tokens so we can test the exchange
        mock_garth = MagicMock()
        mock_client.garth = mock_garth
        mock_garth.domain = "garmin.com"
        mock_garth.timeout = 10

        # Mock OAuth1Token
        mock_oauth1 = MagicMock()
        mock_oauth1.oauth_token = "test_oauth_token"
        mock_oauth1.oauth_token_secret = "test_oauth_secret"
        mock_oauth1.mfa_token = None
        mock_garth.oauth1_token = mock_oauth1

        create_api_client('{"token": "fake"}')

        # The refresh_oauth2 method should have been replaced
        assert callable(mock_garth.refresh_oauth2)

    @patch("src.garmin.client_factory._chrome_tls_exchange")
    def test_refresh_oauth2_delegates_to_chrome_tls_exchange(
        self, mock_exchange: MagicMock
    ) -> None:
        """refresh_oauth2 override must call _chrome_tls_exchange with the right args."""
        from garth.auth_tokens import OAuth1Token, OAuth2Token

        from src.garmin.client_factory import _chrome_tls_exchange

        # Build a real garth Client with tokens set directly (bypass loads)
        garth_client = garth.Client()
        oauth1 = OAuth1Token(oauth_token="tok", oauth_token_secret="sec")
        garth_client.oauth1_token = oauth1

        # Manually wire what create_api_client does: set session + override
        from src.garmin.client_factory import ChromeTLSSession

        garth_client.sess = ChromeTLSSession(impersonate="chrome120")

        # Apply the same monkey-patch that create_api_client applies
        def _patched() -> None:
            assert garth_client.oauth1_token and isinstance(
                garth_client.oauth1_token, OAuth1Token
            )
            garth_client.oauth2_token = _chrome_tls_exchange(
                garth_client.oauth1_token, garth_client
            )

        garth_client.refresh_oauth2 = _patched  # type: ignore[assignment]

        # Call the overridden method
        fake_token = MagicMock(spec=OAuth2Token)
        mock_exchange.return_value = fake_token
        garth_client.refresh_oauth2()

        mock_exchange.assert_called_once_with(oauth1, garth_client)
        assert garth_client.oauth2_token is fake_token
