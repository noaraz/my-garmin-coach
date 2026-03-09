from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.auth.models import InviteCode, User
from src.auth.passwords import hash_password
from src.db.models import AthleteProfile
from src.garmin.encryption import decrypt_token, encrypt_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="garmin_session")
async def garmin_session_fixture() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session_factory = sessionmaker(  # type: ignore[call-overload]
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture(name="garmin_client")
async def garmin_client_fixture(
    garmin_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield garmin_session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(name="garmin_user_token")
async def garmin_user_token_fixture(
    garmin_session: AsyncSession, garmin_client: AsyncClient
) -> str:
    """Create a user + invite, register, login, return access_token."""
    # Create admin + invite
    admin = User(email="admin@garmin.test", password_hash=hash_password("adminpass"))
    garmin_session.add(admin)
    await garmin_session.commit()
    await garmin_session.refresh(admin)

    invite = InviteCode(code="GARMIN-INVITE-001", created_by=admin.id)
    garmin_session.add(invite)
    await garmin_session.commit()

    # Register user
    await garmin_client.post(
        "/api/v1/auth/register",
        json={
            "email": "garminuser@example.com",
            "password": "password123",
            "invite_code": "GARMIN-INVITE-001",
        },
    )

    # Login
    login_resp = await garmin_client.post(
        "/api/v1/auth/login",
        json={"email": "garminuser@example.com", "password": "password123"},
    )
    return login_resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Pure encryption unit tests (no HTTP needed)
# ---------------------------------------------------------------------------


def test_decryption_works() -> None:
    """Encrypt a token then decrypt it — must match original."""
    # Arrange
    user_id = 42
    secret = "test-secret"
    original = '{"oauth_token": "abc123", "oauth_token_secret": "xyz789"}'

    # Act
    encrypted = encrypt_token(user_id, secret, original)
    decrypted = decrypt_token(user_id, secret, encrypted)

    # Assert
    assert decrypted == original
    assert encrypted != original  # must actually be encrypted


def test_different_users_different_keys() -> None:
    """Same plaintext encrypted with different user_ids produces different ciphertext."""
    # Arrange
    secret = "test-secret"
    plaintext = '{"token": "same-data"}'

    # Act
    ciphertext_user1 = encrypt_token(1, secret, plaintext)
    ciphertext_user2 = encrypt_token(2, secret, plaintext)

    # Assert
    assert ciphertext_user1 != ciphertext_user2


# ---------------------------------------------------------------------------
# HTTP endpoint tests (mocked garth)
# ---------------------------------------------------------------------------


async def test_connect_encrypts_token(
    garmin_session: AsyncSession,
    garmin_client: AsyncClient,
    garmin_user_token: str,
) -> None:
    """POST /garmin/connect stores an encrypted (not plaintext) token in DB."""
    # Arrange — mock garth so no real Garmin call happens
    mock_garth_client = MagicMock()
    mock_garth_client.dumps.return_value = '{"oauth_token": "garmin_tok", "oauth_token_secret": "secret_val"}'

    with patch("src.api.routers.garmin_connect.garth") as mock_garth_module:
        mock_garth_module.Client.return_value = mock_garth_client
        mock_garth_module.Client.return_value.login = MagicMock()

        # Act
        resp = await garmin_client.post(
            "/api/v1/garmin/connect",
            json={"email": "garmin@example.com", "password": "garminpass"},
            headers={"Authorization": f"Bearer {garmin_user_token}"},
        )

    # Assert HTTP
    assert resp.status_code == 200
    assert resp.json()["connected"] is True

    # Assert DB — token must not be stored as plaintext
    profile = (
        await garmin_session.exec(
            select(AthleteProfile).where(AthleteProfile.garmin_connected.is_(True))
        )
    ).first()
    assert profile is not None
    assert profile.garmin_oauth_token_encrypted is not None
    assert "garmin_tok" not in profile.garmin_oauth_token_encrypted


async def test_status_connected(
    garmin_session: AsyncSession,
    garmin_client: AsyncClient,
    garmin_user_token: str,
) -> None:
    """After connect, GET /garmin/status returns connected=true."""
    mock_garth_client = MagicMock()
    mock_garth_client.dumps.return_value = '{"oauth_token": "tok"}'

    with patch("src.api.routers.garmin_connect.garth") as mock_garth_module:
        mock_garth_module.Client.return_value = mock_garth_client
        mock_garth_module.Client.return_value.login = MagicMock()

        await garmin_client.post(
            "/api/v1/garmin/connect",
            json={"email": "g@example.com", "password": "pass"},
            headers={"Authorization": f"Bearer {garmin_user_token}"},
        )

    # Act
    resp = await garmin_client.get(
        "/api/v1/garmin/status",
        headers={"Authorization": f"Bearer {garmin_user_token}"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["connected"] is True


async def test_disconnect_removes(
    garmin_session: AsyncSession,
    garmin_client: AsyncClient,
    garmin_user_token: str,
) -> None:
    """POST /garmin/disconnect clears token and sets connected=false."""
    # Arrange — connect first
    mock_garth_client = MagicMock()
    mock_garth_client.dumps.return_value = '{"oauth_token": "tok"}'

    with patch("src.api.routers.garmin_connect.garth") as mock_garth_module:
        mock_garth_module.Client.return_value = mock_garth_client
        mock_garth_module.Client.return_value.login = MagicMock()

        await garmin_client.post(
            "/api/v1/garmin/connect",
            json={"email": "g@example.com", "password": "pass"},
            headers={"Authorization": f"Bearer {garmin_user_token}"},
        )

    # Act
    resp = await garmin_client.post(
        "/api/v1/garmin/disconnect",
        headers={"Authorization": f"Bearer {garmin_user_token}"},
    )

    # Assert HTTP
    assert resp.status_code == 200
    assert resp.json()["connected"] is False

    # Assert DB
    resp_status = await garmin_client.get(
        "/api/v1/garmin/status",
        headers={"Authorization": f"Bearer {garmin_user_token}"},
    )
    assert resp_status.json()["connected"] is False


async def test_connect_returns_400_when_garth_login_fails(
    garmin_client: AsyncClient,
    garmin_user_token: str,
) -> None:
    """POST /garmin/connect returns 400 when garth.login raises an exception."""
    # Arrange — make garth.login raise
    mock_garth_client = MagicMock()
    mock_garth_client.login.side_effect = Exception("Invalid credentials")

    with patch("src.api.routers.garmin_connect.garth") as mock_garth_module:
        mock_garth_module.Client.return_value = mock_garth_client

        # Act
        resp = await garmin_client.post(
            "/api/v1/garmin/connect",
            json={"email": "bad@example.com", "password": "wrong"},
            headers={"Authorization": f"Bearer {garmin_user_token}"},
        )

    # Assert
    assert resp.status_code == 400
    assert "Garmin authentication failed" in resp.json()["detail"]


async def test_connect_returns_401_without_token(
    garmin_client: AsyncClient,
) -> None:
    """POST /garmin/connect without auth token returns 401."""
    # Act — no Authorization header
    resp = await garmin_client.post(
        "/api/v1/garmin/connect",
        json={"email": "g@example.com", "password": "pass"},
    )

    # Assert
    assert resp.status_code == 401


async def test_status_returns_false_when_no_profile_exists(
    garmin_client: AsyncClient,
    garmin_user_token: str,
) -> None:
    """GET /garmin/status returns connected=false when no profile exists yet."""
    # Act — no profile created, just check status
    resp = await garmin_client.get(
        "/api/v1/garmin/status",
        headers={"Authorization": f"Bearer {garmin_user_token}"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["connected"] is False


async def test_disconnect_returns_false_when_no_profile_exists(
    garmin_client: AsyncClient,
    garmin_user_token: str,
) -> None:
    """POST /garmin/disconnect is idempotent — returns false even when no profile exists."""
    # Act — disconnect without ever connecting
    resp = await garmin_client.post(
        "/api/v1/garmin/disconnect",
        headers={"Authorization": f"Bearer {garmin_user_token}"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["connected"] is False


async def test_connect_creates_profile_when_none_exists(
    garmin_session: AsyncSession,
    garmin_client: AsyncClient,
    garmin_user_token: str,
) -> None:
    """POST /garmin/connect creates AthleteProfile when user has none yet."""
    # Arrange — no profile seeded for this user
    mock_garth_client = MagicMock()
    mock_garth_client.dumps.return_value = '{"oauth_token": "tok"}'

    with patch("src.api.routers.garmin_connect.garth") as mock_garth_module:
        mock_garth_module.Client.return_value = mock_garth_client
        mock_garth_module.Client.return_value.login = MagicMock()

        # Act
        resp = await garmin_client.post(
            "/api/v1/garmin/connect",
            json={"email": "g@example.com", "password": "pass"},
            headers={"Authorization": f"Bearer {garmin_user_token}"},
        )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["connected"] is True

    # Verify profile was created in DB
    profile = (
        await garmin_session.exec(
            select(AthleteProfile).where(AthleteProfile.garmin_connected.is_(True))
        )
    ).first()
    assert profile is not None
