from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.db.models import AthleteProfile
from src.garmin import auto_reconnect
from src.garmin.adapter_protocol import GarminAuthError, GarminConnectionError


def _make_session(profile: AthleteProfile | None = None) -> AsyncMock:
    """Create an AsyncMock session with profile query and SystemConfig lookup."""
    session = AsyncMock()
    session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.first.return_value = profile
    session.exec.return_value = mock_result
    # session.get(SystemConfig, "garmin_auth_version") → None (default v1)
    session.get.return_value = None
    return session


class TestAttemptAutoReconnect:
    async def test_returns_none_when_no_profile_exists(self):
        session = _make_session(profile=None)
        result = await auto_reconnect.attempt_auto_reconnect(1, session)
        assert result is None

    async def test_returns_none_when_no_credentials_stored(self):
        profile = AthleteProfile(
            user_id=1,
            garmin_credential_encrypted=None,
            garmin_credential_stored_at=None,
        )
        session = _make_session(profile)
        result = await auto_reconnect.attempt_auto_reconnect(1, session)
        assert result is None

    async def test_returns_none_when_credentials_expired(self):
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=31)
        profile = AthleteProfile(
            user_id=1,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        session = _make_session(profile)
        result = await auto_reconnect.attempt_auto_reconnect(1, session)
        assert result is None
        assert profile.garmin_credential_encrypted is None
        assert profile.garmin_credential_stored_at is None
        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_returns_none_when_on_cooldown(self):
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=1,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        session = _make_session(profile)

        with patch("src.garmin.auto_reconnect.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            auto_reconnect._cooldowns[1] = 1000.0 + 3600
            result = await auto_reconnect.attempt_auto_reconnect(1, session)

        assert result is None
        auto_reconnect._cooldowns.clear()

    async def test_returns_adapter_on_successful_reconnect(self):
        user_id = 1
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        session = _make_session(profile)

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"
        mock_settings.garmincoach_secret_key = "test-secret-key-32-chars-long!"

        mock_adapter = MagicMock()

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", return_value={"email": "test@example.com", "password": "my-password"}),
            patch("src.garmin.auto_reconnect.login_and_get_token", return_value='{"oauth_token": "fresh-token"}'),
            patch("src.garmin.auto_reconnect.encrypt_token", return_value="encrypted-fresh-token"),
            patch("src.garmin.auto_reconnect.create_adapter", return_value=mock_adapter),
            patch("src.garmin.auto_reconnect.cache") as mock_cache,
            patch("src.garmin.auto_reconnect.client_cache") as mock_client_cache,
        ):
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        assert result is mock_adapter
        assert profile.garmin_oauth_token_encrypted == "encrypted-fresh-token"
        assert profile.garmin_auth_version == "v1"
        session.add.assert_called()
        session.commit.assert_awaited_once()
        mock_cache.invalidate.assert_called_once_with(f"profile:{user_id}")
        mock_client_cache.invalidate.assert_called_once_with(user_id)
        mock_client_cache.put.assert_called_once_with(user_id, mock_adapter)

    async def test_clears_credentials_on_auth_error(self):
        user_id = 1
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        session = _make_session(profile)

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"
        mock_settings.garmincoach_secret_key = "test-secret-key-32-chars-long!"

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", return_value={"email": "test@example.com", "password": "bad-password"}),
            patch("src.garmin.auto_reconnect.login_and_get_token", side_effect=GarminAuthError("401 Unauthorized")),
        ):
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        assert result is None
        assert profile.garmin_credential_encrypted is None
        assert profile.garmin_credential_stored_at is None
        session.add.assert_called()
        session.commit.assert_awaited_once()
        assert user_id in auto_reconnect._cooldowns
        auto_reconnect._cooldowns.clear()

    async def test_clears_credentials_on_connection_error(self):
        user_id = 1
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        session = _make_session(profile)

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"
        mock_settings.garmincoach_secret_key = "test-secret-key-32-chars-long!"

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", return_value={"email": "test@example.com", "password": "bad-password"}),
            patch("src.garmin.auto_reconnect.login_and_get_token", side_effect=GarminConnectionError("Connection failed")),
        ):
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        assert result is None
        assert profile.garmin_credential_encrypted is None
        assert profile.garmin_credential_stored_at is None
        session.add.assert_called()
        session.commit.assert_awaited_once()
        assert user_id in auto_reconnect._cooldowns
        auto_reconnect._cooldowns.clear()

    async def test_keeps_credentials_on_generic_exception(self):
        user_id = 1
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        session = _make_session(profile)

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"
        mock_settings.garmincoach_secret_key = "test-secret-key-32-chars-long!"

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", return_value={"email": "test@example.com", "password": "my-password"}),
            patch("src.garmin.auto_reconnect.login_and_get_token", side_effect=ConnectionError("Network error")),
        ):
            result = await auto_reconnect.attempt_auto_reconnect(user_id, session)

        assert result is None
        # Credentials should NOT be cleared
        assert profile.garmin_credential_encrypted == "encrypted-blob"
        assert profile.garmin_credential_stored_at == stored_at
        assert user_id in auto_reconnect._cooldowns
        auto_reconnect._cooldowns.clear()

    async def test_no_credentials_in_logs_on_failure(self, caplog):
        """Security: verify that passwords/emails never appear in log output."""
        user_id = 1
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=user_id,
            garmin_credential_encrypted="encrypted-blob",
            garmin_credential_stored_at=stored_at,
        )
        session = _make_session(profile)

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"
        mock_settings.garmincoach_secret_key = "test-secret-key-32-chars-long!"

        secret_password = "super-secret-p4ssw0rd!"
        secret_email = "secret-user@garmin.com"

        with (
            caplog.at_level(logging.DEBUG, logger="src.garmin.auto_reconnect"),
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", return_value={"email": secret_email, "password": secret_password}),
            patch("src.garmin.auto_reconnect.login_and_get_token", side_effect=GarminAuthError("401")),
        ):
            await auto_reconnect.attempt_auto_reconnect(user_id, session)

        full_log = " ".join(caplog.messages)
        assert secret_password not in full_log, "Password leaked into logs!"
        assert secret_email not in full_log, "Email leaked into logs!"
        auto_reconnect._cooldowns.clear()

    async def test_clears_credentials_when_decrypt_fails(self):
        stored_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        profile = AthleteProfile(
            user_id=1,
            garmin_credential_encrypted="corrupted-blob",
            garmin_credential_stored_at=stored_at,
        )
        session = _make_session(profile)

        mock_settings = MagicMock()
        mock_settings.garmin_credential_key = "test-credential-key-32-chars!!"

        with (
            patch("src.garmin.auto_reconnect.get_settings", return_value=mock_settings),
            patch("src.garmin.auto_reconnect.decrypt_credential", side_effect=ValueError("Invalid token")),
        ):
            result = await auto_reconnect.attempt_auto_reconnect(1, session)

        assert result is None
        assert profile.garmin_credential_encrypted is None
        assert profile.garmin_credential_stored_at is None
        session.add.assert_called()
        session.commit.assert_awaited_once()
