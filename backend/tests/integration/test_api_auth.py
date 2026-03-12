from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

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
from src.core.config import get_settings


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
    """Plain unauthenticated client wired to auth_session."""
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield auth_session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(name="invite_code")
async def invite_code_fixture(auth_session: AsyncSession) -> str:
    """Create a first user (admin) and an unused invite code, return the code string."""
    from src.auth.passwords import hash_password

    admin = User(
        email="admin@example.com",
        password_hash=hash_password("adminpassword"),
    )
    auth_session.add(admin)
    await auth_session.commit()
    await auth_session.refresh(admin)

    code = InviteCode(code="VALID-INVITE-001", created_by=admin.id)
    auth_session.add(code)
    await auth_session.commit()

    return "VALID-INVITE-001"


async def _register_user(
    client: AsyncClient,
    email: str,
    password: str,
    invite_code: str,
) -> dict:
    """Helper: register a user and return the response body."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "invite_code": invite_code},
    )
    return resp


async def _login_user(
    client: AsyncClient,
    email: str,
    password: str,
) -> dict:
    """Helper: login and return the response."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return resp


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


async def test_register_new_user(auth_client: AsyncClient, invite_code: str) -> None:
    # Arrange / Act
    resp = await _register_user(auth_client, "user@example.com", "password123", invite_code)

    # Assert
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "user@example.com"
    assert "id" in body


async def test_register_duplicate_email(
    auth_client: AsyncClient, invite_code: str
) -> None:
    # Arrange — first registration
    await _register_user(auth_client, "dup@example.com", "password123", invite_code)

    # Create a second invite code

    # Act — attempt duplicate
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password123", "invite_code": invite_code},
    )

    # Assert
    assert resp.status_code == 409


async def test_register_invalid_invite(auth_client: AsyncClient) -> None:
    # Act
    resp = await _register_user(auth_client, "user@example.com", "password123", "BAD-CODE")

    # Assert
    assert resp.status_code == 403


async def test_register_weak_password(auth_client: AsyncClient, invite_code: str) -> None:
    # Act
    resp = await _register_user(auth_client, "user@example.com", "short", invite_code)

    # Assert
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


async def test_login_success(auth_client: AsyncClient, invite_code: str) -> None:
    # Arrange
    await _register_user(auth_client, "user@example.com", "password123", invite_code)

    # Act
    resp = await _login_user(auth_client, "user@example.com", "password123")

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(auth_client: AsyncClient, invite_code: str) -> None:
    # Arrange
    await _register_user(auth_client, "user@example.com", "password123", invite_code)

    # Act
    resp = await _login_user(auth_client, "user@example.com", "wrongpassword")

    # Assert
    assert resp.status_code == 401


async def test_login_nonexistent_user(auth_client: AsyncClient) -> None:
    # Act
    resp = await _login_user(auth_client, "nobody@example.com", "password123")

    # Assert
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Protected route tests
# ---------------------------------------------------------------------------


async def test_protected_with_token(auth_client: AsyncClient, invite_code: str) -> None:
    # Arrange
    await _register_user(auth_client, "user@example.com", "password123", invite_code)
    login_resp = await _login_user(auth_client, "user@example.com", "password123")
    token = login_resp.json()["access_token"]

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "user@example.com"
    assert "id" in body
    assert "is_active" in body


async def test_protected_no_token(auth_client: AsyncClient) -> None:
    # Act
    resp = await auth_client.get("/api/v1/auth/me")

    # Assert
    assert resp.status_code == 401


async def test_protected_expired(auth_client: AsyncClient, invite_code: str) -> None:
    # Arrange — create a user so we have a valid user_id
    await _register_user(auth_client, "user@example.com", "password123", invite_code)
    settings = get_settings()

    # Build an expired token manually
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": "999", "type": "access", "exp": expire}
    expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

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


