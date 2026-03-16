from __future__ import annotations

from collections.abc import AsyncGenerator
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import src.db.models  # noqa: F401 — register all SQLModel tables
import src.auth.models  # noqa: F401 — register User/InviteCode tables
from src.auth import service as auth_service
from src.auth.models import User
from src.auth.passwords import hash_password


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
