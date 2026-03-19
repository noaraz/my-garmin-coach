from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User  # noqa: F401 — ensures User table is in SQLModel.metadata

# ---------------------------------------------------------------------------
# Shared test user stub — returned by the mocked get_current_user dependency
# ---------------------------------------------------------------------------

TEST_USER = User(id=1, email="test@example.com", is_active=True)


async def _mock_get_current_user() -> User:
    return TEST_USER


_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
_IS_SQLITE = _TEST_DB_URL.startswith("sqlite")


@pytest.fixture(scope="session", autouse=True)
def _setup_db_schema() -> None:
    """For SQLite: schema is created per-test via create_all.
    For PostgreSQL: run alembic migrations once per session so the test schema
    matches the production migration chain (not just the ORM model definitions)."""
    if not _IS_SQLITE:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            env={**os.environ, "DATABASE_URL": _TEST_DB_URL},
            check=True,
        )


@pytest.fixture(name="session")
async def session_fixture() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    if _IS_SQLITE:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async_session_factory = sessionmaker(  # type: ignore[call-overload]
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        # Seed the test user so FK constraints are satisfied
        session.add(
            User(
                id=1,
                email="test@example.com",
                is_active=True,
            )
        )
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture(name="client")
async def client_fixture(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
