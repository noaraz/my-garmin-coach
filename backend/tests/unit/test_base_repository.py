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
from src.repositories.base import BaseRepository


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
def repo() -> BaseRepository[AthleteProfile]:
    return BaseRepository(AthleteProfile)


# ---------------------------------------------------------------------------
# get — existing and missing
# ---------------------------------------------------------------------------


class TestGet:
    async def test_get_returns_none_when_id_missing(
        self, db_session: AsyncSession, repo: BaseRepository[AthleteProfile]
    ) -> None:
        # Arrange — nothing seeded

        # Act
        result = await repo.get(db_session, 9999)

        # Assert
        assert result is None

    async def test_get_returns_record_when_id_exists(
        self, db_session: AsyncSession, repo: BaseRepository[AthleteProfile]
    ) -> None:
        # Arrange
        profile = AthleteProfile(name="Tester")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)

        # Act
        result = await repo.get(db_session, profile.id)

        # Assert
        assert result is not None
        assert result.name == "Tester"


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------


class TestGetAll:
    async def test_get_all_returns_empty_list_when_no_records(
        self, db_session: AsyncSession, repo: BaseRepository[AthleteProfile]
    ) -> None:
        # Act
        result = await repo.get_all(db_session)

        # Assert — line 21-22 covered
        assert result == []

    async def test_get_all_returns_all_records(
        self, db_session: AsyncSession, repo: BaseRepository[AthleteProfile]
    ) -> None:
        # Arrange
        db_session.add(AthleteProfile(name="Alice"))
        db_session.add(AthleteProfile(name="Bob"))
        await db_session.commit()

        # Act
        result = await repo.get_all(db_session)

        # Assert
        assert len(result) == 2
        names = {r.name for r in result}
        assert names == {"Alice", "Bob"}


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    async def test_create_persists_and_returns_record_with_id(
        self, db_session: AsyncSession, repo: BaseRepository[AthleteProfile]
    ) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner")

        # Act — lines 25-28 covered
        result = await repo.create(db_session, profile)

        # Assert
        assert result.id is not None
        assert result.name == "Runner"


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    async def test_update_changes_fields_on_record(
        self, db_session: AsyncSession, repo: BaseRepository[AthleteProfile]
    ) -> None:
        # Arrange
        profile = AthleteProfile(name="Original", max_hr=180)
        await repo.create(db_session, profile)

        # Act — lines 30-37 covered
        updated = await repo.update(db_session, profile, {"name": "Updated", "max_hr": 190})

        # Assert
        assert updated.name == "Updated"
        assert updated.max_hr == 190

    async def test_update_ignores_unknown_keys(
        self, db_session: AsyncSession, repo: BaseRepository[AthleteProfile]
    ) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner")
        await repo.create(db_session, profile)

        # Act — hasattr check: unknown key is silently skipped
        result = await repo.update(db_session, profile, {"nonexistent_field": "value", "name": "Changed"})

        # Assert
        assert result.name == "Changed"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    async def test_delete_removes_record_from_db(
        self, db_session: AsyncSession, repo: BaseRepository[AthleteProfile]
    ) -> None:
        # Arrange
        profile = AthleteProfile(name="ToDelete")
        created = await repo.create(db_session, profile)
        record_id = created.id

        # Act
        await repo.delete(db_session, created)

        # Assert — record is gone
        result = await repo.get(db_session, record_id)
        assert result is None
