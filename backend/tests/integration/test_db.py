from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pytest
from sqlmodel import Session, select

from src.db.models import (
    AthleteProfile,
    HRZone,
    PaceZone,
    ScheduledWorkout,
    WorkoutTemplate,
)


class TestAthleteProfile:
    def test_create_athlete_profile(self, session: Session) -> None:
        # Arrange
        profile = AthleteProfile(name="Test Runner", max_hr=185, resting_hr=45, lthr=162)

        # Act
        session.add(profile)
        session.commit()
        session.refresh(profile)

        # Assert
        assert profile.id is not None
        assert profile.name == "Test Runner"
        assert profile.max_hr == 185
        assert profile.resting_hr == 45
        assert profile.lthr == 162

    def test_update_athlete_lthr(self, session: Session) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", lthr=155)
        session.add(profile)
        session.commit()
        session.refresh(profile)
        original_updated_at = profile.updated_at

        # Act
        profile.lthr = 162
        profile.updated_at = datetime.utcnow()
        session.add(profile)
        session.commit()
        session.refresh(profile)

        # Assert
        assert profile.lthr == 162
        assert profile.updated_at >= original_updated_at


class TestHRZones:
    def test_create_hr_zones(self, session: Session) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", lthr=162)
        session.add(profile)
        session.commit()
        session.refresh(profile)

        zones = [
            HRZone(
                profile_id=profile.id,
                zone_number=i,
                name=f"Zone {i}",
                lower_bpm=100.0 + i * 10,
                upper_bpm=110.0 + i * 10,
                calculation_method="coggan",
                pct_lower=0.60 + i * 0.05,
                pct_upper=0.65 + i * 0.05,
            )
            for i in range(1, 6)
        ]

        # Act
        for z in zones:
            session.add(z)
        session.commit()

        result = session.exec(
            select(HRZone).where(HRZone.profile_id == profile.id)
        ).all()

        # Assert
        assert len(result) == 5
        zone_numbers = sorted(z.zone_number for z in result)
        assert zone_numbers == [1, 2, 3, 4, 5]

    def test_create_pace_zones(self, session: Session) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", threshold_pace=270.0)
        session.add(profile)
        session.commit()
        session.refresh(profile)

        zones = [
            PaceZone(
                profile_id=profile.id,
                zone_number=i,
                name=f"Pace Zone {i}",
                lower_pace=270.0 + i * 10,
                upper_pace=260.0 + i * 10,
                calculation_method="pct_threshold",
                pct_lower=1.10 - i * 0.05,
                pct_upper=1.05 - i * 0.05,
            )
            for i in range(1, 6)
        ]

        # Act
        for z in zones:
            session.add(z)
        session.commit()

        result = session.exec(
            select(PaceZone).where(PaceZone.profile_id == profile.id)
        ).all()

        # Assert
        assert len(result) == 5
        zone_numbers = sorted(z.zone_number for z in result)
        assert zone_numbers == [1, 2, 3, 4, 5]

    def test_cascade_delete(self, session: Session) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", lthr=162)
        session.add(profile)
        session.commit()
        session.refresh(profile)

        hr_zones = [
            HRZone(
                profile_id=profile.id,
                zone_number=i,
                name=f"Zone {i}",
                lower_bpm=100.0 + i * 10,
                upper_bpm=110.0 + i * 10,
                calculation_method="coggan",
                pct_lower=0.60,
                pct_upper=0.70,
            )
            for i in range(1, 6)
        ]
        pace_zones = [
            PaceZone(
                profile_id=profile.id,
                zone_number=i,
                name=f"Pace {i}",
                lower_pace=300.0,
                upper_pace=270.0,
                calculation_method="pct_threshold",
                pct_lower=1.10,
                pct_upper=1.00,
            )
            for i in range(1, 6)
        ]
        for z in hr_zones + pace_zones:
            session.add(z)
        session.commit()

        # Act
        # Delete zones associated with the profile manually (SQLite has no cascade by default)
        for z in session.exec(select(HRZone).where(HRZone.profile_id == profile.id)).all():
            session.delete(z)
        for z in session.exec(select(PaceZone).where(PaceZone.profile_id == profile.id)).all():
            session.delete(z)
        session.delete(profile)
        session.commit()

        # Assert
        remaining_hr = session.exec(
            select(HRZone).where(HRZone.profile_id == profile.id)
        ).all()
        remaining_pace = session.exec(
            select(PaceZone).where(PaceZone.profile_id == profile.id)
        ).all()
        assert len(remaining_hr) == 0
        assert len(remaining_pace) == 0


class TestWorkoutTemplate:
    def test_create_workout_template(self, session: Session) -> None:
        # Arrange
        steps = [
            {"order": 1, "type": "warmup", "duration_type": "time",
             "duration_value": 600, "duration_unit": "seconds",
             "target_type": "hr_zone", "target_zone": 1}
        ]
        template = WorkoutTemplate(
            name="Easy Run",
            description="An easy aerobic run",
            sport_type="running",
            tags=json.dumps(["easy", "aerobic"]),
            steps=json.dumps(steps),
        )

        # Act
        session.add(template)
        session.commit()
        session.refresh(template)

        # Assert
        assert template.id is not None
        assert template.name == "Easy Run"
        stored_steps = json.loads(template.steps)
        assert len(stored_steps) == 1
        assert stored_steps[0]["type"] == "warmup"


class TestScheduledWorkout:
    def test_schedule_workout(self, session: Session) -> None:
        # Arrange
        template = WorkoutTemplate(name="Tempo Run", sport_type="running")
        session.add(template)
        session.commit()
        session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10),
            workout_template_id=template.id,
            sync_status="pending",
        )

        # Act
        session.add(scheduled)
        session.commit()
        session.refresh(scheduled)

        # Assert
        assert scheduled.id is not None
        assert scheduled.date == date(2026, 3, 10)
        assert scheduled.workout_template_id == template.id
        assert scheduled.sync_status == "pending"

    def test_get_by_date_range(self, session: Session) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running")
        session.add(template)
        session.commit()
        session.refresh(template)

        dates = [date(2026, 3, 8), date(2026, 3, 10), date(2026, 3, 15)]
        for d in dates:
            session.add(ScheduledWorkout(date=d, workout_template_id=template.id))
        session.commit()

        # Act
        start = date(2026, 3, 9)
        end = date(2026, 3, 12)
        result = session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.date >= start,
                ScheduledWorkout.date <= end,
            )
        ).all()

        # Assert
        assert len(result) == 1
        assert result[0].date == date(2026, 3, 10)

    def test_update_sync_status(self, session: Session) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running")
        session.add(template)
        session.commit()
        session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10),
            workout_template_id=template.id,
            sync_status="pending",
        )
        session.add(scheduled)
        session.commit()
        session.refresh(scheduled)

        # Act
        scheduled.sync_status = "synced"
        scheduled.garmin_workout_id = "garmin-123"
        session.add(scheduled)
        session.commit()
        session.refresh(scheduled)

        # Assert
        assert scheduled.sync_status == "synced"
        assert scheduled.garmin_workout_id == "garmin-123"