async def test_refresh_token(auth_client: AsyncClient, invite_code: str) -> None:
    # Arrange
    await _register_user(auth_client, "user@example.com", "password123", invite_code)
    login_resp = await _login_user(auth_client, "user@example.com", "password123")
    refresh_token = login_resp.json()["refresh_token"]

    # Act
    resp = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
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
    """User A's invite creates only User A; User B registers separately with own invite."""

    # Arrange — register User A with the existing invite
    await _register_user(auth_client, "usera@example.com", "passwordAAA", invite_code)

    # Create a second invite from the admin
    admin = (await auth_session.exec(select(User).where(User.email == "admin@example.com"))).first()
    invite2 = InviteCode(code="INVITE-B-002", created_by=admin.id)
    auth_session.add(invite2)
    await auth_session.commit()

    await _register_user(auth_client, "userb@example.com", "passwordBBB", "INVITE-B-002")

    # Log in as User A
    login_a = await _login_user(auth_client, "usera@example.com", "passwordAAA")
    token_a = login_a.json()["access_token"]

    # Log in as User B
    login_b = await _login_user(auth_client, "userb@example.com", "passwordBBB")
    token_b = login_b.json()["access_token"]

    # Act — each user fetches /me
    me_a = await auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    me_b = await auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})

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
    # Arrange — register + login to get tokens
    await _register_user(auth_client, "user@example.com", "password123", invite_code)
    login_resp = await _login_user(auth_client, "user@example.com", "password123")
    refresh_token = login_resp.json()["refresh_token"]

    # Act — try to access protected route with refresh token instead of access token
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    # Assert
    assert resp.status_code == 401


async def test_protected_with_non_integer_sub(auth_client: AsyncClient) -> None:
    """A JWT with non-integer 'sub' claim must be rejected."""
    # Arrange — craft a token with a non-integer sub
    settings = get_settings()
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": "not-an-int", "type": "access", "exp": expire}
    bad_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"},
    )

    # Assert
    assert resp.status_code == 401


async def test_protected_with_unknown_user_id(auth_client: AsyncClient) -> None:
    """A JWT for a non-existent user_id must be rejected."""
    # Arrange — craft a token for user id 99999 (doesn't exist)
    settings = get_settings()
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": "99999", "type": "access", "exp": expire}
    ghost_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {ghost_token}"},
    )

    # Assert
    assert resp.status_code == 401


async def test_protected_with_invalid_jwt_signature(auth_client: AsyncClient) -> None:
    """A token signed with the wrong secret must be rejected."""
    # Arrange
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": "1", "type": "access", "exp": expire}
    bad_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"},
    )

    # Assert
    assert resp.status_code == 401


async def test_protected_with_missing_sub_claim(auth_client: AsyncClient) -> None:
    """A JWT with no 'sub' claim must be rejected."""
    # Arrange — token without 'sub'
    settings = get_settings()
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"type": "access", "exp": expire}
    no_sub_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {no_sub_token}"},
    )

    # Assert
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Account lockout test
# ---------------------------------------------------------------------------


async def test_account_lockout(auth_client: AsyncClient, invite_code: str) -> None:
    # Arrange
    await _register_user(auth_client, "user@example.com", "password123", invite_code)

    # Act — 5 wrong attempts
    for _ in range(5):
        resp = await _login_user(auth_client, "user@example.com", "wrongpassword")

    # 6th attempt — should be locked even with correct password
    resp = await _login_user(auth_client, "user@example.com", "password123")

    # Assert
    assert resp.status_code == 401
    assert "locked" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Bootstrap tests
# ---------------------------------------------------------------------------


