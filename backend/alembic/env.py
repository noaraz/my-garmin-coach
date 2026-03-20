from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import all models so autogenerate detects them
import sqlmodel  # noqa: F401
from src.db.models import (  # noqa: F401
    AthleteProfile,
    GarminActivity,
    HRZone,
    PaceZone,
    ScheduledWorkout,
    TrainingPlan,
    WorkoutTemplate,
)
from src.auth.models import User, InviteCode  # noqa: F401
from sqlmodel import SQLModel

# Alembic Config object
config = context.config

# Set up loggers from the ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use SQLModel's metadata so autogenerate sees all table definitions
target_metadata = SQLModel.metadata

# Override the URL from DATABASE_URL env var if set.
# Strip async driver suffix — alembic uses a sync driver for both SQLite and PostgreSQL.
_db_url = os.environ.get("DATABASE_URL", "sqlite:////data/garmincoach.db")
_sync_url = _db_url.replace("+aiosqlite", "").replace("+asyncpg", "")
# asyncpg uses ?ssl=require; psycopg2 (alembic sync driver) uses ?sslmode=require
_sync_url = _sync_url.replace("ssl=require", "sslmode=require")
_is_sqlite = _sync_url.startswith("sqlite")
config.set_main_option("sqlalchemy.url", _sync_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=False,  # SQLite type comparison unreliable; avoid false positives
            render_as_batch=_is_sqlite,  # Required for SQLite ALTER COLUMN; not needed for PostgreSQL
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
