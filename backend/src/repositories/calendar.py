from __future__ import annotations

from datetime import date

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import ScheduledWorkout
from src.repositories.base import BaseRepository


class ScheduledWorkoutRepository(BaseRepository[ScheduledWorkout]):
    async def get_range(
        self, session: AsyncSession, start: date, end: date
    ) -> list[ScheduledWorkout]:
        result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.date >= start,
                ScheduledWorkout.date <= end,
            )
        )
        return list(result.all())

    async def get_future_incomplete(
        self, session: AsyncSession, from_date: date
    ) -> list[ScheduledWorkout]:
        result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.date >= from_date,
                ScheduledWorkout.completed == False,  # noqa: E712
            )
        )
        return list(result.all())

    async def get_by_status(
        self, session: AsyncSession, statuses: tuple[str, ...]
    ) -> list[ScheduledWorkout]:
        result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.sync_status.in_(statuses)  # type: ignore[attr-defined]
            )
        )
        return list(result.all())

    async def get_all(self, session: AsyncSession) -> list[ScheduledWorkout]:
        result = await session.exec(select(ScheduledWorkout))
        return list(result.all())


scheduled_workout_repository = ScheduledWorkoutRepository(ScheduledWorkout)
