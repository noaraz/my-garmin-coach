"""Unit tests for the garmin_connect router functions.

These tests call the route handler functions directly (not via HTTP)
to ensure pytest-cov properly instruments the async function bodies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests
from curl_cffi import requests as cffi_requests
from fastapi import HTTPException

from src.api.routers.garmin_connect import (
    _get_or_create_profile,
    connect_garmin,
    disconnect_garmin,
    garmin_status,
)
from src.auth.models import User
from src.auth.schemas import GarminConnectRequest
from src.db.models import AthleteProfile


def _make_user(user_id: int = 1) -> User:
    return User(id=user_id, email="test@example.com", is_active=True)


def _make_session() -> AsyncMock:
    """Return an AsyncMock session with a synchronous .add() stub."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# _get_or_create_profile — private helper
# ---------------------------------------------------------------------------


class TestGetOrCreateProfile:
    async def test_returns_existing_profile_when_found(self) -> None:
        # Arrange
        user = _make_user()
        existing = AthleteProfile(id=1, name="Runner", user_id=1)
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = existing
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        result = await _get_or_create_profile(user, mock_session)

        # Assert
        assert result is existing
        mock_session.add.assert_not_called()

    async def test_creates_profile_when_not_found(self) -> None:
        # Arrange
        user = _make_user()
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        await _get_or_create_profile(user, mock_session)

        # Assert — profile was created and added to session
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()
        # The created profile should have the user_id
        created = mock_session.add.call_args[0][0]
        assert created.user_id == user.id


# ---------------------------------------------------------------------------
# connect_garmin
# ---------------------------------------------------------------------------


