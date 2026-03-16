from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.auth.models import InviteCode, User
from src.core.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Fake Google idinfo returned by the mock
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
# Override settings to enable google_client_id
# ---------------------------------------------------------------------------

_test_settings = Settings(
    database_url="sqlite+aiosqlite:///:memory:",
    google_client_id="test-google-client-id.apps.googleusercontent.com",
    bootstrap_secret="dev-bootstrap-secret-change-in-prod",
)

_test_settings_no_google = Settings(
    database_url="sqlite+aiosqlite:///:memory:",
    google_client_id="",
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


@pytest.fixture(name="ga_client_no_google")
async def ga_client_no_google_fixture(
    ga_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with google_client_id empty (Google OAuth not configured)."""
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield ga_session

    app.dependency_overrides[get_session] = override_session

    with patch("src.auth.service.get_settings", return_value=_test_settings_no_google), \
         patch("src.core.config.get_settings", return_value=_test_settings_no_google):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /auth/google — error paths
# ---------------------------------------------------------------------------


class TestGoogleAuthEndpoint:
    async def test_google_auth_returns_503_when_client_id_empty(
        self, ga_client_no_google: AsyncClient
    ) -> None:
        """POST /auth/google returns 503 when google_client_id is not configured."""
        resp = await ga_client_no_google.post(
            "/api/v1/auth/google",
            json={"id_token": "some.fake.token"},
        )
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()

    @patch("src.auth.service.id_token.verify_oauth2_token", side_effect=ValueError("Bad token"))
    async def test_google_auth_returns_401_for_invalid_token(
        self, mock_verify: object, ga_client: AsyncClient
    ) -> None:
        """POST /auth/google returns 401 when Google token verification fails."""
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"id_token": "invalid.google.token"},
        )
        assert resp.status_code == 401
        assert "invalid google token" in resp.json()["detail"].lower()

    @patch("src.auth.service.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_IDINFO)
    async def test_google_auth_returns_403_for_unknown_user_no_invite(
        self, mock_verify: object, ga_client: AsyncClient
    ) -> None:
        """POST /auth/google returns 403 for unknown user without invite code."""
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"id_token": "valid.google.token"},
        )
        assert resp.status_code == 403
        assert "invite" in resp.json()["detail"].lower()

    @patch("src.auth.service.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_IDINFO)
    async def test_google_auth_returns_tokens_for_existing_user(
        self, mock_verify: object, ga_client: AsyncClient, ga_session: AsyncSession
    ) -> None:
        """POST /auth/google returns tokens when user already exists."""
        # Arrange — create existing user
        user = User(
            email="googleuser@gmail.com",
            google_oauth_sub="google-uid-123",
        )
        ga_session.add(user)
        await ga_session.commit()

        # Act
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"id_token": "valid.google.token"},
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    @patch("src.auth.service.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_IDINFO)
    async def test_google_auth_links_google_sub_to_existing_email_user(
        self, mock_verify: object, ga_client: AsyncClient, ga_session: AsyncSession
    ) -> None:
        """If user exists by email but has no google_oauth_sub, link it."""
        # Arrange — user exists with email only (e.g. previously password-based)
        user = User(
            email="googleuser@gmail.com",
            password_hash="old-hash",
            google_oauth_sub=None,
        )
        ga_session.add(user)
        await ga_session.commit()
        await ga_session.refresh(user)

        # Act
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"id_token": "valid.google.token"},
        )

        # Assert — should succeed and link google sub
        assert resp.status_code == 200
        await ga_session.refresh(user)
        assert user.google_oauth_sub == "google-uid-123"

    @patch("src.auth.service.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_IDINFO_2)
    async def test_google_auth_creates_user_with_valid_invite(
        self, mock_verify: object, ga_client: AsyncClient, ga_session: AsyncSession
    ) -> None:
        """POST /auth/google with valid invite creates a new user."""
        # Arrange — need an admin to own the invite code
        admin = User(email="admin@example.com", is_admin=True)
        ga_session.add(admin)
        await ga_session.commit()
        await ga_session.refresh(admin)

        invite = InviteCode(code="GOOGLE-INVITE-001", created_by=admin.id)
        ga_session.add(invite)
        await ga_session.commit()

        # Act
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"id_token": "valid.google.token", "invite_code": "GOOGLE-INVITE-001"},
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    @patch("src.auth.service.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_IDINFO_2)
    async def test_google_auth_rejects_invalid_invite(
        self, mock_verify: object, ga_client: AsyncClient
    ) -> None:
        """POST /auth/google with invalid invite code returns 403."""
        resp = await ga_client.post(
            "/api/v1/auth/google",
            json={"id_token": "valid.google.token", "invite_code": "BAD-CODE"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /auth/bootstrap — Google OAuth version
# ---------------------------------------------------------------------------


class TestBootstrapGoogleOAuth:
    async def test_bootstrap_returns_403_on_wrong_setup_token(
        self, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": "wrong-token",
                "google_id_token": "some.google.jwt",
            },
        )
        assert resp.status_code == 403

    async def test_bootstrap_returns_409_when_users_exist(
        self, ga_client: AsyncClient, ga_session: AsyncSession
    ) -> None:
        # Arrange — create an existing user
        ga_session.add(User(email="existing@example.com"))
        await ga_session.commit()

        resp = await ga_client.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": _test_settings.bootstrap_secret,
                "google_id_token": "some.google.jwt",
            },
        )
        assert resp.status_code == 409

    async def test_bootstrap_returns_503_when_google_not_configured(
        self, ga_client_no_google: AsyncClient
    ) -> None:
        resp = await ga_client_no_google.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": _test_settings_no_google.bootstrap_secret,
                "google_id_token": "some.google.jwt",
            },
        )
        assert resp.status_code == 503

    @patch("src.auth.service.id_token.verify_oauth2_token", side_effect=ValueError("Bad token"))
    async def test_bootstrap_returns_401_for_invalid_google_token(
        self, mock_verify: object, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": _test_settings.bootstrap_secret,
                "google_id_token": "invalid.token",
            },
        )
        assert resp.status_code == 401

    @patch("src.auth.service.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_IDINFO)
    async def test_bootstrap_creates_admin_and_invites(
        self, mock_verify: object, ga_client: AsyncClient
    ) -> None:
        resp = await ga_client.post(
            "/api/v1/auth/bootstrap",
            json={
                "setup_token": _test_settings.bootstrap_secret,
                "google_id_token": "valid.google.token",
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
        # 404 (path not found) or 405 (method not allowed)
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
