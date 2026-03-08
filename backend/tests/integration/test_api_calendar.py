from __future__ import annotations

import json
from datetime import date

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile, HRZone, ScheduledWorkout, WorkoutTemplate
from src.services.calendar_service import CalendarService


class TestCalendarAPI:
    async def _seed_template_with_steps(self, session: AsyncSession) -> WorkoutTemplate:
        steps = [
            {
                "order": 1,
                "type": "active",
                "duration_type": "time",
                "duration_value": 1800,
                "duration_unit": "seconds",
                "target_type": "hr_zone",
                "target_zone": 2,
                "steps": [],
            }
        ]
        template = WorkoutTemplate(
            name="Easy Run", sport_type="running", steps=json.dumps(steps)
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)
        return template

    async def _seed_profile_with_hr_zones(self, session: AsyncSession) -> AthleteProfile:
        from src.zone_engine.hr_zones import HRZoneCalculator
        from src.zone_engine.models import ZoneConfig

        profile = AthleteProfile(name="Runner", max_hr=185, lthr=162, user_id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        config = ZoneConfig(threshold=162, method="coggan")
        zone_set = HRZoneCalculator(config).calculate()
        for z in zone_set.zones:
            session.add(
                HRZone(
                    profile_id=profile.id,
                    zone_number=z.zone_number,
                    name=z.name,
                    lower_bpm=z.lower,
                    upper_bpm=z.upper,
                    calculation_method="coggan",
                    pct_lower=z.pct_lower,
                    pct_upper=z.pct_upper,
                )
            )
        await session.commit()
        return profile

    async def test_schedule(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        template = await self._seed_template_with_steps(session)
        await self._seed_profile_with_hr_zones(session)

        # Act
        response = await client.post(
            "/api/v1/calendar",
            json={"template_id": template.id, "date": "2026-03-15"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["date"] == "2026-03-15"
        assert data["workout_template_id"] == template.id

    async def test_get_range(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running")
        session.add(template)
        await session.commit()
        await session.refresh(template)

        for d in [date(2026, 3, 8), date(2026, 3, 10), date(2026, 3, 20)]:
            session.add(ScheduledWorkout(date=d, workout_template_id=template.id))
        await session.commit()

        # Act
        response = await client.get("/api/v1/calendar?start=2026-03-09&end=2026-03-15")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["date"] == "2026-03-10"

    async def test_reschedule(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running")
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10), workout_template_id=template.id
        )
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        # Act
        response = await client.patch(
            f"/api/v1/calendar/{scheduled.id}", json={"date": "2026-03-17"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-03-17"

    async def test_unschedule(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running")
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10), workout_template_id=template.id
        )
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        # Act
        response = await client.delete(f"/api/v1/calendar/{scheduled.id}")

        # Assert
        assert response.status_code == 204
        deleted = await session.get(ScheduledWorkout, scheduled.id)
        assert deleted is None

    async def test_schedule_resolves_steps(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange
        template = await self._seed_template_with_steps(session)
        await self._seed_profile_with_hr_zones(session)

        # Act
        response = await client.post(
            "/api/v1/calendar",
            json={"template_id": template.id, "date": "2026-03-15"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        # resolved_steps should be populated (not null/empty)
        assert data["resolved_steps"] is not None
        resolved = json.loads(data["resolved_steps"])
        assert len(resolved) == 1
        # The zone-referenced step should have absolute HR targets
        step = resolved[0]
        assert step["target_low"] is not None
        assert step["target_high"] is not None

    async def test_schedule_invalid_template_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange — no template with id=9999 exists
        profile = AthleteProfile(name="Runner", user_id=1)
        session.add(profile)
        await session.commit()

        # Act
        response = await client.post(
            "/api/v1/calendar",
            json={"template_id": 9999, "date": "2026-03-15"},
        )

        # Assert
        assert response.status_code == 404

    async def test_reschedule_nonexistent_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Act — try to reschedule a workout that doesn't exist
        response = await client.patch(
            "/api/v1/calendar/9999", json={"date": "2026-03-20"}
        )

        # Assert
        assert response.status_code == 404

    async def test_unschedule_nonexistent_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Act — try to delete a workout that doesn't exist
        response = await client.delete("/api/v1/calendar/9999")

        # Assert
        assert response.status_code == 404

    async def test_schedule_template_without_steps_sets_null_resolved(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange — template with no steps
        template = WorkoutTemplate(name="Empty", sport_type="running", steps=None)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        profile = AthleteProfile(name="Runner", user_id=1)
        session.add(profile)
        await session.commit()

        # Act
        response = await client.post(
            "/api/v1/calendar",
            json={"template_id": template.id, "date": "2026-03-15"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["resolved_steps"] is None


class TestCalendarServiceUnit:
    """Unit tests for CalendarService that target uncovered service branches."""

    async def test_schedule_raises_value_error_for_missing_template(
        self, session: AsyncSession
    ) -> None:
        # Arrange
        service = CalendarService()
        profile = AthleteProfile(id=1, name="Runner", user_id=1)
        session.add(profile)
        await session.commit()

        # Act / Assert
        with pytest.raises(ValueError, match="WorkoutTemplate 9999 not found"):
            await service.schedule(session, 9999, date(2026, 3, 15), profile)

    async def test_reschedule_raises_value_error_for_missing_scheduled(
        self, session: AsyncSession
    ) -> None:
        # Arrange
        service = CalendarService()

        # Act / Assert
        with pytest.raises(ValueError, match="ScheduledWorkout 9999 not found"):
            await service.reschedule(session, 9999, date(2026, 3, 20))

    async def test_unschedule_raises_value_error_for_missing_scheduled(
        self, session: AsyncSession
    ) -> None:
        # Arrange
        service = CalendarService()

        # Act / Assert
        with pytest.raises(ValueError, match="ScheduledWorkout 9999 not found"):
            await service.unschedule(session, 9999)
