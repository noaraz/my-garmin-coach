from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.auth.models import InviteCode, User
from src.core.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Test settings with Google OAuth configured
# ---------------------------------------------------------------------------

_test_settings = Settings(
    environment="testing",
    database_url="sqlite+aiosqlite:///:memory:",
    google_client_id="test-google-client-id.apps.googleusercontent.com",
    bootstrap_secret="dev-bootstrap-secret-change-in-prod",
)

FAKE_GOOGLE_USER_A = {
    "sub": "google-uid-aaa",
    "email": "usera@example.com",
    "email_verified": True,
}

FAKE_GOOGLE_USER_B = {
    "sub": "google-uid-bbb",
    "email": "userb@example.com",
    "email_verified": True,
}

FAKE_GOOGLE_ADMIN = {
    "sub": "google-uid-admin",
    "email": "admin@example.com",
    "email_verified": True,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="auth_session")
async def auth_session_fixture() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session_factory = sessionmaker(  # type: ignore[call-overload]
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture(name="auth_client")
async def auth_client_fixture(
    auth_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated client wired to auth_session with Google OAuth enabled."""
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield auth_session

    app.dependency_overrides[get_session] = override_session

    with patch("src.auth.service.get_settings", return_value=_test_settings), \
         patch("src.core.config.get_settings", return_value=_test_settings):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.fixture(name="invite_code")
async def invite_code_fixture(auth_session: AsyncSession) -> str:
    """Create a first user (admin) and an unused invite code, return the code string."""
    admin = User(
        email="admin@example.com",
        google_oauth_sub="google-uid-admin",
        is_admin=True,
    )
    auth_session.add(admin)
    await auth_session.commit()
    await auth_session.refresh(admin)

    code = InviteCode(code="VALID-INVITE-001", created_by=admin.id)
    auth_session.add(code)
    await auth_session.commit()

    return "VALID-INVITE-001"


async def _google_auth(
    client: AsyncClient,
    google_idinfo: dict,
    invite_code: str | None = None,
) -> object:
    """Helper: authenticate via Google OAuth (mocking the userinfo call)."""
    payload = {"access_token": "fake.google.access.token"}
    if invite_code:
        payload["invite_code"] = invite_code

    with patch(
        "src.auth.service._google_userinfo",
        return_value=google_idinfo,
    ):
        resp = await client.post("/api/v1/auth/google", json=payload)
    return resp


# ---------------------------------------------------------------------------
# Protected route tests (using Google OAuth to obtain tokens)
# ---------------------------------------------------------------------------


async def test_protected_with_token(
    auth_client: AsyncClient, invite_code: str
) -> None:
    # Arrange — register via Google OAuth with invite
    resp = await _google_auth(auth_client, FAKE_GOOGLE_USER_A, invite_code)
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "usera@example.com"
    assert "id" in body
    assert "is_active" in body


async def test_protected_no_token(auth_client: AsyncClient) -> None:
    # Act
    resp = await auth_client.get("/api/v1/auth/me")

    # Assert
    assert resp.status_code == 401


async def test_protected_expired(auth_client: AsyncClient) -> None:
    # Arrange — build an expired token manually
    settings = get_settings()
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": "999", "type": "access", "exp": expire}
    expired_token = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    # Assert
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh token test
# ---------------------------------------------------------------------------


async def test_refresh_token(
    auth_client: AsyncClient, invite_code: str
) -> None:
    # Arrange — authenticate via Google
    resp = await _google_auth(auth_client, FAKE_GOOGLE_USER_A, invite_code)
    refresh_tok = resp.json()["refresh_token"]

    # Act
    resp = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok},
    )

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


# ---------------------------------------------------------------------------
# Data isolation test
# ---------------------------------------------------------------------------


async def test_user_data_isolation(
    auth_session: AsyncSession, auth_client: AsyncClient, invite_code: str
) -> None:
    """User A and User B see different /me responses."""
    # Arrange — register User A with existing invite
    resp_a = await _google_auth(auth_client, FAKE_GOOGLE_USER_A, invite_code)
    assert resp_a.status_code == 200
    token_a = resp_a.json()["access_token"]

    # Create a second invite from the admin
    admin = (
        await auth_session.exec(
            select(User).where(User.email == "admin@example.com")
        )
    ).first()
    invite2 = InviteCode(code="INVITE-B-002", created_by=admin.id)
    auth_session.add(invite2)
    await auth_session.commit()

    resp_b = await _google_auth(auth_client, FAKE_GOOGLE_USER_B, "INVITE-B-002")
    assert resp_b.status_code == 200
    token_b = resp_b.json()["access_token"]

    # Act — each user fetches /me
    me_a = await auth_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"}
    )
    me_b = await auth_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"}
    )

    # Assert — they see different users
    assert me_a.json()["email"] == "usera@example.com"
    assert me_b.json()["email"] == "userb@example.com"
    assert me_a.json()["id"] != me_b.json()["id"]


# ---------------------------------------------------------------------------
# auth/dependencies.py error paths (get_current_user 401 branches)
# ---------------------------------------------------------------------------


async def test_protected_with_wrong_token_type(
    auth_client: AsyncClient, invite_code: str
) -> None:
    """A refresh token (type=refresh) must be rejected by protected routes."""
    # Arrange — authenticate to get tokens
    resp = await _google_auth(auth_client, FAKE_GOOGLE_USER_A, invite_code)
    refresh_tok = resp.json()["refresh_token"]

    # Act — try to access protected route with refresh token
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_tok}"},
    )

    # Assert
    assert resp.status_code == 401


async def test_protected_with_non_integer_sub(auth_client: AsyncClient) -> None:
    """A JWT with non-integer 'sub' claim must be rejected."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": "not-an-int", "type": "access", "exp": expire}
    bad_token = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert resp.status_code == 401


async def test_protected_with_unknown_user_id(auth_client: AsyncClient) -> None:
    """A JWT for a non-existent user_id must be rejected."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": "99999", "type": "access", "exp": expire}
    ghost_token = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {ghost_token}"},
    )
    assert resp.status_code == 401


async def test_protected_with_invalid_jwt_signature(
    auth_client: AsyncClient,
) -> None:
    """A token signed with the wrong secret must be rejected."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": "1", "type": "access", "exp": expire}
    bad_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert resp.status_code == 401


