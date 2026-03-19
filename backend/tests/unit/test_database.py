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
# get_session — the async generator yields a session
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