class TestConnectGarmin:
    async def test_connect_returns_connected_true_on_success(self) -> None:
        # Arrange
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None  # no existing profile
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        mock_garth_client = MagicMock()
        mock_garth_client.dumps.return_value = '{"oauth_token": "tok"}'

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.cache"), \
             patch("src.api.routers.garmin_connect.client_cache"):
            mock_factory.return_value = mock_garth_client
            mock_settings.return_value.garmincoach_secret_key = "test-key"
            mock_settings.return_value.garmin_credential_key = "test-cred-key"
            mock_settings.return_value.fixie_url = ""  # no proxy in tests

            # Act
            result = await connect_garmin(
                request=request,
                current_user=user,
                session=mock_session,
            )

        # Assert
        assert result.connected is True

    async def test_connect_raises_400_when_garth_raises(self) -> None:
        # Arrange
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="wrong")
        mock_session = _make_session()

        mock_garth_client = MagicMock()
        mock_garth_client.login.side_effect = Exception("Bad credentials")

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings:
            mock_factory.return_value = mock_garth_client
            mock_settings.return_value.fixie_url = ""  # no proxy in tests

            # Act / Assert
            with pytest.raises(HTTPException) as exc_info:
                await connect_garmin(
                    request=request,
                    current_user=user,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 400
        assert "Garmin authentication failed" in exc_info.value.detail

    async def test_connect_retries_once_on_429_then_succeeds(self) -> None:
        # Arrange — first attempt raises 429, second succeeds
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        resp_429 = MagicMock()
        resp_429.status_code = 429
        http_429 = requests.exceptions.HTTPError(response=resp_429)

        mock_garth_client_fail = MagicMock()
        mock_garth_client_fail.login.side_effect = http_429

        mock_garth_client_ok = MagicMock()
        mock_garth_client_ok.dumps.return_value = '{"oauth_token": "tok"}'

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.asyncio.sleep") as mock_sleep, \
             patch("src.api.routers.garmin_connect.random.uniform", return_value=35.0) as mock_uniform, \
             patch("src.api.routers.garmin_connect.cache"), \
             patch("src.api.routers.garmin_connect.client_cache"):
            mock_factory.side_effect = [mock_garth_client_fail, mock_garth_client_ok]
            mock_settings.return_value.garmincoach_secret_key = "test-key"
            mock_settings.return_value.garmin_credential_key = "test-cred-key"
            mock_settings.return_value.fixie_url = ""  # no proxy in tests

            result = await connect_garmin(
                request=request,
                current_user=user,
                session=mock_session,
            )

        assert result.connected is True
        mock_uniform.assert_called_once_with(30, 45)
        mock_sleep.assert_awaited_once_with(35.0)
        assert mock_factory.call_count == 2

    async def test_connect_raises_503_when_both_attempts_rate_limited(self) -> None:
        # Arrange — all 5 fingerprint attempts get 429
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()

        resp_429 = MagicMock()
        resp_429.status_code = 429
        http_429 = requests.exceptions.HTTPError(response=resp_429)

        mock_garth_client = MagicMock()
        mock_garth_client.login.side_effect = http_429

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.asyncio.sleep"), \
             patch("src.api.routers.garmin_connect.random.uniform", return_value=35.0):
            mock_factory.return_value = mock_garth_client
            mock_settings.return_value.fixie_url = ""  # no proxy in tests

            with pytest.raises(HTTPException) as exc_info:
                await connect_garmin(
                    request=request,
                    current_user=user,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 503
        assert "rate-limiting" in exc_info.value.detail
        assert mock_factory.call_count == 5  # all 5 fingerprints attempted

    async def test_connect_stores_encrypted_token_on_profile(self) -> None:
        # Arrange
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()

        # The profile returned from _get_or_create_profile (mocked to return existing)
        profile = AthleteProfile(id=1, name="Runner", user_id=1)
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = profile
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        mock_garth_client = MagicMock()
        mock_garth_client.dumps.return_value = '{"oauth_token": "garmin_tok"}'

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.cache"), \
             patch("src.api.routers.garmin_connect.client_cache"):
            mock_factory.return_value = mock_garth_client
            mock_settings.return_value.garmincoach_secret_key = "test-key"
            mock_settings.return_value.garmin_credential_key = "test-cred-key"
            mock_settings.return_value.fixie_url = ""  # no proxy in tests

            # Act
            await connect_garmin(
                request=request,
                current_user=user,
                session=mock_session,
            )

        # Assert
        assert profile.garmin_connected is True
        assert profile.garmin_oauth_token_encrypted is not None
        # Token should not be stored as plaintext
        assert "garmin_tok" not in profile.garmin_oauth_token_encrypted
        # Credentials should be stored encrypted
        assert profile.garmin_credential_encrypted is not None
        assert profile.garmin_credential_stored_at is not None

    async def test_connect_sets_proxy_on_retry_when_fixie_url_configured(self) -> None:
        # New retry flow: proxy is only applied on the LAST attempt (attempt 5).
        # Simulate 429 on attempts 1-4, succeed on attempt 5 with proxy.
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Build a 429 response to trigger retries
        mock_429_response = MagicMock()
        mock_429_response.status_code = 429
        http_429 = requests.exceptions.HTTPError(response=mock_429_response)

        mock_garth_client_fail = MagicMock()
        mock_garth_client_fail.login.side_effect = http_429

        mock_garth_client_ok = MagicMock()
        mock_garth_client_ok.dumps.return_value = '{"oauth_token": "tok"}'

        from src.garmin.client_factory import FINGERPRINT_SEQUENCE

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.asyncio.sleep", new_callable=AsyncMock), \
             patch("src.api.routers.garmin_connect.random.uniform", return_value=35.0), \
             patch("src.api.routers.garmin_connect.cache"), \
             patch("src.api.routers.garmin_connect.client_cache"):
            # 4 failures then 1 success
            mock_factory.side_effect = [mock_garth_client_fail] * 4 + [mock_garth_client_ok]
            mock_settings.return_value.garmincoach_secret_key = "test-key"
            mock_settings.return_value.garmin_credential_key = "test-cred-key"
            mock_settings.return_value.fixie_url = "http://token@proxy.fixie.io:1234"

            await connect_garmin(request=request, current_user=user, session=mock_session)

        # Verify 5 calls total; only the last one uses the proxy
        assert mock_factory.call_count == 5
        for i, fp in enumerate(FINGERPRINT_SEQUENCE):
            call_kwargs = mock_factory.call_args_list[i][1]
            assert call_kwargs["fingerprint"] == fp
        # First 4: no proxy; last one: proxy
        for i in range(4):
            assert mock_factory.call_args_list[i][1]["proxy_url"] is None
        assert mock_factory.call_args_list[4][1]["proxy_url"] == "http://token@proxy.fixie.io:1234"

    async def test_connect_does_not_set_proxy_when_fixie_url_empty(self) -> None:
        # Arrange — no proxy configured, first attempt succeeds
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        mock_garth_client = MagicMock()
        mock_garth_client.dumps.return_value = '{"oauth_token": "tok"}'

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.cache"), \
             patch("src.api.routers.garmin_connect.client_cache"):
            mock_factory.return_value = mock_garth_client
            mock_settings.return_value.garmincoach_secret_key = "test-key"
            mock_settings.return_value.garmin_credential_key = "test-cred-key"
            mock_settings.return_value.fixie_url = ""

            await connect_garmin(request=request, current_user=user, session=mock_session)

        # Assert create_login_client was called with first fingerprint and no proxy
        mock_factory.assert_called_once_with(fingerprint="chrome136", proxy_url=None)

    async def test_connect_raises_503_on_proxy_error(self) -> None:
        # Arrange — attempts 1-4 get 429, attempt 5 (last, with proxy) gets ProxyError.
        # The proxy is only applied on the last attempt.
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()

        mock_429_response = MagicMock()
        mock_429_response.status_code = 429
        http_429 = requests.exceptions.HTTPError(response=mock_429_response)

        mock_garth_client_429 = MagicMock()
        mock_garth_client_429.login.side_effect = http_429

        mock_garth_client_proxy_fail = MagicMock()
        mock_garth_client_proxy_fail.login.side_effect = cffi_requests.exceptions.ProxyError("proxy down")

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.asyncio.sleep"), \
             patch("src.api.routers.garmin_connect.random.uniform", return_value=35.0):
            mock_factory.side_effect = [mock_garth_client_429] * 4 + [mock_garth_client_proxy_fail]
            mock_settings.return_value.fixie_url = "http://token@proxy.fixie.io:1234"

            with pytest.raises(HTTPException) as exc_info:
                await connect_garmin(request=request, current_user=user, session=mock_session)

        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail

    async def test_connect_uses_different_fingerprint_per_attempt(self) -> None:
        # All 5 attempts fail with 429; verify each attempt used the correct fingerprint.
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()

        resp_429 = MagicMock()
        resp_429.status_code = 429
        http_429 = requests.exceptions.HTTPError(response=resp_429)

        mock_garth_client = MagicMock()
        mock_garth_client.login.side_effect = http_429

        from src.garmin.client_factory import FINGERPRINT_SEQUENCE

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.asyncio.sleep"), \
             patch("src.api.routers.garmin_connect.random.uniform", return_value=35.0):
            mock_factory.return_value = mock_garth_client
            mock_settings.return_value.fixie_url = ""

            with pytest.raises(HTTPException):
                await connect_garmin(request=request, current_user=user, session=mock_session)

        assert mock_factory.call_count == 5
        for i, fp in enumerate(FINGERPRINT_SEQUENCE):
            assert mock_factory.call_args_list[i][1]["fingerprint"] == fp

    async def test_connect_delay_is_30_to_45_seconds_on_retry(self) -> None:
        # First attempt fails with 429; verify the delay before the retry is from random.uniform(30, 45).
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        resp_429 = MagicMock()
        resp_429.status_code = 429
        http_429 = requests.exceptions.HTTPError(response=resp_429)

        mock_garth_client_fail = MagicMock()
        mock_garth_client_fail.login.side_effect = http_429

        mock_garth_client_ok = MagicMock()
        mock_garth_client_ok.dumps.return_value = '{"oauth_token": "tok"}'

        with patch("src.api.routers.garmin_connect.create_login_client") as mock_factory, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.asyncio.sleep") as mock_sleep, \
             patch("src.api.routers.garmin_connect.random.uniform", return_value=42.5) as mock_uniform, \
             patch("src.api.routers.garmin_connect.cache"), \
             patch("src.api.routers.garmin_connect.client_cache"):
            mock_factory.side_effect = [mock_garth_client_fail, mock_garth_client_ok]
            mock_settings.return_value.garmincoach_secret_key = "test-key"
            mock_settings.return_value.garmin_credential_key = "test-cred-key"
            mock_settings.return_value.fixie_url = ""

            await connect_garmin(request=request, current_user=user, session=mock_session)

        mock_uniform.assert_called_once_with(30, 45)
        mock_sleep.assert_awaited_once_with(42.5)


# ---------------------------------------------------------------------------
# garmin_status
# ---------------------------------------------------------------------------


class TestGarminStatus:
    async def test_status_returns_true_when_profile_connected(self) -> None:
        # Arrange
        user = _make_user()
        mock_session = _make_session()
        profile = AthleteProfile(id=1, name="Runner", user_id=1, garmin_connected=True)
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = profile
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        result = await garmin_status(current_user=user, session=mock_session)

        # Assert
        assert result.connected is True

    async def test_status_returns_false_when_no_profile(self) -> None:
        # Arrange
        user = _make_user()
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        result = await garmin_status(current_user=user, session=mock_session)

        # Assert
        assert result.connected is False

    async def test_status_returns_false_when_profile_not_connected(self) -> None:
        # Arrange
        user = _make_user()
        mock_session = _make_session()
        profile = AthleteProfile(id=1, name="Runner", user_id=1, garmin_connected=False)
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = profile
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        result = await garmin_status(current_user=user, session=mock_session)

        # Assert
        assert result.connected is False

    async def test_status_credentials_stored_true_when_credentials_exist(self) -> None:
        # Arrange
        user = _make_user()
        mock_session = _make_session()
        profile = AthleteProfile(
            id=1, name="Runner", user_id=1,
            garmin_connected=True,
            garmin_credential_encrypted="encrypted-blob",
        )
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = profile
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        result = await garmin_status(current_user=user, session=mock_session)

        # Assert
        assert result.connected is True
        assert result.credentials_stored is True

    async def test_status_credentials_stored_false_when_no_credentials(self) -> None:
        # Arrange
        user = _make_user()
        mock_session = _make_session()
        profile = AthleteProfile(
            id=1, name="Runner", user_id=1,
            garmin_connected=True,
            garmin_credential_encrypted=None,
        )
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = profile
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        result = await garmin_status(current_user=user, session=mock_session)

        # Assert
        assert result.connected is True
        assert result.credentials_stored is False


# ---------------------------------------------------------------------------
# disconnect_garmin
# ---------------------------------------------------------------------------


class TestDisconnectGarmin:
    async def test_disconnect_clears_token_and_connected_flag(self) -> None:
        # Arrange
        user = _make_user()
        mock_session = _make_session()
        profile = AthleteProfile(
            id=1,
            name="Runner",
            user_id=1,
            garmin_connected=True,
            garmin_oauth_token_encrypted="encrypted-stuff",
            garmin_credential_encrypted="encrypted-cred",
        )
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = profile
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        with patch("src.api.routers.garmin_connect.cache"), \
             patch("src.api.routers.garmin_connect.client_cache"):
            result = await disconnect_garmin(current_user=user, session=mock_session)

        # Assert
        assert result.connected is False
        assert profile.garmin_connected is False
        assert profile.garmin_oauth_token_encrypted is None
        assert profile.garmin_credential_encrypted is None
        assert profile.garmin_credential_stored_at is None
        mock_session.add.assert_called_once_with(profile)
        mock_session.commit.assert_awaited_once()

    async def test_disconnect_returns_false_when_no_profile(self) -> None:
        # Arrange
        user = _make_user()
        mock_session = _make_session()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        result = await disconnect_garmin(current_user=user, session=mock_session)

        # Assert
        assert result.connected is False
        mock_session.add.assert_not_called()
