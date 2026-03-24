"""Integration tests for ActivityFetchService.fetch_and_store and match_activities.

These tests use a real in-memory SQLite session to cover the DB-interaction paths
that cannot be covered by the pure unit tests.
"""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import GarminActivity, ScheduledWorkout, WorkoutTemplate
from src.services.activity_fetch_service import ActivityFetchService


def _make_raw_activity(
    activity_id: str = "gid-001",
    type_key: str = "running",
    activity_date: str = "2026-03-10",
    duration: float = 3600.0,
    distance: float = 10000.0,
) -> dict:
    return {
        "activityId": activity_id,
        "activityType": {"typeKey": type_key},
        "activityName": "Morning Run",
        "startTimeLocal": f"{activity_date}T08:00:00",
        "duration": duration,
        "distance": distance,
        "averageSpeed": 2.78,
    }


class TestFetchAndStore:
    """Integration tests for ActivityFetchService.fetch_and_store."""

    async def test_fetch_and_store_saves_new_activities(
        self, session: AsyncSession
    ) -> None:
        """fetch_and_store saves running activities to the DB and returns correct count."""
        service = ActivityFetchService()
        adapter = MagicMock()
        adapter.get_activities_by_date.return_value = [_make_raw_activity()]

        result = await service.fetch_and_store(
            adapter, session, user_id=1, start_date="2026-03-01", end_date="2026-03-31"
        )

        assert result.fetched == 1
        assert result.stored == 1

    async def test_fetch_and_store_deduplicates_by_garmin_activity_id(
        self, session: AsyncSession
    ) -> None:
        """fetch_and_store skips activities already in the DB (dedup by garmin_activity_id)."""
        service = ActivityFetchService()
        adapter = MagicMock()
        raw = _make_raw_activity(activity_id="dup-001")
        adapter.get_activities_by_date.return_value = [raw]

        # First call stores the activity
        result1 = await service.fetch_and_store(
            adapter, session, user_id=1, start_date="2026-03-01", end_date="2026-03-31"
        )
        await session.commit()

        # Second call with same activity should not store again
        result2 = await service.fetch_and_store(
            adapter, session, user_id=1, start_date="2026-03-01", end_date="2026-03-31"
        )

        assert result1.stored == 1
        assert result2.stored == 0

    async def test_fetch_and_store_skips_non_running_activities(
        self, session: AsyncSession
    ) -> None:
        """fetch_and_store ignores non-running activity types."""
        service = ActivityFetchService()
        adapter = MagicMock()
        adapter.get_activities_by_date.return_value = [
            _make_raw_activity(type_key="cycling")
        ]

        result = await service.fetch_and_store(
            adapter, session, user_id=1, start_date="2026-03-01", end_date="2026-03-31"
        )

        assert result.fetched == 1
        assert result.stored == 0


class TestMatchActivities:
    """Integration tests for ActivityFetchService.match_activities."""

    async def _make_template(self, session: AsyncSession) -> WorkoutTemplate:
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)
        return template

    async def _make_activity_db(
        self,
        session: AsyncSession,
        activity_id: str = "act-001",
        activity_date: date = date(2026, 3, 10),
        duration_sec: float = 3600.0,
    ) -> GarminActivity:
        activity = GarminActivity(
            garmin_activity_id=activity_id,
            user_id=1,
            activity_type="running",
            name="Morning Run",
            start_time=datetime(2026, 3, 10, 8, 0, 0),  # noqa: DTZ001
            date=activity_date,
            duration_sec=duration_sec,
            distance_m=10000.0,
        )
        session.add(activity)
        await session.commit()
        await session.refresh(activity)
        return activity

    async def test_match_activities_pairs_workout_with_activity_on_same_date(
        self, session: AsyncSession
    ) -> None:
        """match_activities pairs a scheduled workout with an activity on the same date."""
        service = ActivityFetchService()
        template = await self._make_template(session)
        activity = await self._make_activity_db(
            session, activity_id="m-act-001", activity_date=date(2026, 3, 10)
        )

        sw = ScheduledWorkout(
            date=date(2026, 3, 10),
            workout_template_id=template.id,
            user_id=1,
            sync_status="synced",
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        matched = await service.match_activities(
            session,
            user_id=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )
        await session.commit()

        assert matched == 1
        await session.refresh(sw)
        assert sw.matched_activity_id == activity.id
        assert sw.completed is True

    async def test_match_activities_returns_zero_when_no_workouts(
        self, session: AsyncSession
    ) -> None:
        """match_activities returns 0 when there are no unmatched workouts."""
        service = ActivityFetchService()
        await self._make_activity_db(session, activity_id="m-act-002")

        matched = await service.match_activities(
            session,
            user_id=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )

        assert matched == 0

    async def test_match_activities_skips_already_paired_workouts(
        self, session: AsyncSession
    ) -> None:
        """match_activities skips workouts that already have matched_activity_id set."""
        service = ActivityFetchService()
        template = await self._make_template(session)
        activity1 = await self._make_activity_db(session, activity_id="m-act-003")
        activity2 = await self._make_activity_db(
            session, activity_id="m-act-004", activity_date=date(2026, 3, 10)
        )

        # sw already paired to activity1
        sw = ScheduledWorkout(
            date=date(2026, 3, 10),
            workout_template_id=template.id,
            user_id=1,
            matched_activity_id=activity1.id,
        )
        session.add(sw)
        await session.commit()

        matched = await service.match_activities(
            session,
            user_id=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )

        # activity2 remains unmatched because sw is already paired
        assert matched == 0
        _ = activity2  # referenced to avoid lint warning

    async def test_match_activities_picks_longest_when_multiple_on_same_date(
        self, session: AsyncSession
    ) -> None:
        """match_activities picks the longest-duration activity from same-date candidates."""
        service = ActivityFetchService()
        template = await self._make_template(session)
        _short = await self._make_activity_db(
            session, activity_id="m-short", duration_sec=600.0
        )
        long_act = await self._make_activity_db(
            session, activity_id="m-long", duration_sec=3600.0
        )

        sw = ScheduledWorkout(
            date=date(2026, 3, 10),
            workout_template_id=template.id,
            user_id=1,
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        await service.match_activities(
            session,
            user_id=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )
        await session.commit()

        await session.refresh(sw)
        assert sw.matched_activity_id == long_act.id
