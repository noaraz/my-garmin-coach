from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import requests
from garth.exc import GarthHTTPError

from src.db.models import AthleteProfile
from src.garmin import auto_reconnect


class TestAttemptAutoReconnect:
    async def test_returns_none_when_no_profile_exists(self):
        # Arrange
        user_id = 1
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        session.exec.return_value = mock_result

        # Act
        result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        # Assert
        assert result is None

    async def test_returns_none_when_no_credentials_stored(self):
        # Arrange
        user_id = 1
        session = AsyncMock()
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted=None,
            garmin_credential_stored_at=None,
        )
        mock_result = MagicMock()
        mock_result.first.return_value = profile
        session.exec.return_value = mock_result

        # Act
        result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        # Assert
        assert result is None

    async def test_returns_none_when_credentials_expired(self):
        # Arrange
        user_id = 1
        session = AsyncMock()
        session.add = MagicMock()
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=31)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        mock_result = MagicMock()
        mock_result.first.return_value = profile
        session.exec.return_value = mock_result

        # Act
        result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        # Assert
        assert result is None
        # Credentials should be cleared
        assert profile.garmin_credential_encrypted is None
        assert profile.garmin_credential_stored_at is None
        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_returns_none_when_on_cooldown(self):
        # Arrange
        user_id = 1
        session = AsyncMock()
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        mock_result = MagicMock()
        mock_result.first.return_value = profile
        session.exec.return_value = mock_result

        # Set cooldown manually
        with patch("src.garmin.auto_reconnect.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            auto_reconnect._cooldowns[user_id] = 1000.0 + 3600  # 1hr from now

            # Act
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        # Assert
        assert result is None

        # Cleanup
        auto_reconnect._cooldowns.clear()

    async def test_returns_adapter_on_successful_reconnect(self):
        # Arrange
        user_id = 1
        session = AsyncMock()
        session.add = MagicMock()
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        mock_result = MagicMock()
        mock_result.first.return_value = profile
        session.exec.return_value = mock_result

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"
        mock_settings.garmincoach_secret_key = "test-secret-key-32-chars-long!"

        mock_client = MagicMock()
        mock_client.login = MagicMock()
        mock_client.dumps.return_value = '{"oauth_token": "fresh-token"}'

        mock_adapter = MagicMock()

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", return_value={"email": "test@example.com", "password": "my-password"}),
            patch("src.garmin.auto_reconnect.create_login_client", return_value=mock_client),
            patch("src.garmin.auto_reconnect.encrypt_token", return_value="encrypted-fresh-token"),
            patch("src.garmin.auto_reconnect.create_api_client", return_value=mock_adapter),
            patch("src.garmin.auto_reconnect.cache") as mock_cache,
            patch("src.garmin.auto_reconnect.client_cache") as mock_client_cache,
        ):
            # Act
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        # Assert
        assert result is mock_adapter
        mock_client.login.assert_called_once_with("test@example.com", "my-password")
        assert profile.garmin_oauth_token_encrypted == "encrypted-fresh-token"
        session.add.assert_called()
        session.commit.assert_awaited_once()
        mock_cache.invalidate.assert_called_once_with(f"profile:{user_id}")
        mock_client_cache.invalidate.assert_called_once_with(user_id)
        mock_client_cache.put.assert_called_once_with(user_id, mock_adapter)

    async def test_clears_credentials_on_garth_http_error(self):
        # Arrange
        user_id = 1
        session = AsyncMock()
        session.add = MagicMock()
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        mock_result = MagicMock()
        mock_result.first.return_value = profile
        session.exec.return_value = mock_result

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"
        mock_settings.garmincoach_secret_key = "test-secret-key-32-chars-long!"

        # Create a proper GarthHTTPError with HTTPError
        mock_response = MagicMock()
        mock_response.status_code = 401
        http_error = requests.exceptions.HTTPError("401 Unauthorized", response=mock_response)

        mock_client = MagicMock()
        mock_client.login.side_effect = GarthHTTPError("401 Unauthorized", http_error)

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", return_value={"email": "test@example.com", "password": "bad-password"}),
            patch("src.garmin.auto_reconnect.create_login_client", return_value=mock_client),
        ):
            # Act
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        # Assert
        assert result is None
        assert profile.garmin_credential_encrypted is None
        assert profile.garmin_credential_stored_at is None
        session.add.assert_called()
        session.commit.assert_awaited_once()
        # 1hr cooldown should be set
        assert user_id in auto_reconnect._cooldowns

        # Cleanup
        auto_reconnect._cooldowns.clear()

    async def test_keeps_credentials_on_generic_exception(self):
        # Arrange
        user_id = 1
        session = AsyncMock()
        session.add = MagicMock()
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        mock_result = MagicMock()
        mock_result.first.return_value = profile
        session.exec.return_value = mock_result

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"
        mock_settings.garmincoach_secret_key = "test-secret-key-32-chars-long!"

        mock_client = MagicMock()
        mock_client.login.side_effect = ConnectionError("Network error")

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", return_value={"email": "test@example.com", "password": "my-password"}),
            patch("src.garmin.auto_reconnect.create_login_client", return_value=mock_client),
        ):
            # Act
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        # Assert
        assert result is None
        # Credentials should NOT be cleared
        assert profile.garmin_credential_encrypted == "encrypted-blob"
        assert profile.garmin_credential_stored_at == stored_at
        # 15min cooldown should be set
        assert user_id in auto_reconnect._cooldowns

        # Cleanup
        auto_reconnect._cooldowns.clear()

    async def test_clears_credentials_when_decrypt_fails(self):
        # Arrange
        user_id = 1
        session = AsyncMock()
        session.add = MagicMock()
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="corrupted-blob",
            garmin_credential_stored_at=stored_at,
        )
        mock_result = MagicMock()
        mock_result.first.return_value = profile
        session.exec.return_value = mock_result

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", side_effect=ValueError("Invalid token")),
        ):
            # Act
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        # Assert
        assert result is None
        assert profile.garmin_credential_encrypted is None
        assert profile.garmin_credential_stored_at is None
        session.add.assert_called()
        session.commit.assert_awaited_once()
