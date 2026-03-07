from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.api.app import create_app
from src.api.dependencies import get_session, get_sync_service
from src.db.models import ScheduledWorkout


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="mock_sync_service")
def mock_sync_service_fixture() -> MagicMock:
    """Return a MagicMock that stands in for SyncOrchestrator."""
    svc = MagicMock()
    # Default: push_workout returns a garmin ID, schedule_workout succeeds
    svc.push_workout.return_value = "garmin-abc-123"
    svc.schedule_workout.return_value = None
    return svc


@pytest.fixture(name="client")
def client_fixture(session: Session, mock_sync_service: MagicMock) -> TestClient:
    """TestClient with DB and sync service both overridden."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_sync_service] = lambda: mock_sync_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _make_scheduled_workout(
    session: Session,
    *,
    sync_status: str = "pending",
    garmin_workout_id: str | None = None,
) -> ScheduledWorkout:
    """Helper: insert a ScheduledWorkout row and return it."""
    sw = ScheduledWorkout(
        date=date(2026, 3, 10),
        sync_status=sync_status,
        garmin_workout_id=garmin_workout_id,
    )
    session.add(sw)
    session.commit()
    session.refresh(sw)
    return sw


# ---------------------------------------------------------------------------
# POST /api/sync/{workout_id}
# ---------------------------------------------------------------------------


class TestSyncSingle:
    def test_sync_single_returns_200_with_sync_status(
        self,
        client: TestClient,
        session: Session,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/sync/:id with an existing workout returns 200 and synced status."""
        # Arrange
        sw = _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.sync_workout.return_value = "garmin-xyz-999"

        # Act
        response = client.post(f"/api/sync/{sw.id}")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == sw.id
        assert body["sync_status"] == "synced"
        assert body["garmin_workout_id"] == "garmin-xyz-999"

    def test_sync_single_not_found_returns_404(
        self,
        client: TestClient,
    ) -> None:
        """POST /api/sync/:id for a non-existent workout returns 404."""
        # Act
        response = client.post("/api/sync/9999")

        # Assert
        assert response.status_code == 404

    def test_sync_single_when_sync_raises_marks_failed(
        self,
        client: TestClient,
        session: Session,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/sync/:id returns 200 with sync_status=failed when sync errors."""
        # Arrange
        sw = _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.sync_workout.side_effect = RuntimeError("Garmin unavailable")

        # Act
        response = client.post(f"/api/sync/{sw.id}")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == sw.id
        assert body["sync_status"] == "failed"

    def test_sync_single_persists_status_to_db(
        self,
        client: TestClient,
        session: Session,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/sync/:id persists the updated sync_status in the DB."""
        # Arrange
        sw = _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.sync_workout.return_value = "garmin-persisted"

        # Act
        client.post(f"/api/sync/{sw.id}")

        # Assert — reload from DB
        session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_workout_id == "garmin-persisted"


# ---------------------------------------------------------------------------
# POST /api/sync/all
# ---------------------------------------------------------------------------


class TestSyncAll:
    def test_sync_all_pending_returns_counts(
        self,
        client: TestClient,
        session: Session,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/sync/all syncs pending+modified workouts and returns counts."""
        # Arrange — two pending, one already synced (should be skipped)
        _make_scheduled_workout(session, sync_status="pending")
        _make_scheduled_workout(session, sync_status="modified")
        _make_scheduled_workout(session, sync_status="synced")

        mock_sync_service.sync_workout.return_value = "garmin-bulk-id"

        # Act
        response = client.post("/api/sync/all")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 2
        assert body["failed"] == 0

    def test_sync_all_with_no_pending_returns_zero_counts(
        self,
        client: TestClient,
        session: Session,
    ) -> None:
        """POST /api/sync/all with no pending workouts returns synced=0 failed=0."""
        # Arrange — only a synced workout
        _make_scheduled_workout(session, sync_status="synced")

        # Act
        response = client.post("/api/sync/all")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 0
        assert body["failed"] == 0

    def test_sync_all_counts_failures(
        self,
        client: TestClient,
        session: Session,
        mock_sync_service: MagicMock,
    ) -> None:
        """POST /api/sync/all tallies failures when sync raises."""
        # Arrange
        _make_scheduled_workout(session, sync_status="pending")
        _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.sync_workout.side_effect = RuntimeError("boom")

        # Act
        response = client.post("/api/sync/all")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 0
        assert body["failed"] == 2


# ---------------------------------------------------------------------------
# GET /api/sync/status
# ---------------------------------------------------------------------------


class TestSyncStatus:
    def test_sync_status_returns_all_workouts(
        self,
        client: TestClient,
        session: Session,
    ) -> None:
        """GET /api/sync/status returns all scheduled workouts with sync info."""
        # Arrange
        sw1 = _make_scheduled_workout(session, sync_status="pending")
        sw2 = _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="garmin-001"
        )

        # Act
        response = client.get("/api/sync/status")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2

        ids = {item["id"] for item in body}
        assert sw1.id in ids
        assert sw2.id in ids

    def test_sync_status_includes_required_fields(
        self,
        client: TestClient,
        session: Session,
    ) -> None:
        """GET /api/sync/status items contain id, date, sync_status, garmin_workout_id."""
        # Arrange
        _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="garmin-abc"
        )

        # Act
        response = client.get("/api/sync/status")

        # Assert
        assert response.status_code == 200
        item = response.json()[0]
        assert "id" in item
        assert "date" in item
        assert "sync_status" in item
        assert "garmin_workout_id" in item
        assert item["sync_status"] == "synced"
        assert item["garmin_workout_id"] == "garmin-abc"

    def test_sync_status_empty_when_no_workouts(
        self,
        client: TestClient,
    ) -> None:
        """GET /api/sync/status returns empty list when no workouts exist."""
        # Act
        response = client.get("/api/sync/status")

        # Assert
        assert response.status_code == 200
        assert response.json() == []
