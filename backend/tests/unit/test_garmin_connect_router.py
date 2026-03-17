"""Unit tests for the garmin_connect router functions.

These tests call the route handler functions directly (not via HTTP)
to ensure pytest-cov properly instruments the async function bodies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import requests
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
    return User(id=user_id, email="test@example.com", password_hash="x", is_active=True)


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

        with patch("src.api.routers.garmin_connect.garth") as mock_garth, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings:
            mock_garth.Client.return_value = mock_garth_client
            mock_settings.return_value.garmincoach_secret_key = "test-key"

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

        with patch("src.api.routers.garmin_connect.garth") as mock_garth, \
             patch("src.api.routers.garmin_connect.get_settings"):
            mock_garth.Client.return_value = mock_garth_client

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

        with patch("src.api.routers.garmin_connect.garth") as mock_garth, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings, \
             patch("src.api.routers.garmin_connect.asyncio.sleep") as mock_sleep:
            mock_garth.Client.side_effect = [mock_garth_client_fail, mock_garth_client_ok]
            mock_settings.return_value.garmincoach_secret_key = "test-key"

            result = await connect_garmin(
                request=request,
                current_user=user,
                session=mock_session,
            )

        assert result.connected is True
        mock_sleep.assert_awaited_once_with(3)

    async def test_connect_raises_503_when_both_attempts_rate_limited(self) -> None:
        # Arrange — both attempts get 429
        user = _make_user()
        request = GarminConnectRequest(email="g@example.com", password="pass")
        mock_session = _make_session()

        resp_429 = MagicMock()
        resp_429.status_code = 429
        http_429 = requests.exceptions.HTTPError(response=resp_429)

        mock_garth_client = MagicMock()
        mock_garth_client.login.side_effect = http_429

        with patch("src.api.routers.garmin_connect.garth") as mock_garth, \
             patch("src.api.routers.garmin_connect.get_settings"), \
             patch("src.api.routers.garmin_connect.asyncio.sleep"):
            mock_garth.Client.return_value = mock_garth_client

            with pytest.raises(HTTPException) as exc_info:
                await connect_garmin(
                    request=request,
                    current_user=user,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 503
        assert "rate-limiting" in exc_info.value.detail

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

        with patch("src.api.routers.garmin_connect.garth") as mock_garth, \
             patch("src.api.routers.garmin_connect.get_settings") as mock_settings:
            mock_garth.Client.return_value = mock_garth_client
            mock_settings.return_value.garmincoach_secret_key = "test-key"

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
        )
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = profile
        mock_session.exec = AsyncMock(return_value=mock_exec_result)

        # Act
        result = await disconnect_garmin(current_user=user, session=mock_session)

        # Assert
        assert result.connected is False
        assert profile.garmin_connected is False
        assert profile.garmin_oauth_token_encrypted is None
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
