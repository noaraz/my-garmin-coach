from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from garth.exc import GarthHTTPError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core import cache
from src.core.config import get_settings
from src.db.models import AthleteProfile
from src.garmin import client_cache
from src.garmin.adapter import GarminAdapter
from src.garmin.client_factory import create_api_client, create_login_client
from src.garmin.encryption import decrypt_credential, encrypt_token

logger = logging.getLogger(__name__)

_CREDENTIAL_MAX_AGE_DAYS = 30

# Per-user reconnect cooldown: {user_id: cooldown_until_monotonic}
_cooldowns: dict[int, float] = {}


def _credentials_expired(stored_at: datetime | None) -> bool:
    """Check if credentials are older than 30 days."""
    if stored_at is None:
        return True
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    delta = now - stored_at
    return delta.days >= _CREDENTIAL_MAX_AGE_DAYS


def _reconnect_on_cooldown(user_id: int) -> bool:
    """Check if a user's reconnect is on cooldown."""
    until = _cooldowns.get(user_id)
    if until is None:
        return False
    if time.monotonic() >= until:
        del _cooldowns[user_id]
        return False
    return True


def _set_reconnect_cooldown(user_id: int, seconds: int) -> None:
    """Set a reconnect cooldown for a user."""
    _cooldowns[user_id] = time.monotonic() + seconds


async def attempt_auto_reconnect(
    user_id: int,
    session: AsyncSession,
) -> GarminAdapter | None:
    """Try to re-login using stored credentials when exchange fails.

    Returns a fresh GarminAdapter on success, None if credentials are
    missing, expired, on cooldown, or login fails.

    This function implements three layers of storm prevention:
    1. Early-exit: only called once per sync (caller's responsibility)
    2. Module-level cooldown: 15min–1hr per-user backoff on failure
    3. In-process client cache: 1hr TTL on successful reconnect

    Args:
        user_id: The user's database id.
        session: Active async DB session.

    Returns:
        A fresh GarminAdapter if reconnect succeeded, None otherwise.
    """
    settings = get_settings()

    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == user_id)
        )
    ).first()
    if not profile or not profile.garmin_credential_encrypted:
        return None

    # Check 30-day expiry
    if _credentials_expired(profile.garmin_credential_stored_at):
        logger.info(
            "Garmin credentials expired (30-day policy) for user %s — clearing", user_id
        )
        profile.garmin_credential_encrypted = None
        profile.garmin_credential_stored_at = None
        session.add(profile)
        await session.commit()
        return None

    # Per-user reconnect cooldown
    if _reconnect_on_cooldown(user_id):
        logger.info("Auto-reconnect on cooldown for user %s — skipping", user_id)
        return None

    # Decrypt and re-login
    try:
        creds = decrypt_credential(
            user_id, settings.garmin_credential_key, profile.garmin_credential_encrypted
        )
    except Exception:
        logger.warning("Could not decrypt credentials for user %s — clearing", user_id)
        profile.garmin_credential_encrypted = None
        profile.garmin_credential_stored_at = None
        session.add(profile)
        await session.commit()
        return None

    email, password = creds["email"], creds["password"]
    try:
        # Best-effort single attempt — fingerprint rotation not applied here.
        # If chrome136 fails, caller catches the exception and schedules a manual reconnect.
        client = create_login_client()
        client.login(email, password)
        token_json = client.dumps()

        # Persist fresh tokens
        encrypted = encrypt_token(user_id, settings.garmincoach_secret_key, token_json)
        profile.garmin_oauth_token_encrypted = encrypted
        session.add(profile)
        await session.commit()
        cache.invalidate(f"profile:{user_id}")
        client_cache.invalidate(user_id)

        adapter = create_api_client(token_json)
        client_cache.put(user_id, adapter)

        # Clear exchange cooldown — fresh tokens don't need the 30-min pause
        from src.api.routers.sync import clear_exchange_cooldown
        clear_exchange_cooldown(user_id)

        logger.info("Auto-reconnect succeeded for user %s", user_id)
        return adapter
    except GarthHTTPError:
        # Bad credentials or Garmin blocked
        logger.warning(
            "Auto-reconnect login failed for user %s (clearing credentials)", user_id
        )
        profile.garmin_credential_encrypted = None
        profile.garmin_credential_stored_at = None
        session.add(profile)
        await session.commit()
        _set_reconnect_cooldown(user_id, seconds=3600)  # 1 hour
        return None
    except Exception as exc:
        logger.warning(
            "Auto-reconnect failed for user %s: %s", user_id, type(exc).__name__
        )
        _set_reconnect_cooldown(user_id, seconds=900)  # 15 min
        return None
    finally:
        # Clear sensitive credentials from memory
        del email, password
