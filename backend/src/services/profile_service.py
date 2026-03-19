from __future__ import annotations

from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from src.core import cache
from src.db.models import AthleteProfile
from src.repositories.profile import profile_repository

# Fields to cache for AthleteProfile (plain dict, not ORM object)
_PROFILE_CACHE_FIELDS = (
    "id", "name", "user_id", "lthr", "max_hr", "resting_hr",
    "threshold_pace", "garmin_connected", "updated_at",
)


def _profile_to_dict(profile: AthleteProfile) -> dict:
    return {f: getattr(profile, f) for f in _PROFILE_CACHE_FIELDS}


def _dict_to_profile(d: dict) -> AthleteProfile:
    return AthleteProfile(**d)


class ProfileService:
    async def get_or_create(
        self, session: AsyncSession, user_id: int | None = None
    ) -> AthleteProfile:
        """Return the profile for the given user_id, creating it if it doesn't exist.

        Falls back to the legacy singleton (first profile) when user_id is None,
        for backward compatibility.
        """
        if user_id is not None:
            cache_key = f"profile:{user_id}"
            cached = cache.get(cache_key)
            if cached is not None:
                # Cached as dict to avoid DetachedInstanceError across sessions
                return _dict_to_profile(cached)
            profile = await profile_repository.get_by_user_id(session, user_id)
            if profile is None:
                profile = AthleteProfile(name="Athlete", user_id=user_id)
                profile = await profile_repository.create(session, profile)
                # Don't cache on create — invalidate pattern per CLAUDE.md;
                # next read will populate the cache.
            else:
                cache.set(cache_key, _profile_to_dict(profile))
        else:
            profile = await profile_repository.get_singleton(session)
            if profile is None:
                profile = AthleteProfile(name="Athlete")
                profile = await profile_repository.create(session, profile)
        return profile

    async def update(
        self, session: AsyncSession, data: dict, user_id: int | None = None
    ) -> AthleteProfile:
        """Update the profile for the given user_id (or singleton) with the provided fields."""
        profile = await self.get_or_create(session, user_id=user_id)

        changed_fields: set[str] = set()
        for key, value in data.items():
            if value is not None and hasattr(profile, key):
                old_value = getattr(profile, key)
                if old_value != value:
                    setattr(profile, key, value)
                    changed_fields.add(key)

        profile.updated_at = datetime.utcnow()
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        # Invalidate cache after profile update
        if user_id is not None:
            cache.invalidate(f"profile:{user_id}")

        # Trigger zone recalculation if threshold values changed
        if "lthr" in changed_fields or "threshold_pace" in changed_fields:
            from src.services.zone_service import zone_service

            if "lthr" in changed_fields and profile.lthr:
                await zone_service.recalculate_hr_zones(session, profile)

            if "threshold_pace" in changed_fields and profile.threshold_pace:
                await zone_service.recalculate_pace_zones(session, profile)

        return profile


profile_service = ProfileService()

# ---------------------------------------------------------------------------
# Module-level shims for backward compatibility with existing router imports
# ---------------------------------------------------------------------------


async def get_or_create_profile(
    session: AsyncSession, user_id: int | None = None
) -> AthleteProfile:
    return await profile_service.get_or_create(session, user_id=user_id)


async def update_profile(
    session: AsyncSession, data: dict, user_id: int | None = None
) -> AthleteProfile:
    return await profile_service.update(session, data, user_id=user_id)
