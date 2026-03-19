from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


from src.db.models import AthleteProfile, HRZone, PaceZone
from src.services.zone_service import ZoneService


def _make_session() -> AsyncMock:
    """Return an AsyncMock session with a synchronous .add() stub."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _make_hr_zone(zone_number: int, profile_id: int = 1) -> HRZone:
    """Helper to create a minimal HRZone instance."""
    return HRZone(
        id=zone_number,
        profile_id=profile_id,
        zone_number=zone_number,
        name=f"Zone {zone_number}",
        lower_bpm=100.0 + zone_number * 10,
        upper_bpm=110.0 + zone_number * 10,
        calculation_method="coggan",
        pct_lower=0.60 + zone_number * 0.05,
        pct_upper=0.70 + zone_number * 0.05,
    )


def _make_pace_zone(zone_number: int, profile_id: int = 1) -> PaceZone:
    """Helper to create a minimal PaceZone instance."""
    return PaceZone(
        id=zone_number,
        profile_id=profile_id,
        zone_number=zone_number,
        name=f"Pace Zone {zone_number}",
        lower_pace=300.0 - zone_number * 10,
        upper_pace=290.0 - zone_number * 10,
        calculation_method="pct_threshold",
        pct_lower=1.10,
        pct_upper=1.00,
    )


# ---------------------------------------------------------------------------
# get_hr_zones / get_pace_zones — delegation to repository
# ---------------------------------------------------------------------------


class TestGetZones:
    async def test_get_hr_zones_delegates_to_repository(self) -> None:
        # Arrange
        service = ZoneService()
        zones = [_make_hr_zone(i) for i in range(1, 6)]
        mock_session = _make_session()

        with patch("src.services.zone_service.hr_zone_repository") as mock_repo:
            mock_repo.get_by_profile = AsyncMock(return_value=zones)

            # Act
            result = await service.get_hr_zones(mock_session, profile_id=1)

        # Assert
        assert result == zones
        mock_repo.get_by_profile.assert_awaited_once_with(mock_session, 1)

    async def test_get_pace_zones_delegates_to_repository(self) -> None:
        # Arrange
        service = ZoneService()
        zones = [_make_pace_zone(i) for i in range(1, 6)]
        mock_session = _make_session()

        with patch("src.services.zone_service.pace_zone_repository") as mock_repo:
            mock_repo.get_by_profile = AsyncMock(return_value=zones)

            # Act
            result = await service.get_pace_zones(mock_session, profile_id=1)

        # Assert
        assert result == zones
        mock_repo.get_by_profile.assert_awaited_once_with(mock_session, 1)


# ---------------------------------------------------------------------------
# recalculate_hr_zones
# ---------------------------------------------------------------------------


class TestRecalculateHRZones:
    async def test_returns_empty_when_profile_has_no_lthr(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", lthr=None)
        mock_session = _make_session()

        # Act
        result = await service.recalculate_hr_zones(mock_session, profile)

        # Assert
        assert result == []

    async def test_creates_five_zones_for_valid_lthr(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", lthr=162)
        mock_session = _make_session()

        with patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_hr_repo.delete_by_profile = AsyncMock()
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            result = await service.recalculate_hr_zones(mock_session, profile)

        # Assert — 5 zones created, session.add called for each
        assert len(result) == 5
        assert mock_session.add.call_count == 5
        mock_session.commit.assert_awaited()

    async def test_deletes_existing_zones_before_creating(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", lthr=162)
        mock_session = _make_session()

        with patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_hr_repo.delete_by_profile = AsyncMock()
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            await service.recalculate_hr_zones(mock_session, profile)

        # Assert — delete called before creating
        mock_hr_repo.delete_by_profile.assert_awaited_once_with(mock_session, 1)

    async def test_zone_numbers_are_1_through_5(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", lthr=162)
        mock_session = _make_session()

        with patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_hr_repo.delete_by_profile = AsyncMock()
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            result = await service.recalculate_hr_zones(mock_session, profile)

        # Assert
        zone_numbers = [z.zone_number for z in result]
        assert zone_numbers == [1, 2, 3, 4, 5]

    async def test_uses_friel_calculation_method(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", lthr=162)
        mock_session = _make_session()

        with patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_hr_repo.delete_by_profile = AsyncMock()
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            result = await service.recalculate_hr_zones(mock_session, profile)

        # Assert
        assert all(z.calculation_method == "friel" for z in result)

    async def test_triggers_cascade_re_resolve(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, user_id=1, name="Runner", lthr=162)
        mock_session = _make_session()

        with patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()) as mock_cascade:
            mock_hr_repo.delete_by_profile = AsyncMock()
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            await service.recalculate_hr_zones(mock_session, profile)

        # Assert — cascade receives (session, profile_id, user_id, hr_zones=<new zones>)
        mock_cascade.assert_awaited_once()
        call_args = mock_cascade.await_args
        assert call_args[0][:3] == (mock_session, 1, 1)
        assert "hr_zones" in call_args[1]
        assert len(call_args[1]["hr_zones"]) == 5


# ---------------------------------------------------------------------------
# recalculate_pace_zones
# ---------------------------------------------------------------------------


class TestRecalculatePaceZones:
    async def test_returns_empty_when_profile_has_no_threshold_pace(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", threshold_pace=None)
        mock_session = _make_session()

        # Act
        result = await service.recalculate_pace_zones(mock_session, profile)

        # Assert
        assert result == []

    async def test_creates_five_zones_for_valid_threshold_pace(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", threshold_pace=270.0)
        mock_session = _make_session()

        with patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_pace_repo.delete_by_profile = AsyncMock()
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            result = await service.recalculate_pace_zones(mock_session, profile)

        # Assert
        assert len(result) == 5
        assert mock_session.add.call_count == 5

    async def test_deletes_existing_pace_zones_before_creating(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", threshold_pace=270.0)
        mock_session = _make_session()

        with patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_pace_repo.delete_by_profile = AsyncMock()
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            await service.recalculate_pace_zones(mock_session, profile)

        # Assert
        mock_pace_repo.delete_by_profile.assert_awaited_once_with(mock_session, 1)

    async def test_uses_pct_threshold_calculation_method(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, name="Runner", threshold_pace=270.0)
        mock_session = _make_session()

        with patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_pace_repo.delete_by_profile = AsyncMock()
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            result = await service.recalculate_pace_zones(mock_session, profile)

        # Assert
        assert all(z.calculation_method == "pct_threshold" for z in result)

    async def test_triggers_cascade_re_resolve(self) -> None:
        # Arrange
        service = ZoneService()
        profile = AthleteProfile(id=1, user_id=1, name="Runner", threshold_pace=270.0)
        mock_session = _make_session()

        with patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()) as mock_cascade:
            mock_pace_repo.delete_by_profile = AsyncMock()
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            await service.recalculate_pace_zones(mock_session, profile)

        # Assert — cascade receives (session, profile_id, user_id, pace_zones=<new zones>)
        mock_cascade.assert_awaited_once()
        call_args = mock_cascade.await_args
        assert call_args[0][:3] == (mock_session, 1, 1)
        assert "pace_zones" in call_args[1]
        assert len(call_args[1]["pace_zones"]) == 5


# ---------------------------------------------------------------------------
# set_hr_zones
# ---------------------------------------------------------------------------


class TestSetHRZones:
    async def test_set_hr_zones_replaces_all_zones(self) -> None:
        # Arrange
        service = ZoneService()
        mock_session = _make_session()
        zones_data = [
            {
                "zone_number": i,
                "name": f"Zone {i}",
                "lower_bpm": 100.0 + i * 10,
                "upper_bpm": 110.0 + i * 10,
                "calculation_method": "custom",
                "pct_lower": 0.60,
                "pct_upper": 0.70,
            }
            for i in range(1, 6)
        ]

        with patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_hr_repo.delete_by_profile = AsyncMock()
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            result = await service.set_hr_zones(mock_session, profile_id=1, user_id=1, zones_data=zones_data)

        # Assert
        assert len(result) == 5
        mock_hr_repo.delete_by_profile.assert_awaited_once_with(mock_session, 1)
        assert mock_session.add.call_count == 5
        mock_session.commit.assert_awaited()

    async def test_set_hr_zones_uses_custom_method_when_not_specified(self) -> None:
        # Arrange
        service = ZoneService()
        mock_session = _make_session()
        zones_data = [
            {
                "zone_number": 1,
                "name": "Zone 1",
                "lower_bpm": 100.0,
                "upper_bpm": 120.0,
                # no calculation_method key → should default to "custom"
                "pct_lower": 0.60,
                "pct_upper": 0.70,
            }
        ]

        with patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()):
            mock_hr_repo.delete_by_profile = AsyncMock()
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            result = await service.set_hr_zones(mock_session, profile_id=1, user_id=1, zones_data=zones_data)

        # Assert
        assert result[0].calculation_method == "custom"

    async def test_set_hr_zones_triggers_cascade_re_resolve(self) -> None:
        # Arrange
        service = ZoneService()
        mock_session = _make_session()
        zones_data = [
            {
                "zone_number": 1,
                "name": "Zone 1",
                "lower_bpm": 100.0,
                "upper_bpm": 120.0,
                "pct_lower": 0.60,
                "pct_upper": 0.70,
            }
        ]

        with patch("src.services.zone_service.hr_zone_repository") as mock_hr_repo, \
             patch("src.services.zone_service.pace_zone_repository") as mock_pace_repo, \
             patch.object(service, "_cascade_re_resolve", AsyncMock()) as mock_cascade:
            mock_hr_repo.delete_by_profile = AsyncMock()
            mock_hr_repo.get_by_profile = AsyncMock(return_value=[])
            mock_pace_repo.get_by_profile = AsyncMock(return_value=[])

            # Act
            await service.set_hr_zones(mock_session, profile_id=1, user_id=1, zones_data=zones_data)

        # Assert — cascade receives (session, profile_id, user_id)
        mock_cascade.assert_awaited_once_with(mock_session, 1, 1)


# ---------------------------------------------------------------------------
# _cascade_re_resolve — marks modified even for builder-format steps
# ---------------------------------------------------------------------------


class TestCascadeReResolve:
    async def test_cascade_marks_modified_when_resolver_format_succeeds(self) -> None:
        """Resolver-format steps → resolved_steps updated + status = modified."""
        import json
        from datetime import date

        from src.db.models import ScheduledWorkout, WorkoutTemplate

        service = ZoneService()
        session = _make_session()

        template = WorkoutTemplate(
            id=1, name="T", sport_type="running",
            steps=json.dumps([{
                "order": 1, "step_type": "active", "duration_type": "time",
                "duration_value": 600, "end_condition": "time",
                "end_condition_value": 600, "target_type": "open",
            }]),
        )
        sw = ScheduledWorkout(
            id=10, date=date(2099, 1, 1), workout_template_id=1,
            sync_status="synced", resolved_steps=None,
        )

        # Mock session.exec to return batch-loaded templates
        mock_result = MagicMock()
        mock_result.all.return_value = [template]
        session.exec = AsyncMock(return_value=mock_result)

        with (
            patch("src.services.zone_service.hr_zone_repository") as mock_hr,
            patch("src.services.zone_service.pace_zone_repository") as mock_pace,
            patch("src.repositories.calendar.scheduled_workout_repository") as mock_cal,
        ):
            mock_hr.get_by_profile = AsyncMock(return_value=[])
            mock_pace.get_by_profile = AsyncMock(return_value=[])
            mock_cal.get_all_incomplete = AsyncMock(return_value=[sw])

            await service._cascade_re_resolve(session, profile_id=1, user_id=1)

        assert sw.sync_status == "modified"

    async def test_cascade_marks_modified_for_builder_format_steps(self) -> None:
        """Builder-format steps fail resolver validation but workout is still marked modified."""
        import json
        from datetime import date

        from src.db.models import ScheduledWorkout, WorkoutTemplate

        service = ZoneService()
        session = _make_session()

        # Builder-format step: uses 'duration_sec'/'zone' keys, no 'order' field.
        template = WorkoutTemplate(
            id=2, name="Builder", sport_type="running",
            steps=json.dumps([{
                "id": "abc", "type": "interval",
                "duration_type": "time", "target_type": "pace_zone",
                "duration_sec": 300, "zone": 4,
            }]),
        )
        sw = ScheduledWorkout(
            id=20, date=date(2099, 6, 1), workout_template_id=2,
            sync_status="synced", resolved_steps=None,
        )

        # Mock session.exec to return batch-loaded templates
        mock_result = MagicMock()
        mock_result.all.return_value = [template]
        session.exec = AsyncMock(return_value=mock_result)

        with (
            patch("src.services.zone_service.hr_zone_repository") as mock_hr,
            patch("src.services.zone_service.pace_zone_repository") as mock_pace,
            patch("src.repositories.calendar.scheduled_workout_repository") as mock_cal,
        ):
            mock_hr.get_by_profile = AsyncMock(return_value=[])
            mock_pace.get_by_profile = AsyncMock(return_value=[])
            mock_cal.get_all_incomplete = AsyncMock(return_value=[sw])

            await service._cascade_re_resolve(session, profile_id=1, user_id=1)

        # Builder steps can't be resolved by the old resolver, but the workout
        # must still be marked modified so the next sync re-translates it.
        assert sw.sync_status == "modified"
        # resolved_steps stays None — sync fallback will handle it
        assert sw.resolved_steps is None
