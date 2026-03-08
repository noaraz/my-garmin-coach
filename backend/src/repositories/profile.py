from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile
from src.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[AthleteProfile]):
    async def get_singleton(self, session: AsyncSession) -> AthleteProfile | None:
        result = await session.exec(select(AthleteProfile))
        return result.first()

    async def get_by_user_id(
        self, session: AsyncSession, user_id: int
    ) -> AthleteProfile | None:
        result = await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == user_id)
        )
        return result.first()


profile_repository = ProfileRepository(AthleteProfile)
