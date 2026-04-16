"""Shared helpers for the Garmin auth-version runtime flag.

The flag lives in SystemConfig under ``SYSTEM_CONFIG_KEY`` and can be switched
by the admin endpoint. A ``GarminAuthVersion`` enum replaces ad-hoc "v1"/"v2"
literals across routers, factories, and the auto-reconnect flow.
"""
from __future__ import annotations

from enum import StrEnum

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import SystemConfig

SYSTEM_CONFIG_KEY = "garmin_auth_version"


class GarminAuthVersion(StrEnum):
    V1 = "v1"
    V2 = "v2"


def parse(value: str | None) -> GarminAuthVersion:
    """Coerce a stored/config string to the enum. Unknown/None → V1."""
    if not value:
        return GarminAuthVersion.V1
    try:
        return GarminAuthVersion(value)
    except ValueError:
        return GarminAuthVersion.V1


async def get_db_auth_version(session: AsyncSession) -> GarminAuthVersion:
    """Read the runtime Garmin auth version from SystemConfig.

    Returns V1 when the row is absent (fresh install default).
    """
    row = await session.get(SystemConfig, SYSTEM_CONFIG_KEY)
    return parse(row.value if row else None)
