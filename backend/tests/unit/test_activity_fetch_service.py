from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models import GarminActivity
from src.services.activity_fetch_service import ActivityFetchService


def _make_garmin_activity(
    activity_id: str = "111",
    type_key: str = "running",
    name: str = "Morning Run",
    start_time_local: str = "2026-03-19 07:30:00",
    duration: float = 1800.0,
    distance: float = 5000.0,
    avg_speed: float = 2.78,
    avg_hr: float = 145.0,
    max_hr: float = 165.0,
    calories: int = 350,
) -> dict:
    return {
        "activityId": activity_id,
        "activityType": {"typeKey": type_key},
        "activityName": name,
        "startTimeLocal": start_time_local,
        "duration": duration,
        "distance": distance,
        "averageSpeed": avg_speed,
        "averageHR": avg_hr,
        "maxHR": max_hr,
        "calories": calories,
    }


class TestActivityFetchService:
    @pytest.fixture()
    def service(self):
        return ActivityFetchService()

    def test_parse_activity_extracts_fields(self, service):
        raw = _make_garmin_activity()
        parsed = service._parse_activity(raw, user_id=1)
        assert parsed.garmin_activity_id == "111"
        assert parsed.activity_type == "running"
        assert parsed.name == "Morning Run"
        assert parsed.date == date(2026, 3, 19)
        assert parsed.duration_sec == 1800.0
        assert parsed.distance_m == 5000.0
        assert parsed.avg_hr == 145.0
        assert parsed.max_hr == 165.0
        assert parsed.calories == 350
        assert parsed.avg_pace_sec_per_km is not None
        assert abs(parsed.avg_pace_sec_per_km - 359.7) < 1.0

    def test_parse_activity_filters_non_running(self, service):
        raw = _make_garmin_activity(type_key="cycling")
        result = service._parse_activity(raw, user_id=1)
        assert result is None

    def test_parse_activity_accepts_trail_running(self, service):
        raw = _make_garmin_activity(type_key="trail_running")
        result = service._parse_activity(raw, user_id=1)
        assert result is not None
        assert result.activity_type == "trail_running"

    def test_parse_activity_accepts_treadmill_running(self, service):
        raw = _make_garmin_activity(type_key="treadmill_running")
        result = service._parse_activity(raw, user_id=1)
        assert result is not None

    def test_parse_activity_handles_zero_speed(self, service):
        raw = _make_garmin_activity(avg_speed=0.0)
        parsed = service._parse_activity(raw, user_id=1)
        assert parsed is not None
        assert parsed.avg_pace_sec_per_km is None


class TestMatchActivities:
    def test_match_picks_longest_when_multiple(self):
        service = ActivityFetchService()
        activities = [
            GarminActivity(
                id=1, user_id=1, garmin_activity_id="a",
                activity_type="running", name="Short",
                start_time=datetime.now(timezone.utc).replace(tzinfo=None),
                date=date(2026, 3, 19), duration_sec=600, distance_m=2000,
            ),
            GarminActivity(
                id=2, user_id=1, garmin_activity_id="b",
                activity_type="running", name="Long",
                start_time=datetime.now(timezone.utc).replace(tzinfo=None),
                date=date(2026, 3, 19), duration_sec=3600, distance_m=10000,
            ),
        ]
        best = service._pick_best_match(activities)
        assert best is not None
        assert best.id == 2

    def test_match_returns_none_for_empty(self):
        service = ActivityFetchService()
        assert service._pick_best_match([]) is None


def _make_raw_activity(
    activity_id: str = "act-1",
    name: str = "Morning Run",
    distance: float = 10000.0,
    duration: float = 3600.0,
    avg_speed: float = 2.78,
    avg_hr: float = 145.0,
    start_time_local: str = "2026-04-10 08:00:00",
) -> dict[str, Any]:
    return {
        "activityId": activity_id,
        "activityName": name,
        "activityType": {"typeKey": "running"},
        "distance": distance,
        "duration": duration,
        "averageSpeed": avg_speed,
        "averageHR": avg_hr,
        "maxHR": 170.0,
        "calories": 500,
        "startTimeLocal": start_time_local,
    }


class TestFetchAndStoreUpsert:
    async def test_fetch_and_store_upserts_existing_activity(self):
        """When an activity already exists in DB, update its fields (not skip)."""
        existing = GarminActivity(
            id=1,
            user_id=1,
            garmin_activity_id="act-1",
            activity_type="running",
            name="Old Name",
            start_time=datetime(2026, 4, 10, 8, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None),
            date=date(2026, 4, 10),
            duration_sec=3500.0,
            distance_m=9500.0,
            avg_hr=140.0,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [existing]
        mock_session.exec.return_value = mock_result

        mock_adapter = MagicMock()
        mock_adapter.get_activities_by_date.return_value = [
            _make_raw_activity(
                activity_id="act-1",
                name="Corrected Name",
                distance=10000.0,
                duration=3600.0,
            )
        ]

        result = await ActivityFetchService().fetch_and_store(
            garmin_adapter=mock_adapter,
            session=mock_session,
            user_id=1,
            start_date="2026-04-10",
            end_date="2026-04-10",
        )

        assert result.fetched == 1
        assert result.stored == 0
        assert result.updated == 1
        assert existing.distance_m == 10000.0
        assert existing.duration_sec == 3600.0
        assert existing.name == "Corrected Name"
        mock_session.add.assert_called()

    async def test_fetch_and_store_inserts_new_activity(self):
        """New activities are inserted as before."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        mock_adapter = MagicMock()
        mock_adapter.get_activities_by_date.return_value = [
            _make_raw_activity(activity_id="brand-new")
        ]

        result = await ActivityFetchService().fetch_and_store(
            garmin_adapter=mock_adapter,
            session=mock_session,
            user_id=1,
            start_date="2026-04-10",
            end_date="2026-04-10",
        )

        assert result.fetched == 1
        assert result.stored == 1
        assert result.updated == 0

    async def test_fetch_and_store_does_not_mutate_date_on_upsert(self):
        """Upsert must NOT change the date field — date drives pairing."""
        original_date = date(2026, 4, 10)
        existing = GarminActivity(
            id=1, user_id=1, garmin_activity_id="act-1",
            activity_type="running", name="Run",
            start_time=datetime(2026, 4, 10, 8, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None),
            date=original_date,
            duration_sec=3500.0, distance_m=9500.0,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [existing]
        mock_session.exec.return_value = mock_result

        mock_adapter = MagicMock()
        mock_adapter.get_activities_by_date.return_value = [
            _make_raw_activity(
                activity_id="act-1",
                start_time_local="2026-04-11 08:00:00",
            )
        ]

        await ActivityFetchService().fetch_and_store(
            garmin_adapter=mock_adapter, session=mock_session,
            user_id=1, start_date="2026-04-10", end_date="2026-04-11",
        )

        assert existing.date == original_date
