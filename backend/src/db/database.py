from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import get_settings

_settings = get_settings()
_is_postgres = _settings.database_url.startswith("postgresql")

_engine_kwargs: dict[str, Any] = {"echo": False}
if _is_postgres:
    _engine_kwargs.update(
        pool_size=5,
        max_overflow=5,
        pool_recycle=270,
        pool_pre_ping=True,
    )

engine = create_async_engine(_settings.database_url, **_engine_kwargs)

async_session_factory = sessionmaker(  # type: ignore[call-overload]
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
