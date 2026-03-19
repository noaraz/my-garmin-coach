from __future__ import annotations

from datetime import date, datetime, timezone

from src.db.models import GarminActivity, ScheduledWorkout


class TestGarminActivityModel:
    def test_create_garmin_activity(self):
        activity = GarminActivity(
            user_id=1,
            garmin_activity_id="12345678",
            activity_type="running",
            name="Morning Run",
            start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            date=date(2026, 3, 19),
            duration_sec=1800.0,
            distance_m=5000.0,
            avg_hr=145.0,
            max_hr=165.0,
            avg_pace_sec_per_km=360.0,
            calories=350,
        )
        assert activity.garmin_activity_id == "12345678"
        assert activity.activity_type == "running"
        assert activity.duration_sec == 1800.0

    def test_garmin_activity_nullable_fields(self):
        activity = GarminActivity(
            user_id=1,
            garmin_activity_id="99999",
            activity_type="treadmill_running",
            name="Treadmill",
            start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            date=date(2026, 3, 19),
            duration_sec=600.0,
            distance_m=2000.0,
        )
        assert activity.avg_hr is None
        assert activity.max_hr is None
        assert activity.avg_pace_sec_per_km is None
        assert activity.calories is None

    def test_scheduled_workout_matched_activity_id(self):
        sw = ScheduledWorkout(
            user_id=1,
            date=date(2026, 3, 19),
            matched_activity_id=42,
        )
        assert sw.matched_activity_id == 42
        assert sw.completed is False

    def test_scheduled_workout_matched_activity_id_default_none(self):
        sw = ScheduledWorkout(user_id=1, date=date(2026, 3, 19))
        assert sw.matched_activity_id is None
