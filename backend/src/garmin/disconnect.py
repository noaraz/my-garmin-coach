"""Shared helper for clearing a user's Garmin connection state.

Used by the explicit disconnect endpoint and by the version-mismatch branch
in ``_get_garmin_adapter`` so both paths invalidate the same caches.
"""
from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from src.core import cache
from src.db.models import AthleteProfile
from src.garmin import client_cache


async def clear_garmin_connection(
    profile: AthleteProfile,
    user_id: int,
    session: AsyncSession,
    *,
    keep_credentials: bool = False,
) -> None:
    """Mark the user's Garmin connection as disconnected and invalidate caches.

    Args:
        keep_credentials: If True, leaves the encrypted credentials in place
            so auto-reconnect can retry a re-login (used for transient token
            incompatibilities, e.g. auth-version mismatch). If False, wipes
            credentials too — used for explicit user-initiated disconnect.
    """
    profile.garmin_oauth_token_encrypted = None
    profile.garmin_connected = False
    if not keep_credentials:
        profile.garmin_credential_encrypted = None
        profile.garmin_credential_stored_at = None
    session.add(profile)
    await session.commit()
    cache.invalidate(f"profile:{user_id}")
    client_cache.invalidate(user_id)
