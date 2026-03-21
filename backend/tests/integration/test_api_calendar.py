from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import date
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.app import create_app
from src.api.dependencies import get_session
from src.api.routers.sync import get_optional_garmin_sync_service
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import AthleteProfile, HRZone, ScheduledWorkout, WorkoutTemplate
from src.services.calendar_service import CalendarService

# ---------------------------------------------------------------------------
# Shared auth stub (mirrors the integration conftest pattern)
# ---------------------------------------------------------------------------

_TEST_USER = User(id=1, email="test@example.com", is_active=True)


async def _mock_get_current_user() -> User:
    return _TEST_USER


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
            name="Easy Run", sport_type="running", steps=json.dumps(steps), user_id=1
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
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        for d in [date(2026, 3, 8), date(2026, 3, 10), date(2026, 3, 20)]:
            session.add(ScheduledWorkout(date=d, workout_template_id=template.id, user_id=1))
        await session.commit()

        # Act
        response = await client.get("/api/v1/calendar?start=2026-03-09&end=2026-03-15")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "workouts" in data
        assert "unplanned_activities" in data
        assert len(data["workouts"]) == 1
        assert data["workouts"][0]["date"] == "2026-03-10"
        assert len(data["unplanned_activities"]) == 0

    async def test_reschedule(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10), workout_template_id=template.id, user_id=1
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
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10), workout_template_id=template.id, user_id=1
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
        assert step["target_value_one"] is not None
        assert step["target_value_two"] is not None

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
        template = WorkoutTemplate(name="Empty", sport_type="running", steps=None, user_id=1)
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
            await service.reschedule(session, 9999, date(2026, 3, 20), user_id=1)

    async def test_unschedule_raises_value_error_for_missing_scheduled(
        self, session: AsyncSession
    ) -> None:
        # Arrange
        service = CalendarService()

        # Act / Assert
        with pytest.raises(ValueError, match="ScheduledWorkout 9999 not found"):
            await service.unschedule(session, 9999, user_id=1)

    async def test_unschedule_with_garmin_id_calls_deleter(
        self, session: AsyncSession
    ) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        sw = ScheduledWorkout(
            date=date(2026, 3, 15),
            workout_template_id=template.id,
            garmin_workout_id="garmin-xyz-999",
            sync_status="synced",
            user_id=1,
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        service = CalendarService()
        deleter = MagicMock()

        # Act
        await service.unschedule(session, sw.id, user_id=1, garmin_deleter=deleter)

        # Assert — deleter called with the Garmin ID and local record removed
        deleter.assert_called_once_with("garmin-xyz-999")
        deleted = await session.get(ScheduledWorkout, sw.id)
        assert deleted is None

    async def test_unschedule_without_garmin_id_skips_deleter(
        self, session: AsyncSession
    ) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        sw = ScheduledWorkout(
            date=date(2026, 3, 15),
            workout_template_id=template.id,
            garmin_workout_id=None,
            sync_status="pending",
            user_id=1,
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        service = CalendarService()
        deleter = MagicMock()

        # Act
        await service.unschedule(session, sw.id, user_id=1, garmin_deleter=deleter)

        # Assert — no Garmin ID → deleter never called; local record still removed
        deleter.assert_not_called()
        deleted = await session.get(ScheduledWorkout, sw.id)
        assert deleted is None

    async def test_unschedule_garmin_failure_still_deletes_locally(
        self, session: AsyncSession
    ) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        sw = ScheduledWorkout(
            date=date(2026, 3, 15),
            workout_template_id=template.id,
            garmin_workout_id="garmin-failing-id",
            sync_status="synced",
            user_id=1,
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        service = CalendarService()
        deleter = MagicMock(side_effect=RuntimeError("Garmin API unreachable"))

        # Act — must not raise despite Garmin failure
        await service.unschedule(session, sw.id, user_id=1, garmin_deleter=deleter)

        # Assert — local record deleted despite Garmin failure
        deleted = await session.get(ScheduledWorkout, sw.id)
        assert deleted is None


class TestCalendarGarminCascade:
    """Integration tests: DELETE /calendar/{id} → Garmin delete cascade via API."""

    @pytest.fixture
    def mock_garmin(self) -> MagicMock:
        svc = MagicMock()
        svc.delete_workout.return_value = None
        return svc

    @pytest.fixture
    async def garmin_client(
        self, session: AsyncSession, mock_garmin: MagicMock
    ) -> AsyncGenerator[AsyncClient, None]:
        app = create_app()

        async def override_session() -> AsyncGenerator[AsyncSession, None]:
            yield session

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_user] = _mock_get_current_user
        app.dependency_overrides[get_optional_garmin_sync_service] = (
            lambda: mock_garmin
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

        app.dependency_overrides.clear()

    async def test_delete_synced_workout_calls_garmin_delete(
        self,
        garmin_client: AsyncClient,
        mock_garmin: MagicMock,
        session: AsyncSession,
    ) -> None:
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        sw = ScheduledWorkout(
            date=date(2026, 3, 15),
            workout_template_id=template.id,
            garmin_workout_id="garmin-abc-123",
            sync_status="synced",
            user_id=1,
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        # Act
        response = await garmin_client.delete(f"/api/v1/calendar/{sw.id}")

        # Assert
        assert response.status_code == 204
        mock_garmin.delete_workout.assert_called_once_with("garmin-abc-123")
        deleted = await session.get(ScheduledWorkout, sw.id)
        assert deleted is None

    async def test_delete_pending_workout_skips_garmin_delete(
        self,
        garmin_client: AsyncClient,
        mock_garmin: MagicMock,
        session: AsyncSession,
    ) -> None:
        # Arrange — workout was never synced (no garmin_workout_id)
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        sw = ScheduledWorkout(
            date=date(2026, 3, 15),
            workout_template_id=template.id,
            garmin_workout_id=None,
            sync_status="pending",
            user_id=1,
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        # Act
        response = await garmin_client.delete(f"/api/v1/calendar/{sw.id}")

        # Assert
        assert response.status_code == 204
        mock_garmin.delete_workout.assert_not_called()
        deleted = await session.get(ScheduledWorkout, sw.id)
        assert deleted is None


class TestCalendarNotesUpdate:
    """Tests for PATCH /calendar/{id} optional notes field."""

    async def test_patch_scheduled_workout_notes(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """PATCH /calendar/{id} with notes only (no date change)."""
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10), workout_template_id=template.id, user_id=1
        )
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        # Act
        response = await client.patch(
            f"/api/v1/calendar/{scheduled.id}",
            json={"notes": "Felt strong today"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Felt strong today"

    async def test_patch_scheduled_workout_date_and_notes(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """PATCH /calendar/{id} with both date and notes."""
        # Arrange
        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10), workout_template_id=template.id, user_id=1
        )
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        # Act
        response = await client.patch(
            f"/api/v1/calendar/{scheduled.id}",
            json={"date": "2026-04-01", "notes": "Moved to next week"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-04-01"
        assert data["notes"] == "Moved to next week"


class TestActivityPairing:
    """Tests for manual activity pairing/unpairing."""

    async def test_unpair_activity_preserves_completed_status(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Unpairing a workout should preserve completed status — only remove activity link."""
        # Arrange
        from datetime import datetime, timezone

        from src.db.models import GarminActivity

        template = WorkoutTemplate(name="Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        scheduled = ScheduledWorkout(
            date=date(2026, 3, 10), workout_template_id=template.id, user_id=1
        )
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        activity = GarminActivity(
            garmin_activity_id="123456",
            user_id=1,
            activity_type="running",
            name="Morning Run",
            start_time=datetime(2026, 3, 10, 8, 0, 0),
            date=date(2026, 3, 10),
            duration_sec=3600,
            distance_m=10000,
            avg_hr=None,
            max_hr=None,
            avg_pace_sec_per_km=None,
            calories=None,
        )
        session.add(activity)
        await session.commit()
        await session.refresh(activity)

        # Pair activity to workout (sets completed=True)
        pair_response = await client.post(
            f"/api/v1/calendar/{scheduled.id}/pair/{activity.id}"
        )
        assert pair_response.status_code == 200
        assert pair_response.json()["completed"] is True

        # Act — unpair the activity
        response = await client.post(f"/api/v1/calendar/{scheduled.id}/unpair")

        # Assert — activity link removed, completed still True
        assert response.status_code == 200
        data = response.json()
        assert data["matched_activity_id"] is None
        assert data["activity"] is None
        assert data["completed"] is True  # Should NOT be reset to False
