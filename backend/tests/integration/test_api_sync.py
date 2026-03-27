from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.api.routers.sync import _get_garmin_sync_service
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import AthleteProfile, ScheduledWorkout, WorkoutTemplate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="mock_sync_service")
def mock_sync_service_fixture() -> MagicMock:
    """Return a MagicMock that stands in for SyncOrchestrator."""
    svc = MagicMock()
    svc.push_workout = AsyncMock(return_value="garmin-abc-123")
    svc.sync_workout = AsyncMock(return_value=("garmin-abc-123", "sched-abc-123"))
    svc.schedule_workout.return_value = None
    # get_workouts returns empty by default — tests that need dedup override this
    svc.get_workouts.return_value = []
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
    completed: bool = False,
    workout_date: date = date(2026, 3, 10),
) -> ScheduledWorkout:
    """Helper: insert a ScheduledWorkout row and return it."""
    sw = ScheduledWorkout(
        date=workout_date,
        sync_status=sync_status,
        garmin_workout_id=garmin_workout_id,
        completed=completed,
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
        mock_sync_service.sync_workout.return_value = ("garmin-xyz-999", "sched-xyz-999")

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
        mock_sync_service.sync_workout.return_value = ("garmin-persisted", "sched-persisted")

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
        mock_sync_service.sync_workout.return_value = ("new-garmin-id", "sched-new-id")

        # Act
        response = await client.post(f"/api/v1/sync/{sw.id}")

        # Assert — old workout deleted, new one created
        assert response.status_code == 200
        mock_sync_service.delete_workout.assert_called_once_with("old-garmin-id")
        mock_sync_service.sync_workout.assert_called_once()
        body = response.json()
        assert body["garmin_workout_id"] == "new-garmin-id"

    async def test_sync_single_resync_skips_push_when_delete_fails(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Re-sync skips push and marks failed when deleting the old workout fails.

        This prevents orphaned duplicates on Garmin: if we can't delete the old
        workout, pushing a new one would leave two copies on Garmin with no way
        to clean up the old one.
        """
        # Arrange
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="stale-id"
        )
        mock_sync_service.delete_workout.side_effect = Exception("500 Server Error")
        mock_sync_service.sync_workout.return_value = ("fresh-garmin-id", "sched-fresh-id")

        # Act
        response = await client.post(f"/api/v1/sync/{sw.id}")

        # Assert — push skipped, status failed, old garmin_workout_id retained
        assert response.status_code == 200
        body = response.json()
        assert body["sync_status"] == "failed"
        assert body["garmin_workout_id"] == "stale-id"
        mock_sync_service.sync_workout.assert_not_called()

    async def test_sync_single_resync_proceeds_when_delete_returns_404(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """404 on delete means the workout is already gone — clear ID and push."""
        # Arrange
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="stale-id"
        )
        mock_sync_service.delete_workout.side_effect = Exception(
            "404 Client Error: Not Found"
        )
        mock_sync_service.sync_workout.return_value = ("fresh-garmin-id", "sched-fresh-id")

        # Act
        response = await client.post(f"/api/v1/sync/{sw.id}")

        # Assert — push proceeds, new ID assigned
        assert response.status_code == 200
        body = response.json()
        assert body["garmin_workout_id"] == "fresh-garmin-id"
        assert body["sync_status"] == "synced"
        mock_sync_service.sync_workout.assert_called_once()

    async def test_sync_single_resync_clears_id_only_on_successful_delete(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """garmin_workout_id is only cleared after a successful Garmin delete."""
        # Arrange
        sw = await _make_scheduled_workout(
            session, sync_status="modified", garmin_workout_id="old-garmin-id"
        )
        mock_sync_service.sync_workout.return_value = ("new-garmin-id", "sched-new-id")

        # Act
        response = await client.post(f"/api/v1/sync/{sw.id}")

        # Assert — old deleted, new pushed, ID updated
        assert response.status_code == 200
        body = response.json()
        assert body["garmin_workout_id"] == "new-garmin-id"
        assert body["sync_status"] == "synced"
        mock_sync_service.delete_workout.assert_called_once_with("old-garmin-id")


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

        mock_sync_service.sync_workout.return_value = ("garmin-bulk-id", "sched-bulk-id")

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

    async def test_sync_all_deletes_garmin_workout_for_completed_workouts(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """sync_all deletes the Garmin scheduled workout for completed+paired workouts."""
        # Arrange — a previously synced workout that got paired after the run
        sw = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="garmin-paired-id",
            completed=True,
            workout_date=date(2026, 3, 10),
        )

        # Act
        response = await client.post("/api/v1/sync/all?fetch_days=30")

        # Assert — response OK, and Garmin delete was called
        assert response.status_code == 200
        mock_sync_service.delete_workout.assert_called_with("garmin-paired-id")

        # garmin_workout_id should be cleared in DB
        await session.refresh(sw)
        assert sw.garmin_workout_id is None

    async def test_sync_all_clears_garmin_id_of_past_paired_workouts(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """sync_all retroactively cleans up past paired workouts still holding garmin_workout_id."""
        # Arrange — two completed workouts with stale garmin IDs (paired in a prior sync)
        sw1 = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="old-garmin-1",
            completed=True,
            workout_date=date(2026, 3, 8),
        )
        sw2 = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="old-garmin-2",
            completed=True,
            workout_date=date(2026, 3, 9),
        )

        # Act
        await client.post("/api/v1/sync/all?fetch_days=30")

        # Assert — both cleared
        await session.refresh(sw1)
        await session.refresh(sw2)
        assert sw1.garmin_workout_id is None
        assert sw2.garmin_workout_id is None

    async def test_sync_all_continues_when_garmin_delete_fails(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """sync_all response is still 200 even if Garmin delete raises during cleanup."""
        # Arrange — completed workout with garmin ID, but Garmin delete will fail
        await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="failing-garmin-id",
            completed=True,
        )
        mock_sync_service.delete_workout.side_effect = RuntimeError("Garmin unreachable")

        # Act
        response = await client.post("/api/v1/sync/all?fetch_days=30")

        # Assert — still returns 200, failure swallowed
        assert response.status_code == 200

    async def test_sync_all_is_idempotent_when_garmin_id_already_cleared(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Second sync after cleanup is a no-op: garmin_workout_id=None means nothing to delete."""
        # Arrange — workout already cleaned up by a previous sync (garmin_workout_id already None)
        # This is the state after the first cleanup sweep: completed=True, sync_status="synced",
        # garmin_workout_id=None
        await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id=None,
            completed=True,
        )

        # Act
        await client.post("/api/v1/sync/all?fetch_days=30")

        # Assert — no Garmin delete called; workout not in PENDING_STATUSES so not re-pushed either
        mock_sync_service.delete_workout.assert_not_called()

    async def test_sync_all_does_not_delete_non_completed_synced_workout(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """A synced-but-not-yet-completed workout must NOT be deleted during cleanup."""
        # Arrange — workout pushed to Garmin but run not yet done
        sw = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="active-garmin-id",
            completed=False,
        )
        mock_sync_service.sync_workout.return_value = ("garmin-skip", "sched-skip")

        # Act
        await client.post("/api/v1/sync/all?fetch_days=30")

        # Assert — garmin_workout_id untouched
        await session.refresh(sw)
        assert sw.garmin_workout_id == "active-garmin-id"

    async def test_sync_all_does_not_delete_workout_outside_date_window(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Completed workout outside fetch_days window is not touched by the cleanup sweep."""
        from datetime import timedelta

        from src.db.models import ScheduledWorkout as SW  # local alias avoids confusion

        # Arrange — completed workout 40 days ago, fetch_days=30 means it's outside the window
        old_date = date.today() - timedelta(days=40)
        sw = SW(
            date=old_date,
            sync_status="synced",
            garmin_workout_id="old-out-of-window",
            completed=True,
            user_id=1,
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        # Act — fetch_days=30, so old_date is outside the window
        await client.post("/api/v1/sync/all?fetch_days=30")

        # Assert — garmin_workout_id NOT cleared
        await session.refresh(sw)
        assert sw.garmin_workout_id == "old-out-of-window"

    async def test_sync_all_continues_cleanup_after_single_delete_failure(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """If one Garmin delete fails in the batch, the rest still succeed."""
        # Arrange — two completed workouts; first delete fails, second should still be cleared
        sw1 = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="garmin-fail",
            completed=True,
            workout_date=date(2026, 3, 8),
        )
        sw2 = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="garmin-ok",
            completed=True,
            workout_date=date(2026, 3, 9),
        )

        def _delete_side_effect(garmin_id: str) -> None:
            if garmin_id == "garmin-fail":
                raise RuntimeError("rate limited")
            # "garmin-ok" succeeds silently

        mock_sync_service.delete_workout.side_effect = _delete_side_effect

        # Act
        response = await client.post("/api/v1/sync/all?fetch_days=30")

        # Assert
        assert response.status_code == 200
        await session.refresh(sw1)
        await session.refresh(sw2)
        # sw1 failed → ID retained
        assert sw1.garmin_workout_id == "garmin-fail"
        # sw2 succeeded → ID cleared
        assert sw2.garmin_workout_id is None

    async def test_sync_all_links_existing_garmin_workout_before_push(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """sync_all deduplicates: if a Garmin workout matches by name, delete it before push."""
        # Arrange — pending workout with no garmin_workout_id, but Garmin has a matching one
        template = WorkoutTemplate(name="Easy Run", user_id=1, sport_type="running")
        session.add(template)
        await session.flush()
        sw = ScheduledWorkout(
            date=date(2026, 3, 10),
            sync_status="pending",
            garmin_workout_id=None,
            user_id=1,
            workout_template_id=template.id,
        )
        session.add(sw)
        await session.commit()

        mock_sync_service.get_workouts.return_value = [
            {"workoutId": "orphan-gw-123", "workoutName": "Easy Run"},
        ]
        mock_sync_service.sync_workout.return_value = ("new-gw-456", "sched-new-gw-456")

        # Act
        response = await client.post("/api/v1/sync/all")

        # Assert — the orphaned Garmin workout was deleted before pushing
        assert response.status_code == 200
        mock_sync_service.delete_workout.assert_any_call("orphan-gw-123")
        body = response.json()
        assert body["synced"] == 1

    async def test_sync_all_cleans_up_orphaned_garmin_workouts(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """sync_all deletes Garmin workouts that are orphaned but match our template names."""
        # Arrange — no pending workouts, but an orphaned Garmin workout exists
        template = WorkoutTemplate(name="Tempo Run", user_id=1, sport_type="running")
        session.add(template)
        await session.commit()

        mock_sync_service.get_workouts.return_value = [
            {"workoutId": "orphan-99", "workoutName": "Tempo Run"},
        ]

        # Act
        response = await client.post("/api/v1/sync/all")

        # Assert — orphan deleted
        assert response.status_code == 200
        mock_sync_service.delete_workout.assert_any_call("orphan-99")

    async def test_sync_all_does_not_delete_user_created_garmin_workouts(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """sync_all orphan cleanup ignores Garmin workouts whose names don't match our templates."""
        # Arrange — Garmin has a workout with a name we don't own
        template = WorkoutTemplate(name="Easy Run", user_id=1, sport_type="running")
        session.add(template)
        await session.commit()

        mock_sync_service.get_workouts.return_value = [
            {"workoutId": "user-custom-99", "workoutName": "My Weekend Fun Run"},
        ]

        # Act
        response = await client.post("/api/v1/sync/all")

        # Assert — user's workout NOT deleted
        assert response.status_code == 200
        mock_sync_service.delete_workout.assert_not_called()

    async def test_sync_all_handles_get_workouts_failure_gracefully(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """sync_all still succeeds if get_workouts() raises."""
        # Arrange
        await _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.get_workouts.side_effect = RuntimeError("Garmin API down")
        mock_sync_service.sync_workout.return_value = ("gw-ok", "sched-gw-ok")

        # Act
        response = await client.post("/api/v1/sync/all")

        # Assert — sync proceeds without dedup
        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 1

    async def test_sync_all_reconciles_stale_garmin_ids(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """GET schedule returns no entry for our date → re-schedule (1 POST), reconciled=1."""
        future_date = date.today() + timedelta(days=30)
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="tmpl-999", workout_date=future_date
        )
        sw.garmin_schedule_id = "sched-old-999"
        session.add(sw)
        await session.commit()

        # GET returns entries but NOT for our date → date missing from calendar
        mock_sync_service.get_scheduled_workout_by_id.return_value = []
        mock_sync_service.reschedule_workout.return_value = "sched-new-999"

        # Act
        response = await client.post("/api/v1/sync/all")

        # Assert: calendar entry re-scheduled, sync_status unchanged, new schedule ID stored
        assert response.status_code == 200
        body = response.json()
        assert body["reconciled"] == 1
        assert body["synced"] == 0  # no full re-push needed

        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_schedule_id == "sched-new-999"

    async def test_sync_all_skips_reconciliation_when_workout_already_on_calendar(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """GET schedule returns our date → already on calendar → skip (reconciled=0, 0 POST calls)."""
        future_date = date.today() + timedelta(days=30)
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="tmpl-777", workout_date=future_date
        )
        sw.garmin_schedule_id = "sched-777"
        session.add(sw)
        await session.commit()

        # GET returns the date → workout is already on the calendar
        mock_sync_service.get_scheduled_workout_by_id.return_value = [{"date": str(future_date)}]

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        body = response.json()
        assert body["reconciled"] == 0
        assert body["synced"] == 0
        mock_sync_service.reschedule_workout.assert_not_called()

        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_schedule_id == "sched-777"  # unchanged

    async def test_sync_all_does_not_reset_synced_workout_when_id_exists_on_garmin(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Workouts whose garmin_workout_id IS in Garmin's list are not touched."""
        valid_id = "valid-garmin-456"
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id=valid_id
        )
        mock_sync_service.get_workouts.return_value = [
            {"workoutId": valid_id, "workoutName": "My Workout"}
        ]

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        assert response.json()["synced"] == 0  # not re-pushed
        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_workout_id == valid_id

    async def test_sync_all_skips_reconciliation_when_get_workouts_fails(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """get_workouts() failure (used for dedup) does not affect sync_all returning 200."""
        await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="stale-id"
        )
        mock_sync_service.get_workouts.side_effect = RuntimeError("429")

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        assert response.json()["synced"] == 0  # nothing re-pushed

    @pytest.mark.parametrize("error_code", ["404", "403"])
    async def test_sync_all_marks_template_inaccessible_as_modified_for_repush(
        self,
        error_code: str,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """GET schedule returns 404/403 → template inaccessible → mark modified → full re-push."""
        future_date = date.today() + timedelta(days=15)
        sw = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="tmpl-deleted",
            workout_date=future_date,
        )
        sw.garmin_schedule_id = "sched-old"
        session.add(sw)
        await session.commit()

        mock_sync_service.get_scheduled_workout_by_id.side_effect = Exception(
            f"HTTP Error {error_code}: "
        )
        mock_sync_service.sync_workout = AsyncMock(return_value=("tmpl-new", "sched-new"))

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 1  # full re-push succeeded
        assert body["reconciled"] == 0  # no reschedule, went straight to re-push
        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_workout_id == "tmpl-new"

    async def test_sync_all_falls_back_to_full_repush_when_reschedule_fails(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """GET returns date-missing, reschedule raises 404 → marked modified → full re-push."""
        future_date = date.today() + timedelta(days=10)
        sw = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="tmpl-gone",
            workout_date=future_date,
        )
        sw.garmin_schedule_id = "sched-old"
        session.add(sw)
        await session.commit()

        mock_sync_service.get_scheduled_workout_by_id.return_value = []  # date not found
        mock_sync_service.reschedule_workout.side_effect = Exception("404 Not Found")
        mock_sync_service.sync_workout = AsyncMock(return_value=("tmpl-new", "sched-new"))

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 1  # full re-push succeeded
        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_workout_id == "tmpl-new"


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


# ---------------------------------------------------------------------------
# POST /api/v1/sync/all — Activity Fetch portion
# ---------------------------------------------------------------------------


class TestSyncAllActivityFetch:
    """Tests for the activity fetch/match portion of POST /api/v1/sync/all."""

    async def test_sync_all_returns_activities_fetched_and_matched(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """sync_all fetches and matches activities, populating counts in the response."""
        # Arrange: adapter returns one running activity dated 7 days ago
        recent_date = datetime.now(timezone.utc).date() - timedelta(days=7)
        mock_sync_service.adapter.get_activities_by_date.return_value = [
            {
                "activityId": 111222333,
                "activityType": {"typeKey": "running"},
                "activityName": "Morning Run",
                "startTimeLocal": f"{recent_date.isoformat()}T08:00:00",
                "duration": 3600.0,
                "distance": 10000.0,
                "averageSpeed": 2.78,
            }
        ]
        # Create a scheduled workout on the same date so match_activities pairs them
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        sw = ScheduledWorkout(
            date=recent_date,
            workout_template_id=template.id,
            user_id=1,
            sync_status="synced",
        )
        session.add(sw)
        await session.commit()

        # Act
        response = await client.post("/api/v1/sync/all")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["activities_fetched"] == 1
        assert body["activities_matched"] == 1
        assert body["fetch_error"] is None

    async def test_sync_all_fetch_error_is_returned_in_response(
        self,
        client: AsyncClient,
        mock_sync_service: MagicMock,
    ) -> None:
        """When the Garmin adapter raises, sync_all returns fetch_error (best-effort, still 200)."""
        mock_sync_service.adapter.get_activities_by_date.side_effect = RuntimeError(
            "Garmin timeout"
        )

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        body = response.json()
        assert body["activities_fetched"] == 0
        assert body["activities_matched"] == 0
        assert body["fetch_error"] == "Activity fetch failed — please retry"

    async def test_sync_all_deduplicates_activities(
        self,
        client: AsyncClient,
        mock_sync_service: MagicMock,
    ) -> None:
        """Fetching the same Garmin activity twice only stores it once (dedup by garmin_activity_id)."""
        raw_activity = {
            "activityId": 999888777,
            "activityType": {"typeKey": "running"},
            "activityName": "Easy Run",
            "startTimeLocal": "2026-03-10T07:00:00",
            "duration": 1800.0,
            "distance": 5000.0,
            "averageSpeed": 2.78,
        }
        mock_sync_service.adapter.get_activities_by_date.return_value = [raw_activity]

        # First call — stores the activity
        response1 = await client.post("/api/v1/sync/all")
        assert response1.status_code == 200
        assert response1.json()["activities_fetched"] == 1

        # Second call with same activity — still fetches 1 from Garmin, but stores 0 (dedup)
        response2 = await client.post("/api/v1/sync/all")
        assert response2.status_code == 200
        assert response2.json()["activities_fetched"] == 1


# ---------------------------------------------------------------------------
# Token persistence after sync (prevents repeated OAuth2 exchange → 429)
# ---------------------------------------------------------------------------


class TestSyncTokenPersistence:
    """garth's refreshed OAuth2 token is persisted back to DB after each sync.

    Without this, every sync loads the same expired token from DB and triggers
    a new OAuth2 exchange at the exchange endpoint.  Frequent syncs hit Garmin's
    rate limit (429) on that endpoint.
    """

    async def test_sync_all_persists_refreshed_token_to_db(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """After sync_all, the profile's encrypted token reflects garth's current state."""
        from src.garmin.encryption import decrypt_token, encrypt_token

        secret = "dev-secret-change-in-prod"
        initial_token = '{"oauth1_token": "old", "oauth2_token": null}'
        refreshed_token = '{"oauth1_token": "old", "oauth2_token": {"access_token": "fresh"}}'

        profile = AthleteProfile(
            user_id=1,
            garmin_connected=True,
            garmin_oauth_token_encrypted=encrypt_token(1, secret, initial_token),
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        mock_sync_service.adapter.dump_token.return_value = refreshed_token

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        await session.refresh(profile)
        assert profile.garmin_oauth_token_encrypted is not None
        stored = decrypt_token(1, secret, profile.garmin_oauth_token_encrypted)
        assert stored == refreshed_token

    async def test_sync_all_continues_when_token_persist_fails(
        self,
        client: AsyncClient,
        mock_sync_service: MagicMock,
    ) -> None:
        """Token persistence failure is non-critical — sync_all still returns 200."""
        mock_sync_service.adapter.dump_token.side_effect = RuntimeError("garth error")

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200

    async def test_sync_single_persists_refreshed_token_to_db(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """After sync_single, the profile's encrypted token reflects garth's current state."""
        from src.garmin.encryption import decrypt_token, encrypt_token

        secret = "dev-secret-change-in-prod"
        initial_token = '{"oauth1_token": "old", "oauth2_token": null}'
        refreshed_token = '{"oauth1_token": "old", "oauth2_token": {"access_token": "fresh2"}}'

        profile = AthleteProfile(
            user_id=1,
            garmin_connected=True,
            garmin_oauth_token_encrypted=encrypt_token(1, secret, initial_token),
        )
        session.add(profile)
        await session.commit()

        sw = await _make_scheduled_workout(session, sync_status="pending")
        mock_sync_service.adapter.dump_token.return_value = refreshed_token

        response = await client.post(f"/api/v1/sync/{sw.id}")

        assert response.status_code == 200
        await session.refresh(profile)
        assert profile.garmin_oauth_token_encrypted is not None
        stored = decrypt_token(1, secret, profile.garmin_oauth_token_encrypted)
        assert stored == refreshed_token
