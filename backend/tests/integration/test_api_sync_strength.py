"""Integration tests for strength workout push and same-day pairing.

Covers:
- Strength template sync calls sync_strength_workout (not sync_workout)
- Running template sync still calls sync_workout
- match_activities pairs strength activities with strength workouts
- match_activities does NOT pair a strength activity with a running workout
- match_activities does NOT pair a running activity with a strength workout
- ActivityFetchService.fetch_and_store stores strength_training activities
"""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.api.routers.sync import _get_garmin_sync_service
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import GarminActivity, ScheduledWorkout, WorkoutTemplate
from src.services.activity_fetch_service import ActivityFetchService

_TEST_USER = User(id=1, email="test@example.com", is_active=True)

_STRENGTH_STEPS = json.dumps([
    {
        "kind": "strength_exercise",
        "exercise_key": "back_squat",
        "garmin_category": "SQUAT",
        "garmin_name": "BARBELL_BACK_SQUAT",
        "sets": [{"reps": 5, "load": {"type": "kg", "value": 80}}] * 3,
        "note": None,
    }
])


async def _mock_get_current_user() -> User:
    return _TEST_USER


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="mock_sync_service")
def mock_sync_service_fixture() -> MagicMock:
    svc = MagicMock()
    svc.push_workout = AsyncMock(return_value="garmin-strength-001")
    svc.sync_workout = AsyncMock(return_value=("garmin-run-001", None))
    svc.sync_strength_workout = AsyncMock(return_value=("garmin-strength-001", None))
    svc.schedule_workout.return_value = None
    svc.get_workouts.return_value = []
    svc.get_calendar_items.return_value = []
    svc.adapter = MagicMock()
    return svc


@pytest.fixture(name="client")
async def client_fixture(
    session: AsyncSession, mock_sync_service: MagicMock
) -> AsyncGenerator[AsyncClient, None]:
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