async def test_protected_with_missing_sub_claim(auth_client: AsyncClient) -> None:
    """A JWT with no 'sub' claim must be rejected."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"type": "access", "exp": expire}
    no_sub_token = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {no_sub_token}"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Bootstrap tests
# ---------------------------------------------------------------------------


async def test_bootstrap_rejects_missing_google_access_token(
    auth_client: AsyncClient,
) -> None:
    """Bootstrap with old email+password fields is rejected (422 -- wrong schema)."""
    resp = await auth_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "setup_token": _test_settings.bootstrap_secret,
            "email": "admin@example.com",
            "password": "adminpassword",
        },
    )
    assert resp.status_code == 422


async def test_bootstrap_returns_403_on_wrong_token(
    auth_client: AsyncClient,
) -> None:
    resp = await auth_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "setup_token": "wrong-token",
            "google_access_token": "some.google.jwt",
        },
    )
    assert resp.status_code == 403


async def test_bootstrap_returns_409_when_users_exist(
    auth_client: AsyncClient,
    invite_code: str,  # fixture creates a user
) -> None:
    """Bootstrap returns 409 when a user already exists."""
    resp = await auth_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "setup_token": _test_settings.bootstrap_secret,
            "google_access_token": "some.google.jwt",
        },
    )
    assert resp.status_code == 409


async def test_me_includes_is_admin(
    auth_client: AsyncClient,
    invite_code: str,
) -> None:
    """Admin user created via fixture has is_admin=True visible on /me."""
    # The admin already exists from the invite_code fixture. Authenticate as admin.
    resp = await _google_auth(auth_client, FAKE_GOOGLE_ADMIN)
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_admin"] is True


async def test_invite_blocked_for_non_admin(
    auth_client: AsyncClient,
    invite_code: str,
) -> None:
    # Arrange — register a normal (non-admin) user via Google OAuth
    resp = await _google_auth(auth_client, FAKE_GOOGLE_USER_A, invite_code)
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # Act — try to create an invite as non-admin
    resp = await auth_client.post(
        "/api/v1/auth/invite",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert
    assert resp.status_code == 403
