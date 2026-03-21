"""Unit tests for session safety in sync operations.

SQLAlchemy AsyncSession is NOT concurrency-safe. Using asyncio.gather() with
the same session instance in multiple tasks causes InvalidRequestError.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.routers.sync import sync_modified_workouts
from src.auth.models import User
from src.db.models import ScheduledWorkout


@pytest.mark.asyncio
async def test_sync_modified_workouts_uses_sequential_not_concurrent_session_access() -> None:
    """sync_modified_workouts must call _sync_and_persist sequentially, not concurrently.

    Concurrent session access via asyncio.gather() causes InvalidRequestError.
    This test verifies that when multiple workouts are present, they are processed
    sequentially (each completes before the next starts) rather than concurrently.
    """
    # Arrange — track call order with a counter
    call_order: list[tuple[int, str]] = []  # (workout_id, event_type)

    async def mock_sync_and_persist(
        session: AsyncSession,
        sync_service: MagicMock,
        workout: ScheduledWorkout,
        hr_zone_map: dict | None = None,
        pace_zone_map: dict | None = None,
        templates: dict | None = None,
    ) -> str | None:
        workout_id = workout.id or 0
        call_order.append((workout_id, "start"))
        await asyncio.sleep(0.01)  # Simulate async work
        call_order.append((workout_id, "end"))
        return f"garmin-{workout_id}"

    # Mock session
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.exec = AsyncMock(return_value=AsyncMock(first=AsyncMock(return_value=None)))
    mock_session.commit = AsyncMock()

    # Mock sync service
    mock_sync_service = MagicMock()

    # Mock user
    mock_user = User(id=1, email="test@example.com", is_active=True)

    # Create 3 workouts
    workouts = [
        ScheduledWorkout(id=1, sync_status="modified", user_id=1),
        ScheduledWorkout(id=2, sync_status="modified", user_id=1),
        ScheduledWorkout(id=3, sync_status="modified", user_id=1),
    ]

    # Patch the helper functions
    async def mock_get_zone_maps(session: AsyncSession, user: User) -> tuple[dict, dict]:
        return {}, {}

    async def mock_get_by_status(
        session: AsyncSession, statuses: tuple[str, ...], user_id: int
    ) -> list[ScheduledWorkout]:
        return workouts

    async def mock_preload_templates(
        session: AsyncSession, workouts: list[ScheduledWorkout]
    ) -> dict:
        return {}

    # Monkey-patch the module
    import src.api.routers.sync as sync_module
    original_get_zone_maps = sync_module._get_zone_maps
    original_get_by_status = sync_module.scheduled_workout_repository.get_by_status
    original_preload_templates = sync_module._preload_templates
    original_sync_and_persist = sync_module._sync_and_persist

    try:
        sync_module._get_zone_maps = mock_get_zone_maps
        sync_module.scheduled_workout_repository.get_by_status = mock_get_by_status
        sync_module._preload_templates = mock_preload_templates
        sync_module._sync_and_persist = mock_sync_and_persist

        # Act
        await sync_modified_workouts(mock_session, mock_sync_service, mock_user)

        # Assert — sequential execution means each workout completes before next starts
        # With asyncio.gather(), we would see: [(1,'start'), (2,'start'), (3,'start'), (1,'end'), ...]
        # With sequential for-loop, we see: [(1,'start'), (1,'end'), (2,'start'), (2,'end'), ...]
        assert len(call_order) == 6, f"Expected 6 events (3 start + 3 end), got {len(call_order)}"

        # Check that each workout completes before the next starts
        assert call_order[0] == (1, "start"), "Workout 1 should start first"
        assert call_order[1] == (1, "end"), "Workout 1 should complete before workout 2 starts"
        assert call_order[2] == (2, "start"), "Workout 2 should start after workout 1 completes"
        assert call_order[3] == (2, "end"), "Workout 2 should complete before workout 3 starts"
        assert call_order[4] == (3, "start"), "Workout 3 should start after workout 2 completes"
        assert call_order[5] == (3, "end"), "Workout 3 should complete last"

    finally:
        # Restore originals
        sync_module._get_zone_maps = original_get_zone_maps
        sync_module.scheduled_workout_repository.get_by_status = original_get_by_status
        sync_module._preload_templates = original_preload_templates
        sync_module._sync_and_persist = original_sync_and_persist
