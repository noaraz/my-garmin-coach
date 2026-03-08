"""Tests for the /api/v1/garmin router using the mocked-auth conftest fixtures.

These tests use the standard `client` and `session` fixtures from conftest.py
which mock get_current_user as TEST_USER (id=1). This ensures pytest-cov
properly instruments the garmin_connect router code.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile


class TestGarminConnect:
    async def test_connect_success_returns_connected_true(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """POST /garmin/connect with valid garth login sets connected=True."""
        # Arrange
        mock_garth_client = MagicMock()
        mock_garth_client.dump.return_value = '{"oauth_token": "tok123"}'

        with patch("src.api.routers.garmin_connect.garth") as mock_garth:
            mock_garth.Client.return_value = mock_garth_client

            # Act
            resp = await client.post(
                "/api/v1/garmin/connect",
                json={"email": "g@example.com", "password": "pass"},
            )

        # Assert
        assert resp.status_code == 200
        assert resp.json()["connected"] is True

    async def test_connect_success_creates_profile_when_none_exists(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """POST /garmin/connect creates an AthleteProfile if the user has none."""
        # Arrange — no profile seeded
        mock_garth_client = MagicMock()
        mock_garth_client.dump.return_value = '{"oauth_token": "tok123"}'

        with patch("src.api.routers.garmin_connect.garth") as mock_garth:
            mock_garth.Client.return_value = mock_garth_client

            # Act
            resp = await client.post(
                "/api/v1/garmin/connect",
                json={"email": "g@example.com", "password": "pass"},
            )

        # Assert
        assert resp.status_code == 200
        # Profile should exist in DB now
        profile = (
            await session.exec(
                select(AthleteProfile).where(AthleteProfile.user_id == 1)
            )
        ).first()
        assert profile is not None
        assert profile.garmin_connected is True
        assert profile.garmin_oauth_token_encrypted is not None

    async def test_connect_success_uses_existing_profile(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """POST /garmin/connect reuses existing AthleteProfile."""
        # Arrange — seed a profile for test user (id=1)
        profile = AthleteProfile(name="Runner", user_id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        original_id = profile.id

        mock_garth_client = MagicMock()
        mock_garth_client.dump.return_value = '{"oauth_token": "tok"}'

        with patch("src.api.routers.garmin_connect.garth") as mock_garth:
            mock_garth.Client.return_value = mock_garth_client

            # Act
            resp = await client.post(
                "/api/v1/garmin/connect",
                json={"email": "g@example.com", "password": "pass"},
            )

        # Assert — same profile updated, not a new one created
        assert resp.status_code == 200
        profiles = (
            await session.exec(
                select(AthleteProfile).where(AthleteProfile.user_id == 1)
            )
        ).all()
        assert len(profiles) == 1
        assert profiles[0].id == original_id
        assert profiles[0].garmin_connected is True

    async def test_connect_failure_returns_400(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """POST /garmin/connect returns 400 when garth raises during login."""
        # Arrange
        mock_garth_client = MagicMock()
        mock_garth_client.login.side_effect = Exception("Bad credentials")

        with patch("src.api.routers.garmin_connect.garth") as mock_garth:
            mock_garth.Client.return_value = mock_garth_client

            # Act
            resp = await client.post(
                "/api/v1/garmin/connect",
                json={"email": "bad@example.com", "password": "wrong"},
            )

        # Assert
        assert resp.status_code == 400
        assert "Garmin authentication failed" in resp.json()["detail"]


class TestGarminStatus:
    async def test_status_when_not_connected_returns_false(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """GET /garmin/status returns connected=false when no profile exists."""
        # Act — no profile for test user
        resp = await client.get("/api/v1/garmin/status")

        # Assert
        assert resp.status_code == 200
        assert resp.json()["connected"] is False

    async def test_status_when_connected_returns_true(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """GET /garmin/status returns connected=true after connecting."""
        # Arrange — seed a connected profile
        profile = AthleteProfile(name="Runner", user_id=1, garmin_connected=True)
        session.add(profile)
        await session.commit()

        # Act
        resp = await client.get("/api/v1/garmin/status")

        # Assert
        assert resp.status_code == 200
        assert resp.json()["connected"] is True

    async def test_status_when_profile_exists_but_not_connected(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """GET /garmin/status returns connected=false when profile exists but garmin_connected=False."""
        # Arrange — profile exists but not connected
        profile = AthleteProfile(name="Runner", user_id=1, garmin_connected=False)
        session.add(profile)
        await session.commit()

        # Act
        resp = await client.get("/api/v1/garmin/status")

        # Assert
        assert resp.status_code == 200
        assert resp.json()["connected"] is False


class TestGarminDisconnect:
    async def test_disconnect_when_connected_clears_token(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """POST /garmin/disconnect clears garmin_connected and token."""
        # Arrange — seed a connected profile with a token
        profile = AthleteProfile(
            name="Runner",
            user_id=1,
            garmin_connected=True,
            garmin_oauth_token_encrypted="some-encrypted-token",
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        # Act
        resp = await client.post("/api/v1/garmin/disconnect")

        # Assert
        assert resp.status_code == 200
        assert resp.json()["connected"] is False

        # Verify DB
        await session.refresh(profile)
        assert profile.garmin_connected is False
        assert profile.garmin_oauth_token_encrypted is None

    async def test_disconnect_when_no_profile_returns_false(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """POST /garmin/disconnect is idempotent when no profile exists."""
        # Act — no profile exists
        resp = await client.post("/api/v1/garmin/disconnect")

        # Assert
        assert resp.status_code == 200
        assert resp.json()["connected"] is False
