from __future__ import annotations

from datetime import date

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import ScheduledWorkout
from src.repositories.base import BaseRepository


class ScheduledWorkoutRepository(BaseRepository[ScheduledWorkout]):
    async def get_range(
        self, session: AsyncSession, start: date, end: date, user_id: int
    ) -> list[ScheduledWorkout]:
        result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.date >= start,
                ScheduledWorkout.date <= end,
                ScheduledWorkout.user_id == user_id,
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

    async def get_all_incomplete(
        self, session: AsyncSession, user_id: int
    ) -> list[ScheduledWorkout]:
        """Return every non-completed ScheduledWorkout for the given user.

        Used by zone/template cascades so that already-synced workouts in the
        past (e.g. scheduled for today or yesterday) are also re-queued when
        zones or the linked template change.
        """
        result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.completed == False,  # noqa: E712
                ScheduledWorkout.user_id == user_id,
            )
        )
        return list(result.all())

    async def get_by_status(
        self, session: AsyncSession, statuses: tuple[str, ...], user_id: int
    ) -> list[ScheduledWorkout]:
        result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.sync_status.in_(statuses),  # type: ignore[attr-defined]
                ScheduledWorkout.user_id == user_id,
            )
        )
        return list(result.all())

    async def get_all(self, session: AsyncSession, user_id: int) -> list[ScheduledWorkout]:
        result = await session.exec(
            select(ScheduledWorkout).where(ScheduledWorkout.user_id == user_id)
        )
        return list(result.all())


scheduled_workout_repository = ScheduledWorkoutRepository(ScheduledWorkout)
