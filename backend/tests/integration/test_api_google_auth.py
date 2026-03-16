from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.auth.models import InviteCode, User
from src.core.config import Settings

# ---------------------------------------------------------------------------
# Fake Google userinfo returned by the mock
# ---------------------------------------------------------------------------

FAKE_GOOGLE_IDINFO = {
    "sub": "google-uid-123",
    "email": "googleuser@gmail.com",
    "email_verified": True,
}

FAKE_GOOGLE_IDINFO_2 = {
    "sub": "google-uid-456",
    "email": "newuser@gmail.com",
    "email_verified": True,
}

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

_test_settings = Settings(
    database_url="sqlite+aiosqlite:///:memory:",
    google_client_id="test-google-client-id.apps.googleusercontent.com",
    bootstrap_secret="dev-bootstrap-secret-change-in-prod",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="ga_session")
async def ga_session_fixture() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session_factory = sessionmaker(  # type: ignore[call-overload]
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture(name="ga_client")
async def ga_client_fixture(
    ga_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield ga_session

    app.dependency_overrides[get_session] = override_session

    with patch("src.auth.service.get_settings", return_value=_test_settings), \
         patch("src.core.config.get_settings", return_value=_test_settings):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /auth/google
# ---------------------------------------------------------------------------


class TestGoogleAuthEndpoint:
    @patch(
        "src.auth.service._google_userinfo",
        side_effect=HTTPException(status_code=401, detail="Invalid Google access token"),
    )
    async def test_google_auth_returns_401_for_invalid_token(
        self, _mock: object, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"access_token": "invalid.google.token"},
        )
        assert resp.status_code == 401
        assert "invalid google" in resp.json()["detail"].lower()

    @patch(
        "src.auth.service._google_userinfo",
        side_effect=HTTPException(
            status_code=401, detail="Google account email is not verified"
        ),
    )
    async def test_google_auth_returns_401_for_unverified_email(
        self, _mock: object, ga_client: AsyncClient
    ) -> None:
        """Google accounts with unverified emails are rejected."""
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"access_token": "unverified.google.token"},
        )
        assert resp.status_code == 401
        assert "verified" in resp.json()["detail"].lower()

    @patch("src.auth.service._google_userinfo", return_value=FAKE_GOOGLE_IDINFO)
    async def test_google_auth_returns_403_for_unknown_user_no_invite(
        self, _mock: object, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"access_token": "valid.google.token"},
        )
        assert resp.status_code == 403
        assert "invite" in resp.json()["detail"].lower()

    @patch("src.auth.service._google_userinfo", return_value=FAKE_GOOGLE_IDINFO)
    async def test_google_auth_returns_tokens_for_existing_user(
        self, _mock: object, ga_client: AsyncClient, ga_session: AsyncSession
    ) -> None:
        user = User(email="googleuser@gmail.com", google_oauth_sub="google-uid-123")
        ga_session.add(user)
        await ga_session.commit()

        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"access_token": "valid.google.token"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    @patch("src.auth.service._google_userinfo", return_value=FAKE_GOOGLE_IDINFO)
    async def test_google_auth_does_not_grant_access_by_email_alone(
        self, _mock: object, ga_client: AsyncClient, ga_session: AsyncSession
    ) -> None:
        """A Google account with matching email but different sub must not access an existing account."""
        # Existing user has a different google_sub than the token presents
        user = User(email="googleuser@gmail.com", google_oauth_sub="different-sub-original")
        ga_session.add(user)
        await ga_session.commit()

        # FAKE_GOOGLE_IDINFO has sub="google-uid-123" — doesn't match "different-sub-original"
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"access_token": "valid.google.token"},
        )
        # No sub match → not found → 403 (no invite code provided)
        assert resp.status_code == 403

    @patch("src.auth.service._google_userinfo", return_value=FAKE_GOOGLE_IDINFO_2)
    async def test_google_auth_creates_user_with_valid_invite(
        self, _mock: object, ga_client: AsyncClient, ga_session: AsyncSession
    ) -> None:
        admin = User(email="admin@example.com", is_admin=True)
        ga_session.add(admin)
        await ga_session.commit()
        await ga_session.refresh(admin)

        invite = InviteCode(code="GOOGLE-INVITE-001", created_by=admin.id)
        ga_session.add(invite)
        await ga_session.commit()

        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"access_token": "valid.google.token", "invite_code": "GOOGLE-INVITE-001"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    @patch("src.auth.service._google_userinfo", return_value=FAKE_GOOGLE_IDINFO_2)
    async def test_google_auth_rejects_invalid_invite(
        self, _mock: object, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"access_token": "valid.google.token", "invite_code": "BAD-CODE"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /auth/bootstrap
# ---------------------------------------------------------------------------


class TestBootstrapGoogleOAuth:
    async def test_bootstrap_returns_403_on_wrong_setup_token(
        self, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": "wrong-token",
                "google_access_token": "some.google.token",
            },
        )
        assert resp.status_code == 403

    async def test_bootstrap_returns_409_when_users_exist(
        self, ga_client: AsyncClient, ga_session: AsyncSession
    ) -> None:
        ga_session.add(User(email="existing@example.com"))
        await ga_session.commit()

        resp = await ga_client.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": _test_settings.bootstrap_secret,
                "google_access_token": "some.google.token",
            },
        )
        assert resp.status_code == 409

    @patch(
        "src.auth.service._google_userinfo",
        side_effect=HTTPException(status_code=401, detail="Invalid Google access token"),
    )
    async def test_bootstrap_returns_401_for_invalid_google_token(
        self, _mock: object, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": _test_settings.bootstrap_secret,
                "google_access_token": "invalid.token",
            },
        )
        assert resp.status_code == 401

    @patch("src.auth.service._google_userinfo", return_value=FAKE_GOOGLE_IDINFO)
    async def test_bootstrap_creates_admin_and_invites(
        self, _mock: object, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": _test_settings.bootstrap_secret,
                "google_access_token": "valid.google.token",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "invite_codes" in body
        assert len(body["invite_codes"]) == 5


# ---------------------------------------------------------------------------
# Removed endpoints — /login and /register should 404 or 405
# ---------------------------------------------------------------------------


class TestRemovedEndpoints:
    async def test_login_endpoint_removed(self, ga_client: AsyncClient) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert resp.status_code in (404, 405)

    async def test_register_endpoint_removed(self, ga_client: AsyncClient) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "invite_code": "SOME-CODE",
            },
        )
        assert resp.status_code in (404, 405)
