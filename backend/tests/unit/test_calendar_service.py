from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from src.db.models import ScheduledWorkout
from src.services.calendar_service import CalendarService


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _make_workout(
    *,
    sync_status: str = "synced",
    workout_date: date = date(2026, 3, 10),
    user_id: int = 1,
) -> ScheduledWorkout:
    return ScheduledWorkout(
        id=1,
        user_id=user_id,
        date=workout_date,
        sync_status=sync_status,
        garmin_workout_id="G123" if sync_status == "synced" else None,
    )


class TestRescheduleSetsSyncStatus:
    async def test_reschedule_sets_modified_when_date_changes_and_was_synced(self) -> None:
        # Arrange
        service = CalendarService()
        workout = _make_workout(sync_status="synced", workout_date=date(2026, 3, 10))
        session = _make_session()
        session.refresh = AsyncMock(return_value=None)

        with patch("src.services.calendar_service.scheduled_workout_repository") as mock_repo:
            mock_repo.get = AsyncMock(return_value=workout)

            # Act
            await service.reschedule(session, scheduled_id=1, new_date=date(2026, 3, 15), user_id=1)

        # Assert
        assert workout.sync_status == "modified"
        assert workout.date == date(2026, 3, 15)

    async def test_reschedule_does_not_change_status_when_notes_only_updated(self) -> None:
        # Arrange
        service = CalendarService()
        workout = _make_workout(sync_status="synced", workout_date=date(2026, 3, 10))
        session = _make_session()
        session.refresh = AsyncMock(return_value=None)

        with patch("src.services.calendar_service.scheduled_workout_repository") as mock_repo:
            mock_repo.get = AsyncMock(return_value=workout)

            # Act — no new_date, only notes
            await service.reschedule(session, scheduled_id=1, new_date=None, user_id=1, notes="feeling good")

        # Assert
        assert workout.sync_status == "synced"  # unchanged
        assert workout.notes == "feeling good"

    async def test_reschedule_does_not_change_status_when_date_is_same(self) -> None:
        # Arrange
        service = CalendarService()
        workout = _make_workout(sync_status="synced", workout_date=date(2026, 3, 10))
        session = _make_session()
        session.refresh = AsyncMock(return_value=None)

        with patch("src.services.calendar_service.scheduled_workout_repository") as mock_repo:
            mock_repo.get = AsyncMock(return_value=workout)

            # Act — same date
            await service.reschedule(session, scheduled_id=1, new_date=date(2026, 3, 10), user_id=1)

        # Assert — no status change when date didn't actually move
        assert workout.sync_status == "synced"

    async def test_reschedule_does_not_change_status_when_pending(self) -> None:
        # Arrange — pending workout was never synced; stays pending
        service = CalendarService()
        workout = _make_workout(sync_status="pending", workout_date=date(2026, 3, 10))
        session = _make_session()
        session.refresh = AsyncMock(return_value=None)

        with patch("src.services.calendar_service.scheduled_workout_repository") as mock_repo:
            mock_repo.get = AsyncMock(return_value=workout)

            # Act
            await service.reschedule(session, scheduled_id=1, new_date=date(2026, 3, 17), user_id=1)

        # Assert — pending stays pending (already in sync queue)
        assert workout.sync_status == "pending"

    async def test_reschedule_does_not_change_status_when_failed(self) -> None:
        # Arrange — failed workout stays failed so sync retries it
        service = CalendarService()
        workout = _make_workout(sync_status="failed", workout_date=date(2026, 3, 10))
        session = _make_session()
        session.refresh = AsyncMock(return_value=None)

        with patch("src.services.calendar_service.scheduled_workout_repository") as mock_repo:
            mock_repo.get = AsyncMock(return_value=workout)

            # Act
            await service.reschedule(session, scheduled_id=1, new_date=date(2026, 3, 17), user_id=1)

        # Assert — failed stays failed (still in sync queue)
        assert workout.sync_status == "failed"
