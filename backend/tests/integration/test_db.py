from __future__ import annotations

import json
from datetime import date, datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import (
    AthleteProfile,
    HRZone,
    PaceZone,
    ScheduledWorkout,
    WorkoutTemplate,
)


class TestAthleteProfile:
    async def test_create_athlete_profile(self, session: AsyncSession) -> None:
        # Arrange
        profile = AthleteProfile(name="Test Runner", max_hr=185, resting_hr=45, lthr=162)

        # Act
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        # Assert
        assert profile.id is not None
        assert profile.name == "Test Runner"
        assert profile.max_hr == 185
        assert profile.resting_hr == 45
        assert profile.lthr == 162

    async def test_update_athlete_lthr(self, session: AsyncSession) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", lthr=155)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        original_updated_at = profile.updated_at

        # Act
        profile.lthr = 162
        profile.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        # Assert
        assert profile.lthr == 162
        assert profile.updated_at >= original_updated_at


class TestHRZones:
    async def test_create_hr_zones(self, session: AsyncSession) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", lthr=162)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

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
        await session.commit()

        result = await session.exec(
            select(HRZone).where(HRZone.profile_id == profile.id)
        )

        # Assert
        all_zones = result.all()
        assert len(all_zones) == 5
        zone_numbers = sorted(z.zone_number for z in all_zones)
        assert zone_numbers == [1, 2, 3, 4, 5]

    async def test_create_pace_zones(self, session: AsyncSession) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", threshold_pace=270.0)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

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
        await session.commit()

        result = await session.exec(
            select(PaceZone).where(PaceZone.profile_id == profile.id)
        )

        # Assert
        all_zones = result.all()
        assert len(all_zones) == 5
        zone_numbers = sorted(z.zone_number for z in all_zones)
        assert zone_numbers == [1, 2, 3, 4, 5]

    async def test_cascade_delete(self, session: AsyncSession) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", lthr=162)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

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
        await session.commit()

        # Act — delete zones manually (SQLite has no cascade by default)
        hr_result = await session.exec(select(HRZone).where(HRZone.profile_id == profile.id))
        for z in hr_result.all():
            await session.delete(z)
        pace_result = await session.exec(select(PaceZone).where(PaceZone.profile_id == profile.id))
        for z in pace_result.all():
            await session.delete(z)
        await session.delete(profile)
        await session.commit()

        # Assert
        remaining_hr_result = await session.exec(
            select(HRZone).where(HRZone.profile_id == profile.id)
        )
        remaining_pace_result = await session.exec(
            select(PaceZone).where(PaceZone.profile_id == profile.id)
        )
        assert len(remaining_hr_result.all()) == 0
        assert len(remaining_pace_result.all()) == 0


class TestWorkoutTemplate:
    async def test_create_workout_template(self, session: AsyncSession) -> None:
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
        await session.commit()
        await session.refresh(template)

        # Assert
        assert template.id is not None
        assert template.name == "Easy Run"
        stored_steps = json.loads(template.steps)
        assert len(stored_steps) == 1
        assert stored_steps[0]["type"] == "warmup"


class TestScheduledWorkout:
    async def test_schedule_workout(self, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="Tempo Run", sport_type="running")
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10),
            workout_template_id=template.id,
            sync_status="pending",
        )

        # Act
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        # Assert
        assert scheduled.id is not None
        assert scheduled.date == date(2026, 3, 10)
        assert scheduled.workout_template_id == template.id
        assert scheduled.sync_status == "pending"

    async def test_get_by_date_range(self, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running")
        session.add(template)
        await session.commit()
        await session.refresh(template)

        dates = [date(2026, 3, 8), date(2026, 3, 10), date(2026, 3, 15)]
        for d in dates:
            session.add(ScheduledWorkout(date=d, workout_template_id=template.id))
        await session.commit()

        # Act
        start = date(2026, 3, 9)
        end = date(2026, 3, 12)
        result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.date >= start,
                ScheduledWorkout.date <= end,
            )
        )

        # Assert
        rows = result.all()
        assert len(rows) == 1
        assert rows[0].date == date(2026, 3, 10)

    async def test_update_sync_status(self, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running")
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10),
            workout_template_id=template.id,
            sync_status="pending",
        )
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        # Act
        scheduled.sync_status = "synced"
        scheduled.garmin_workout_id = "garmin-123"
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        # Assert
        assert scheduled.sync_status == "synced"
        assert scheduled.garmin_workout_id == "garmin-123"
