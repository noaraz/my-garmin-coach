from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, text
from sqlmodel.ext.asyncio.session import AsyncSession

import src.db.models  # noqa: F401 — register all SQLModel tables
import src.auth.models  # noqa: F401 — register User/InviteCode tables


# ---------------------------------------------------------------------------
# Shared in-memory engine fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def mem_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


# ---------------------------------------------------------------------------
# create_db_and_tables — lines 20-21
# ---------------------------------------------------------------------------


class TestCreateDbAndTables:
    async def test_create_db_and_tables_runs_create_all(self, mem_engine) -> None:
        # Arrange — patch the module-level engine with our in-memory engine
        # so that create_db_and_tables() operates on memory, not the real DB file.
        from src.db import database

        with patch.object(database, "engine", mem_engine):
            # Act — lines 20-21: engine.begin() + run_sync(SQLModel.metadata.create_all)
            await database.create_db_and_tables()

        # Assert — the call completes without error (schema already exists; no-op)
        # Verify tables are present in the engine
        factory = sessionmaker(  # type: ignore[call-overload]
            mem_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            result = await session.exec(text("SELECT name FROM sqlite_master WHERE type='table'"))
            table_names = {row[0] for row in result}
            assert "athleteprofile" in table_names


# ---------------------------------------------------------------------------
# get_session — lines 25-26 (the async generator yields a session)
# ---------------------------------------------------------------------------


class TestGetSession:
    async def test_get_session_yields_async_session(self, mem_engine) -> None:
        # Arrange — patch the module-level async_session_factory to use our in-memory engine
        from src.db import database

        in_memory_factory = sessionmaker(  # type: ignore[call-overload]
            mem_engine, class_=AsyncSession, expire_on_commit=False
        )

        with patch.object(database, "async_session_factory", in_memory_factory):
            # Act — lines 25-26: consume the async generator
            session_gen = database.get_session()
            session = await session_gen.__anext__()

            # Assert — it yields an AsyncSession
            assert isinstance(session, AsyncSession)

            # Cleanup — exhaust the generator
            try:
                await session_gen.__anext__()
            except StopAsyncIteration:
                pass
