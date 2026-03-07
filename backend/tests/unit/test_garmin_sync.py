from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.garmin.exceptions import GarminAuthError
from src.garmin.sync_service import GarminSyncService
from src.services.sync_orchestrator import SyncOrchestrator


# ---------------------------------------------------------------------------
# Session / login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_login_success_establishes_session(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        service = GarminSyncService(mock_garmin_client)

        # Act
        service.login("user@example.com", "password123")

        # Assert
        mock_garmin_client.login.assert_called_once_with(
            "user@example.com", "password123"
        )

    def test_login_failure_raises_garmin_auth_error(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        mock_garmin_client.login.side_effect = Exception("Auth failed")
        service = GarminSyncService(mock_garmin_client)

        # Act / Assert
        with pytest.raises(GarminAuthError):
            service.login("user@example.com", "wrong_password")


# ---------------------------------------------------------------------------
# Push / schedule / update / delete
# ---------------------------------------------------------------------------


class TestPushNew:
    def test_push_new_returns_garmin_workout_id(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        mock_garmin_client.add_workout.return_value = {"workoutId": "garmin-12345"}
        service = GarminSyncService(mock_garmin_client)
        formatted_workout = {"workoutName": "Easy Run", "sportType": {}}

        # Act
        garmin_id = service.push_workout(formatted_workout)

        # Assert
        assert garmin_id == "garmin-12345"
        mock_garmin_client.add_workout.assert_called_once_with(formatted_workout)


class TestScheduleOnDate:
    def test_schedule_on_date_calls_client(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        service = GarminSyncService(mock_garmin_client)

        # Act
        service.schedule_workout("garmin-12345", "2026-03-10")

        # Assert
        mock_garmin_client.schedule_workout.assert_called_once_with(
            "garmin-12345", "2026-03-10"
        )


class TestUpdateExisting:
    def test_update_existing_calls_client(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        service = GarminSyncService(mock_garmin_client)
        formatted_workout = {"workoutName": "Updated Run"}

        # Act
        service.update_workout("garmin-12345", formatted_workout)

        # Assert
        mock_garmin_client.update_workout.assert_called_once_with(
            "garmin-12345", formatted_workout
        )


class TestDelete:
    def test_delete_calls_client(self, mock_garmin_client: MagicMock) -> None:
        # Arrange
        service = GarminSyncService(mock_garmin_client)

        # Act
        service.delete_workout("garmin-12345")

        # Assert
        mock_garmin_client.delete_workout.assert_called_once_with("garmin-12345")


# ---------------------------------------------------------------------------
# Bulk resync
# ---------------------------------------------------------------------------


class TestBulkResync:
    def test_bulk_resync_pushes_all_five_workouts(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        # Each call returns a unique workoutId
        mock_garmin_client.add_workout.side_effect = [
            {"workoutId": f"garmin-{i}"} for i in range(5)
        ]
        service = GarminSyncService(mock_garmin_client)
        workouts = [{"workoutName": f"Workout {i}"} for i in range(5)]

        # Act
        ids = service.bulk_resync(workouts)

        # Assert
        assert len(ids) == 5
        assert ids == [f"garmin-{i}" for i in range(5)]
        assert mock_garmin_client.add_workout.call_count == 5


# ---------------------------------------------------------------------------
# Rate limiting / retry
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_rate_limiting_retries_on_429_and_succeeds(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange — first two calls raise a 429-like error, third succeeds
        rate_limit_error = Exception("429 Too Many Requests")
        mock_garmin_client.add_workout.side_effect = [
            rate_limit_error,
            rate_limit_error,
            {"workoutId": "garmin-retry"},
        ]
        service = GarminSyncService(mock_garmin_client)
        formatted_workout = {"workoutName": "Tempo Run"}

        # Act — patch sleep so the test runs instantly
        with patch("src.garmin.sync_service.time.sleep"):
            garmin_id = service.push_workout(formatted_workout)

        # Assert
        assert garmin_id == "garmin-retry"
        assert mock_garmin_client.add_workout.call_count == 3


# ---------------------------------------------------------------------------
# Sync status tracking
# ---------------------------------------------------------------------------


class TestMarksSynced:
    def test_marks_synced_after_successful_push(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        mock_garmin_client.add_workout.return_value = {"workoutId": "garmin-abc"}
        service = GarminSyncService(mock_garmin_client)
        formatted_workout = {"workoutName": "Z2 Long Run"}

        # Act
        service.push_workout(formatted_workout)

        # Assert
        assert service.last_sync_status == "synced"


class TestMarksFailed:
    def test_marks_failed_after_error(self, mock_garmin_client: MagicMock) -> None:
        # Arrange — exhaust all retries
        mock_garmin_client.add_workout.side_effect = Exception("Network error")
        service = GarminSyncService(mock_garmin_client)

        # Act
        with patch("src.garmin.sync_service.time.sleep"):
            with pytest.raises(Exception):
                service.push_workout({"workoutName": "Interval"})

        # Assert
        assert service.last_sync_status == "failed"


# ---------------------------------------------------------------------------
# Skip completed workouts
# ---------------------------------------------------------------------------


class TestSkipsCompleted:
    def test_skips_completed_workout_in_bulk_resync(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange — second workout is already completed
        mock_garmin_client.add_workout.return_value = {"workoutId": "garmin-ok"}
        service = GarminSyncService(mock_garmin_client)
        workouts = [
            {"workoutName": "Run 1", "completed": False},
            {"workoutName": "Run 2", "completed": True},
            {"workoutName": "Run 3", "completed": False},
        ]

        # Act
        ids = service.bulk_resync(workouts)

        # Assert — only 2 non-completed workouts are pushed
        assert mock_garmin_client.add_workout.call_count == 2
        assert len(ids) == 2


# ---------------------------------------------------------------------------
# SyncOrchestrator
# ---------------------------------------------------------------------------


class TestSyncOrchestrator:
    def test_sync_workout_resolves_formats_pushes_schedules(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        mock_sync_service = MagicMock()
        mock_sync_service.push_workout.return_value = "garmin-orch-1"

        mock_formatter = MagicMock()
        mock_formatter.return_value = {"workoutName": "Easy Run"}

        mock_resolver = MagicMock()
        mock_resolver.return_value = [{"step": "resolved"}]

        orchestrator = SyncOrchestrator(
            sync_service=mock_sync_service,
            formatter=mock_formatter,
            resolver=mock_resolver,
        )

        resolved_steps = [{"step": "raw"}]

        # Act
        garmin_id = orchestrator.sync_workout(
            resolved_steps=resolved_steps,
            workout_name="Easy Run",
            date="2026-03-10",
        )

        # Assert
        assert garmin_id == "garmin-orch-1"
        mock_sync_service.push_workout.assert_called_once()
        mock_sync_service.schedule_workout.assert_called_once_with(
            "garmin-orch-1", "2026-03-10"
        )

    def test_resync_all_returns_synced_and_failed_counts(
        self, mock_garmin_client: MagicMock
    ) -> None:
        # Arrange
        mock_sync_service = MagicMock()
        # First two succeed, third fails
        mock_sync_service.push_workout.side_effect = [
            "garmin-1",
            "garmin-2",
            Exception("push failed"),
        ]

        mock_formatter = MagicMock()
        mock_formatter.return_value = {"workoutName": "Run"}

        mock_resolver = MagicMock()

        orchestrator = SyncOrchestrator(
            sync_service=mock_sync_service,
            formatter=mock_formatter,
            resolver=mock_resolver,
        )

        workouts = [
            {"name": "Run 1", "steps": [], "date": "2026-03-08"},
            {"name": "Run 2", "steps": [], "date": "2026-03-09"},
            {"name": "Run 3", "steps": [], "date": "2026-03-10"},
        ]

        # Act
        result = orchestrator.resync_all(workouts)

        # Assert
        assert result["synced"] == 2
        assert result["failed"] == 1
