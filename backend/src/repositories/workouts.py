from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import WorkoutTemplate
from src.repositories.base import BaseRepository


class WorkoutTemplateRepository(BaseRepository[WorkoutTemplate]):
    async def get_all_ordered(self, session: AsyncSession) -> list[WorkoutTemplate]:
        result = await session.exec(select(WorkoutTemplate))
        return list(result.all())


workout_template_repository = WorkoutTemplateRepository(WorkoutTemplate)
