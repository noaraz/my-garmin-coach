from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import src.db.models  # noqa: F401 — register all SQLModel tables
import src.auth.models  # noqa: F401 — register User/InviteCode tables
from src.auth import service as auth_service
from src.auth.models import InviteCode, User
from src.auth.passwords import hash_password
from src.auth.schemas import LoginRequest, RegisterRequest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = sessionmaker(  # type: ignore[call-overload]
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def admin_and_invite(db_session: AsyncSession) -> tuple[User, str]:
    """Seed an admin user and an unused invite code. Returns (admin, code_str)."""
    admin = User(email="admin@example.com", password_hash=hash_password("adminpass123"))
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    code = InviteCode(code="UNIT-INVITE-001", created_by=admin.id)
    db_session.add(code)
    await db_session.commit()

    return admin, "UNIT-INVITE-001"


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_register_success_returns_user(
        self, db_session: AsyncSession, admin_and_invite: tuple[User, str]
    ) -> None:
        # Arrange
        _, code = admin_and_invite
        req = RegisterRequest(email="new@example.com", password="password123", invite_code=code)

        # Act — lines 38-65
        user = await auth_service.register(req, db_session)

        # Assert
        assert user.id is not None
        assert user.email == "new@example.com"

    async def test_register_marks_invite_as_used(
        self, db_session: AsyncSession, admin_and_invite: tuple[User, str]
    ) -> None:
        # Arrange
        _, code = admin_and_invite
        req = RegisterRequest(email="new@example.com", password="password123", invite_code=code)

        # Act
        user = await auth_service.register(req, db_session)

        # Assert — invite is consumed
        from sqlmodel import select
        invite = (await db_session.exec(select(InviteCode).where(InviteCode.code == code))).first()
        assert invite is not None
        assert invite.used_by == user.id
        assert invite.used_at is not None

    async def test_register_duplicate_email_raises_409(
        self, db_session: AsyncSession, admin_and_invite: tuple[User, str]
    ) -> None:
        # Arrange — pre-insert a user with the same email
        _, code = admin_and_invite
        existing = User(email="dup@example.com", password_hash=hash_password("password123"))
        db_session.add(existing)
        await db_session.commit()

        req = RegisterRequest(email="dup@example.com", password="password123", invite_code=code)

        # Act & Assert — line 39
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register(req, db_session)

        assert exc_info.value.status_code == 409

    async def test_register_invalid_invite_raises_403(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — no invite in DB
        req = RegisterRequest(email="new@example.com", password="password123", invite_code="BAD-CODE")

        # Act & Assert — line 48 (invite is None)
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register(req, db_session)

        assert exc_info.value.status_code == 403

    async def test_register_used_invite_raises_403(
        self, db_session: AsyncSession, admin_and_invite: tuple[User, str]
    ) -> None:
        # Arrange — consume the invite first
        admin, code = admin_and_invite
        first_user = User(email="first@example.com", password_hash=hash_password("password123"))
        db_session.add(first_user)
        await db_session.commit()
        await db_session.refresh(first_user)

        from sqlmodel import select
        invite = (await db_session.exec(select(InviteCode).where(InviteCode.code == code))).first()
        invite.used_by = first_user.id
        invite.used_at = datetime.now(timezone.utc)
        db_session.add(invite)
        await db_session.commit()

        req = RegisterRequest(email="second@example.com", password="password123", invite_code=code)

        # Act & Assert — line 48 (invite.used_by is not None)
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register(req, db_session)

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


class TestLogin:
    async def _seed_user(
        self, db_session: AsyncSession, email: str = "user@example.com", password: str = "password123"
    ) -> User:
        user = User(email=email, password_hash=hash_password(password))
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    async def test_login_success_returns_tokens(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange
        await self._seed_user(db_session)
        req = LoginRequest(email="user@example.com", password="password123")

        # Act — lines 81-109
        response = await auth_service.login(req, db_session)

        # Assert
        assert response.access_token
        assert response.refresh_token
        assert response.token_type == "bearer"

    async def test_login_success_resets_failed_counter(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — user has some prior failures
        user = await self._seed_user(db_session)
        user.failed_login_attempts = 3
        db_session.add(user)
        await db_session.commit()

        req = LoginRequest(email="user@example.com", password="password123")

        # Act — lines 100-104
        await auth_service.login(req, db_session)

        # Assert — counter reset
        await db_session.refresh(user)
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    async def test_login_wrong_password_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange
        await self._seed_user(db_session)
        req = LoginRequest(email="user@example.com", password="wrongpassword")

        # Act & Assert — line 98
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(req, db_session)

        assert exc_info.value.status_code == 401

    async def test_login_wrong_password_increments_counter(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange
        user = await self._seed_user(db_session)
        req = LoginRequest(email="user@example.com", password="wrongpassword")

        # Act — line 93
        with pytest.raises(HTTPException):
            await auth_service.login(req, db_session)

        # Assert
        await db_session.refresh(user)
        assert user.failed_login_attempts == 1

    async def test_login_fifth_failure_locks_account(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — 4 prior failures
        user = await self._seed_user(db_session)
        user.failed_login_attempts = 4
        db_session.add(user)
        await db_session.commit()

        req = LoginRequest(email="user@example.com", password="wrongpassword")

        # Act — line 94-95: 5th failure triggers lockout
        with pytest.raises(HTTPException):
            await auth_service.login(req, db_session)

        # Assert — locked_until is set
        await db_session.refresh(user)
        assert user.locked_until is not None
        assert user.failed_login_attempts == 5

    async def test_login_locked_account_raises_401_regardless_of_password(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — account already locked
        user = await self._seed_user(db_session)
        user.failed_login_attempts = 5
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        db_session.add(user)
        await db_session.commit()

        req = LoginRequest(email="user@example.com", password="password123")

        # Act & Assert — lines 85-89
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(req, db_session)

        assert exc_info.value.status_code == 401
        assert "locked" in exc_info.value.detail.lower()

    async def test_login_nonexistent_user_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — no users in DB
        req = LoginRequest(email="nobody@example.com", password="password123")

        # Act & Assert — line 82
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(req, db_session)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# refresh_token
# ---------------------------------------------------------------------------


class TestRefreshToken:
    async def _seed_user(self, db_session: AsyncSession) -> User:
        user = User(email="user@example.com", password_hash=hash_password("password123"))
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    async def test_refresh_token_valid_returns_new_access_token(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange
        user = await self._seed_user(db_session)
        from src.auth.jwt import create_refresh_token
        refresh_tok = create_refresh_token(user.id)

        # Act — lines 123-136
        response = await auth_service.refresh_token(refresh_tok, db_session)

        # Assert
        assert response.access_token
        assert response.token_type == "bearer"

    async def test_refresh_token_with_access_token_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — pass an access token where a refresh token is expected
        user = await self._seed_user(db_session)
        from src.auth.jwt import create_access_token
        access_tok = create_access_token(user.id)

        # Act & Assert — line 129: type != "refresh"
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(access_tok, db_session)

        assert exc_info.value.status_code == 401

    async def test_refresh_token_invalid_token_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — garbage token
        bad_token = "not.a.valid.jwt"

        # Act & Assert — lines 124-126: JWTError
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(bad_token, db_session)

        assert exc_info.value.status_code == 401

    async def test_refresh_token_inactive_user_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — deactivate the user
        user = await self._seed_user(db_session)
        user.is_active = False
        db_session.add(user)
        await db_session.commit()

        from src.auth.jwt import create_refresh_token
        refresh_tok = create_refresh_token(user.id)

        # Act & Assert — line 133-134: user.is_active is False
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(refresh_tok, db_session)

        assert exc_info.value.status_code == 401

    async def test_refresh_token_nonexistent_user_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — create token for user 9999 who doesn't exist
        from src.auth.jwt import create_refresh_token
        refresh_tok = create_refresh_token(9999)

        # Act & Assert — line 133-134: user is None
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(refresh_tok, db_session)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# create_invite
# ---------------------------------------------------------------------------


class TestCreateInvite:
    async def test_create_invite_returns_invite_with_code(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange
        admin = User(email="admin@example.com", password_hash=hash_password("adminpass123"))
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        # Act — lines 144-149
        invite = await auth_service.create_invite(admin, db_session)

        # Assert
        assert invite.id is not None
        assert invite.code
        assert len(invite.code) > 0
        assert invite.created_by == admin.id
        assert invite.used_by is None