async def _make_template(
    session: AsyncSession,
    *,
    sport: str = "strength",
    sport_type: str = "strength_training",
    steps: str | None = None,
) -> WorkoutTemplate:
    t = WorkoutTemplate(
        user_id=1,
        name="Lower Body",
        sport=sport,
        sport_type=sport_type,
        steps=steps or _STRENGTH_STEPS,
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def _make_scheduled_workout(
    session: AsyncSession,
    *,
    sport: str = "strength",
    template_id: int | None = None,
    sync_status: str = "pending",
    garmin_workout_id: str | None = None,
    completed: bool = False,
    workout_date: date | None = None,
    matched_activity_id: int | None = None,
) -> ScheduledWorkout:
    sw = ScheduledWorkout(
        date=workout_date or date(2026, 6, 1),
        sync_status=sync_status,
        garmin_workout_id=garmin_workout_id,
        completed=completed,
        user_id=1,
        sport=sport,
        workout_template_id=template_id,
        matched_activity_id=matched_activity_id,
    )
    session.add(sw)
    await session.commit()
    await session.refresh(sw)
    return sw


async def _make_garmin_activity(
    session: AsyncSession,
    *,
    activity_type: str = "strength_training",
    activity_date: date | None = None,
    garmin_id: str = "g-strength-001",
) -> GarminActivity:
    act = GarminActivity(
        user_id=1,
        garmin_activity_id=garmin_id,
        activity_type=activity_type,
        name="Strength Training",
        start_time=datetime.now(timezone.utc).replace(tzinfo=None),
        date=activity_date or date(2026, 6, 1),
        duration_sec=3600.0,
        distance_m=0.0,
        avg_hr=None,
        max_hr=None,
        avg_pace_sec_per_km=None,
        calories=None,
    )
    session.add(act)
    await session.commit()
    await session.refresh(act)
    return act


# ---------------------------------------------------------------------------
# Sync push — sport branch
# ---------------------------------------------------------------------------


class TestStrengthPush:
    async def test_strength_template_calls_sync_strength_workout(
        self, client: AsyncClient, session: AsyncSession, mock_sync_service: MagicMock
    ) -> None:
        """Syncing a strength workout calls sync_strength_workout, not sync_workout."""
        template = await _make_template(session, sport="strength")
        await _make_scheduled_workout(
            session, sport="strength", template_id=template.id, sync_status="pending"
        )

        with patch(
            "src.services.activity_fetch_service.activity_fetch_service.fetch_and_store",
            new_callable=AsyncMock,
        ) as mock_fetch, patch(
            "src.services.activity_fetch_service.activity_fetch_service.match_activities",
            new_callable=AsyncMock, return_value=0,
        ):
            mock_fetch.return_value = MagicMock(fetched=0, stored=0)
            r = await client.post("/api/v1/sync/all")

        assert r.status_code == 200
        mock_sync_service.sync_strength_workout.assert_called_once()
        mock_sync_service.sync_workout.assert_not_called()

    async def test_running_template_calls_sync_workout(
        self, client: AsyncClient, session: AsyncSession, mock_sync_service: MagicMock
    ) -> None:
        """Syncing a running workout calls sync_workout, not sync_strength_workout."""
        template = await _make_template(session, sport="run", sport_type="running", steps=None)
        sw = await _make_scheduled_workout(
            session, sport="run", template_id=template.id, sync_status="pending"
        )
        sw.resolved_steps = json.dumps([{"zone": 2, "duration_sec": 2700}])
        session.add(sw)
        await session.commit()

        with patch(
            "src.services.activity_fetch_service.activity_fetch_service.fetch_and_store",
            new_callable=AsyncMock,
        ) as mock_fetch, patch(
            "src.services.activity_fetch_service.activity_fetch_service.match_activities",
            new_callable=AsyncMock, return_value=0,
        ):
            mock_fetch.return_value = MagicMock(fetched=0, stored=0)
            r = await client.post("/api/v1/sync/all")

        assert r.status_code == 200
        mock_sync_service.sync_workout.assert_called_once()
        mock_sync_service.sync_strength_workout.assert_not_called()

    async def test_strength_sync_marks_workout_synced(
        self, client: AsyncClient, session: AsyncSession, mock_sync_service: MagicMock
    ) -> None:
        """After syncing, the ScheduledWorkout has sync_status=synced and garmin_workout_id set."""
        template = await _make_template(session, sport="strength")
        sw = await _make_scheduled_workout(
            session, sport="strength", template_id=template.id, sync_status="pending"
        )

        with patch(
            "src.services.activity_fetch_service.activity_fetch_service.fetch_and_store",
            new_callable=AsyncMock,
        ) as mock_fetch, patch(
            "src.services.activity_fetch_service.activity_fetch_service.match_activities",
            new_callable=AsyncMock, return_value=0,
        ):
            mock_fetch.return_value = MagicMock(fetched=0, stored=0)
            r = await client.post("/api/v1/sync/all")

        assert r.status_code == 200
        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_workout_id == "garmin-strength-001"


# ---------------------------------------------------------------------------
# match_activities — sport-aware pairing
# ---------------------------------------------------------------------------


class TestStrengthPairing:
    async def test_strength_activity_pairs_with_strength_workout(
        self, session: AsyncSession
    ) -> None:
        """A strength_training activity on the same date pairs with the strength workout."""
        sw = await _make_scheduled_workout(
            session, sport="strength", workout_date=date(2026, 6, 1)
        )
        act = await _make_garmin_activity(
            session, activity_type="strength_training", activity_date=date(2026, 6, 1)
        )

        svc = ActivityFetchService()
        count = await svc.match_activities(
            session, user_id=1,
            start_date=date(2026, 5, 1), end_date=date(2026, 7, 1),
        )
        await session.commit()
        await session.refresh(sw)

        assert count == 1
        assert sw.matched_activity_id == act.id
        assert sw.completed is True

    async def test_running_activity_does_not_pair_with_strength_workout(
        self, session: AsyncSession
    ) -> None:
        """A running activity on the same date does NOT pair with a strength workout."""
        sw = await _make_scheduled_workout(
            session, sport="strength", workout_date=date(2026, 6, 1)
        )
        await _make_garmin_activity(
            session, activity_type="running", activity_date=date(2026, 6, 1),
            garmin_id="g-run-001",
        )

        svc = ActivityFetchService()
        count = await svc.match_activities(
            session, user_id=1,
            start_date=date(2026, 5, 1), end_date=date(2026, 7, 1),
        )

        assert count == 0
        await session.refresh(sw)
        assert sw.matched_activity_id is None

    async def test_strength_activity_does_not_pair_with_running_workout(
        self, session: AsyncSession
    ) -> None:
        """A strength_training activity does NOT pair with a running (run) workout."""
        sw = await _make_scheduled_workout(
            session, sport="run", workout_date=date(2026, 6, 1)
        )
        await _make_garmin_activity(
            session, activity_type="strength_training", activity_date=date(2026, 6, 1)
        )

        svc = ActivityFetchService()
        count = await svc.match_activities(
            session, user_id=1,
            start_date=date(2026, 5, 1), end_date=date(2026, 7, 1),
        )

        assert count == 0
        await session.refresh(sw)
        assert sw.matched_activity_id is None


# ---------------------------------------------------------------------------
# fetch_and_store — strength activities are stored
# ---------------------------------------------------------------------------


class TestFetchStrengthActivity:
    async def test_fetch_and_store_saves_strength_training_activity(
        self, session: AsyncSession
    ) -> None:
        """fetch_and_store now stores strength_training activities (not just running)."""
        svc = ActivityFetchService()
        adapter = MagicMock()
        adapter.get_activities_by_date.return_value = [{
            "activityId": "st-001",
            "activityType": {"typeKey": "strength_training"},
            "activityName": "Strength Training",
            "startTimeLocal": "2026-06-01T10:00:00",
            "duration": 3600.0,
            "distance": 0.0,
            "averageSpeed": 0.0,
        }]

        result = await svc.fetch_and_store(
            adapter, session, user_id=1, start_date="2026-06-01", end_date="2026-06-30"
        )

        assert result.fetched == 1
        assert result.stored == 1
