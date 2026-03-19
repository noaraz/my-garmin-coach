from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.api.routers.sync import _get_garmin_sync_service
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import ScheduledWorkout


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="mock_sync_service")
def mock_sync_service_fixture() -> MagicMock:
    """Return a MagicMock that stands in for SyncOrchestrator."""
    svc = MagicMock()
    svc.push_workout.return_value = "garmin-abc-123"
    svc.schedule_workout.return_value = None
    return svc


_TEST_USER = User(id=1, email="test@example.com", is_active=True)


async def _mock_get_current_user() -> User:
    return _TEST_USER


@pytest.fixture(name="client")
async def client_fixture(
    session: AsyncSession, mock_sync_service: MagicMock
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with DB, sync service, and auth all overridden."""
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[_get_garmin_sync_service] = lambda: mock_sync_service
    app.dependency_overrides[get_current_user] = _mock_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


async def _make_scheduled_workout(
    session: AsyncSession,
    *,
    sync_status: str = "pending",
    garmin_workout_id: str | None = None,
) -> ScheduledWorkout:
    """Helper: insert a ScheduledWorkout row and return it."""
    sw = ScheduledWorkout(
        date=date(2026, 3, 10),
        sync_status=sync_status,
        garmin_workout_id=garmin_workout_id,
        user_id=1,  # must match _TEST_USER.id for user-scoped queries
    )
    session.add(sw)
    await session.commit()
    await session.refresh(sw)
    return sw


# ---------------------------------------------------------------------------
# POST /api/v1/sync/{workout_id}
# ---------------------------------------------------------------------------


class TestSyncSingle:
    async def test_sync_single_returns_200_with_sync_status(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/v1/sync/:id with an existing workout returns 200 and synced status."""
        # Arrange
        sw = await _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.sync_workout.return_value = "garmin-xyz-999"

        # Act
        response = await client.post(f"/api/v1/sync/{sw.id}")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == sw.id
        assert body["sync_status"] == "synced"
        assert body["garmin_workout_id"] == "garmin-xyz-999"

    async def test_sync_single_not_found_returns_404(
        self,
        client: AsyncClient,
    ) -> None:
        """POST /api/v1/sync/:id for a non-existent workout returns 404."""
        response = await client.post("/api/v1/sync/9999")
        assert response.status_code == 404

    async def test_sync_single_when_sync_raises_marks_failed(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/v1/sync/:id returns 200 with sync_status=failed when sync errors."""
        # Arrange
        sw = await _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.sync_workout.side_effect = RuntimeError("Garmin unavailable")

        # Act
        response = await client.post(f"/api/v1/sync/{sw.id}")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == sw.id
        assert body["sync_status"] == "failed"

    async def test_sync_single_persists_status_to_db(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/v1/sync/:id persists the updated sync_status in the DB."""
        # Arrange
        sw = await _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.sync_workout.return_value = "garmin-persisted"

        # Act
        await client.post(f"/api/v1/sync/{sw.id}")

        # Assert — reload from DB
        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_workout_id == "garmin-persisted"

    async def test_sync_single_resync_deletes_old_garmin_workout(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Re-syncing an already-synced workout deletes the old Garmin workout first."""
        # Arrange — workout already has a Garmin ID from a previous sync
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="old-garmin-id"
        )
        mock_sync_service.sync_workout.return_value = "new-garmin-id"

        # Act
        response = await client.post(f"/api/v1/sync/{sw.id}")

        # Assert — old workout deleted, new one created
        assert response.status_code == 200
        mock_sync_service.delete_workout.assert_called_once_with("old-garmin-id")
        mock_sync_service.sync_workout.assert_called_once()
        body = response.json()
        assert body["garmin_workout_id"] == "new-garmin-id"

    async def test_sync_single_resync_continues_when_delete_fails(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Re-sync still creates the new workout even if deleting the old one fails."""
        # Arrange
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="stale-id"
        )
        mock_sync_service.delete_workout.side_effect = Exception("Garmin delete failed")
        mock_sync_service.sync_workout.return_value = "fresh-garmin-id"

        # Act
        response = await client.post(f"/api/v1/sync/{sw.id}")

        # Assert — sync still succeeds despite delete failure
        assert response.status_code == 200
        body = response.json()
        assert body["sync_status"] == "synced"
        assert body["garmin_workout_id"] == "fresh-garmin-id"


# ---------------------------------------------------------------------------
# POST /api/v1/sync/all
# ---------------------------------------------------------------------------


class TestSyncAll:
    async def test_sync_all_pending_returns_counts(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/v1/sync/all syncs pending+modified workouts and returns counts."""
        # Arrange — two pending, one already synced (should be skipped)
        await _make_scheduled_workout(session, sync_status="pending")
        await _make_scheduled_workout(session, sync_status="modified")
        await _make_scheduled_workout(session, sync_status="synced")

        mock_sync_service.sync_workout.return_value = "garmin-bulk-id"

        # Act
        response = await client.post("/api/v1/sync/all")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 2
        assert body["failed"] == 0

    async def test_sync_all_with_no_pending_returns_zero_counts(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        """POST /api/v1/sync/all with no pending workouts returns synced=0 failed=0."""
        await _make_scheduled_workout(session, sync_status="synced")

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 0
        assert body["failed"] == 0

    async def test_sync_all_counts_failures(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/v1/sync/all tallies failures when sync raises."""
        # Arrange
        await _make_scheduled_workout(session, sync_status="pending")
        await _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.sync_workout.side_effect = RuntimeError("boom")

        # Act
        response = await client.post("/api/v1/sync/all")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 0
        assert body["failed"] == 2


# ---------------------------------------------------------------------------
# GET /api/v1/sync/status
# ---------------------------------------------------------------------------


class TestSyncStatus:
    async def test_sync_status_returns_all_workouts(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        """GET /api/v1/sync/status returns all scheduled workouts with sync info."""
        # Arrange
        sw1 = await _make_scheduled_workout(session, sync_status="pending")
        sw2 = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="garmin-001"
        )

        # Act
        response = await client.get("/api/v1/sync/status")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        ids = {item["id"] for item in body}
        assert sw1.id in ids
        assert sw2.id in ids

    async def test_sync_status_includes_required_fields(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        """GET /api/v1/sync/status items contain id, date, sync_status, garmin_workout_id."""
        await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="garmin-abc"
        )

        response = await client.get("/api/v1/sync/status")

        assert response.status_code == 200
        item = response.json()[0]
        assert "id" in item
        assert "date" in item
        assert "sync_status" in item
        assert "garmin_workout_id" in item
        assert item["sync_status"] == "synced"
        assert item["garmin_workout_id"] == "garmin-abc"

    async def test_sync_status_empty_when_no_workouts(
        self,
        client: AsyncClient,
    ) -> None:
        """GET /api/v1/sync/status returns empty list when no workouts exist."""
        response = await client.get("/api/v1/sync/status")
        assert response.status_code == 200
        assert response.json() == []
