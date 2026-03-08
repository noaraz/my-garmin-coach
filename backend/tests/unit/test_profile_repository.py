from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import src.db.models  # noqa: F401 — register all SQLModel tables
import src.auth.models  # noqa: F401 — register User/InviteCode tables
from src.db.models import AthleteProfile
from src.repositories.profile import ProfileRepository


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
def repo() -> ProfileRepository:
    return ProfileRepository(AthleteProfile)


# ---------------------------------------------------------------------------
# get_singleton — lines 12-13
# ---------------------------------------------------------------------------


class TestGetSingleton:
    async def test_get_singleton_returns_none_when_no_profile_exists(
        self, db_session: AsyncSession, repo: ProfileRepository
    ) -> None:
        # Arrange — empty DB

        # Act — line 12-13 covered
        result = await repo.get_singleton(db_session)

        # Assert
        assert result is None

    async def test_get_singleton_returns_first_profile_when_exists(
        self, db_session: AsyncSession, repo: ProfileRepository
    ) -> None:
        # Arrange
        profile = AthleteProfile(name="Singleton")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)

        # Act
        result = await repo.get_singleton(db_session)

        # Assert
        assert result is not None
        assert result.name == "Singleton"


# ---------------------------------------------------------------------------
# get_by_user_id — line 21
# ---------------------------------------------------------------------------


class TestGetByUserId:
    async def test_get_by_user_id_returns_none_when_user_has_no_profile(
        self, db_session: AsyncSession, repo: ProfileRepository
    ) -> None:
        # Arrange — empty DB

        # Act — line 21 covered (result.first() returns None)
        result = await repo.get_by_user_id(db_session, user_id=42)

        # Assert
        assert result is None

    async def test_get_by_user_id_returns_profile_when_found(
        self, db_session: AsyncSession, repo: ProfileRepository
    ) -> None:
        # Arrange
        profile = AthleteProfile(name="UserProfile", user_id=7)
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)

        # Act
        result = await repo.get_by_user_id(db_session, user_id=7)

        # Assert
        assert result is not None
        assert result.user_id == 7
        assert result.name == "UserProfile"

    async def test_get_by_user_id_returns_none_for_different_user(
        self, db_session: AsyncSession, repo: ProfileRepository
    ) -> None:
        # Arrange — profile belongs to user 1, querying for user 2
        profile = AthleteProfile(name="User1Profile", user_id=1)
        db_session.add(profile)
        await db_session.commit()

        # Act
        result = await repo.get_by_user_id(db_session, user_id=2)

        # Assert
        assert result is None