async def test_bootstrap_creates_admin_user(
    auth_client: AsyncClient, auth_session: AsyncSession
) -> None:
    """Bootstrap creates first user when secret is correct."""
    from src.core.config import get_settings, Settings
    from src.api.app import create_app
    from src.api.dependencies import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: auth_session  # type: ignore[assignment]

    def override_settings() -> Settings:
        return Settings(bootstrap_secret="test-secret-abc", app_url=None)

    app.dependency_overrides[get_settings] = override_settings

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/bootstrap",
            json={"email": "admin@example.com", "password": "adminpass1", "bootstrap_secret": "test-secret-abc"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert "Bootstrap successful" in body["message"]

    from sqlmodel import select
    user = (await auth_session.exec(select(User).where(User.email == "admin@example.com"))).first()
    assert user is not None

    app.dependency_overrides.clear()


async def test_bootstrap_wrong_secret_returns_403(
    auth_client: AsyncClient, auth_session: AsyncSession
) -> None:
    """Wrong bootstrap_secret returns 403."""
    from src.core.config import get_settings, Settings
    from src.api.app import create_app
    from src.api.dependencies import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: auth_session  # type: ignore[assignment]
    app.dependency_overrides[get_settings] = lambda: Settings(bootstrap_secret="real-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/bootstrap",
            json={"email": "a@b.com", "password": "password1", "bootstrap_secret": "wrong-secret"},
        )

    assert resp.status_code == 403
    app.dependency_overrides.clear()


async def test_bootstrap_locked_after_first_user_returns_409(
    auth_client: AsyncClient, auth_session: AsyncSession, invite_code: str
) -> None:
    """Bootstrap returns 409 when at least one user already exists."""
    from src.core.config import get_settings, Settings
    from src.api.app import create_app
    from src.api.dependencies import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: auth_session  # type: ignore[assignment]
    app.dependency_overrides[get_settings] = lambda: Settings(bootstrap_secret="test-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/bootstrap",
            json={"email": "new@admin.com", "password": "password1", "bootstrap_secret": "test-secret"},
        )

    assert resp.status_code == 409
    app.dependency_overrides.clear()


async def test_bootstrap_missing_secret_env_returns_503(
    auth_client: AsyncClient, auth_session: AsyncSession
) -> None:
    """Bootstrap returns 503 when BOOTSTRAP_SECRET env var is not configured."""
    from src.core.config import get_settings, Settings
    from src.api.app import create_app
    from src.api.dependencies import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: auth_session  # type: ignore[assignment]
    app.dependency_overrides[get_settings] = lambda: Settings(bootstrap_secret=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/bootstrap",
            json={"email": "a@b.com", "password": "password1", "bootstrap_secret": "any"},
        )

    assert resp.status_code == 503
    app.dependency_overrides.clear()


async def test_bootstrap_weak_password_returns_422(
    auth_client: AsyncClient, auth_session: AsyncSession
) -> None:
    """Bootstrap rejects passwords shorter than 8 chars."""
    from src.core.config import get_settings, Settings
    from src.api.app import create_app
    from src.api.dependencies import get_session

    app = create_app()
    app.dependency_overrides[get_session] = lambda: auth_session  # type: ignore[assignment]
    app.dependency_overrides[get_settings] = lambda: Settings(bootstrap_secret="test-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/bootstrap",
            json={"email": "a@b.com", "password": "short", "bootstrap_secret": "test-secret"},
        )

    assert resp.status_code == 422
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Invite link tests
# ---------------------------------------------------------------------------


async def test_invite_response_includes_invite_link(
    auth_client: AsyncClient, auth_session: AsyncSession, invite_code: str
) -> None:
    """POST /invite returns invite_link when APP_URL is set."""
    from src.core.config import get_settings, Settings
    from src.api.app import create_app
    from src.api.dependencies import get_session

    await _register_user(auth_client, "user@example.com", "password123", invite_code)
    login_resp = await _login_user(auth_client, "user@example.com", "password123")
    token = login_resp.json()["access_token"]

    app = create_app()
    app.dependency_overrides[get_session] = lambda: auth_session  # type: ignore[assignment]
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_url="https://garmincoach.onrender.com"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/invite",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert "code" in body
    assert body["invite_link"] == f"https://garmincoach.onrender.com/register?invite={body['code']}"
    app.dependency_overrides.clear()


async def test_invite_response_link_null_without_app_url(
    auth_client: AsyncClient, invite_code: str
) -> None:
    """POST /invite returns invite_link=null when APP_URL is not set."""
    await _register_user(auth_client, "user@example.com", "password123", invite_code)
    login_resp = await _login_user(auth_client, "user@example.com", "password123")
    token = login_resp.json()["access_token"]

    resp = await auth_client.post(
        "/api/v1/auth/invite",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["invite_link"] is None
