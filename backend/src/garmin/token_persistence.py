from __future__ import annotations

import logging

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core import cache
from src.core.config import get_settings
from src.db.models import AthleteProfile
from src.garmin.encryption import encrypt_token
from src.services.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)


async def persist_refreshed_token(
    sync_service: SyncOrchestrator,
    user_id: int,
    session: AsyncSession,
) -> None:
    """Persist garth's current token state back to the DB.

    garth may refresh the OAuth2 token in-memory during API calls (via
    refresh_oauth2()). Without persisting it, each sync re-exchanges the same
    expired token, hitting Garmin's rate limit on the exchange endpoint (429).

    This function is called after any Garmin API operation that may have
    triggered a token refresh.
    """
    try:
        settings = get_settings()
        new_token_json = sync_service.dump_token()
        new_encrypted = encrypt_token(
            user_id, settings.garmincoach_secret_key, new_token_json
        )
        profile = (
            await session.exec(
                select(AthleteProfile).where(AthleteProfile.user_id == user_id)
            )
        ).first()
        if profile:
            profile.garmin_oauth_token_encrypted = new_encrypted
            session.add(profile)
            await session.commit()
            cache.invalidate(f"profile:{user_id}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not persist refreshed Garmin token (non-critical): %s", exc
        )
