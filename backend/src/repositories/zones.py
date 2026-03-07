from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import HRZone, PaceZone
from src.repositories.base import BaseRepository


class HRZoneRepository(BaseRepository[HRZone]):
    async def get_by_profile(self, session: AsyncSession, profile_id: int) -> list[HRZone]:
        result = await session.exec(
            select(HRZone)
            .where(HRZone.profile_id == profile_id)
            .order_by(HRZone.zone_number)
        )
        return list(result.all())

    async def delete_by_profile(self, session: AsyncSession, profile_id: int) -> None:
        zones = await self.get_by_profile(session, profile_id)
        for z in zones:
            await session.delete(z)
        await session.commit()


class PaceZoneRepository(BaseRepository[PaceZone]):
    async def get_by_profile(self, session: AsyncSession, profile_id: int) -> list[PaceZone]:
        result = await session.exec(
            select(PaceZone)
            .where(PaceZone.profile_id == profile_id)
            .order_by(PaceZone.zone_number)
        )
        return list(result.all())

    async def delete_by_profile(self, session: AsyncSession, profile_id: int) -> None:
        zones = await self.get_by_profile(session, profile_id)
        for z in zones:
            await session.delete(z)
        await session.commit()


hr_zone_repository = HRZoneRepository(HRZone)
pace_zone_repository = PaceZoneRepository(PaceZone)
