from __future__ import annotations

import pytest


def _normalize_for_alembic(url: str) -> str:
    """Mirror of the logic in alembic/env.py — normalize URL for sync alembic use."""
    url = url.replace("+aiosqlite", "").replace("+asyncpg", "")
    # asyncpg uses ssl=require; psycopg2 (sync alembic driver) uses sslmode=require
    url = url.replace("ssl=require", "sslmode=require")
    return url


@pytest.mark.parametrize(
    "input_url,expected",
    [
        # Local dev: SQLite async driver → sync for alembic
        ("sqlite+aiosqlite:////data/db.db", "sqlite:////data/db.db"),
        # Production: PostgreSQL async driver + ssl param → sync psycopg2 form
        ("postgresql+asyncpg://user:pw@host/db?ssl=require", "postgresql://user:pw@host/db?sslmode=require"),
        # Already sync (no async driver suffix) — must pass through unchanged
        ("sqlite:////data/db.db", "sqlite:////data/db.db"),
        ("postgresql://user:pw@host/db", "postgresql://user:pw@host/db"),
    ],
    ids=["sqlite-async", "postgres-async-ssl", "sqlite-sync-passthrough", "postgres-sync-passthrough"],
)
def test_normalize_for_alembic(input_url: str, expected: str) -> None:
    assert _normalize_for_alembic(input_url) == expected


@pytest.mark.parametrize(
    "url,expected_is_sqlite",
    [
        ("sqlite:////data/db.db", True),
        ("sqlite+aiosqlite:////data/db.db", True),
        ("postgresql://user:pw@host/db", False),
        ("postgresql+asyncpg://user:pw@host/db?ssl=require", False),
    ],
    ids=["sqlite-sync", "sqlite-async", "postgres-sync", "postgres-async"],
)
def test_render_as_batch_condition(url: str, expected_is_sqlite: bool) -> None:
    sync_url = _normalize_for_alembic(url)
    assert sync_url.startswith("sqlite") == expected_is_sqlite
