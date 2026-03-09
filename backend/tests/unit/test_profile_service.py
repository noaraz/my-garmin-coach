from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


from src.db.models import AthleteProfile
from src.services.profile_service import ProfileService


def _make_session() -> AsyncMock:
    """Return an AsyncMock session with a synchronous .add() stub."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# get_or_create — user_id path
# ---------------------------------------------------------------------------


class TestGetOrCreateWithUserId:
    async def test_get_or_create_returns_existing_profile_when_found(self) -> None:
        # Arrange
        service = ProfileService()
        existing = AthleteProfile(id=1, name="Runner", user_id=42)
        mock_session = _make_session()

        with patch(
            "src.services.profile_service.profile_repository"
        ) as mock_repo:
            mock_repo.get_by_user_id = AsyncMock(return_value=existing)

            # Act
            result = await service.get_or_create(mock_session, user_id=42)

        # Assert
        assert result is existing
        mock_repo.get_by_user_id.assert_awaited_once_with(mock_session, 42)
        mock_repo.create.assert_not_called()

    async def test_get_or_create_creates_profile_when_not_found(self) -> None:
        # Arrange
        service = ProfileService()
        created = AthleteProfile(id=2, name="Athlete", user_id=99)
        mock_session = _make_session()

        with patch(
            "src.services.profile_service.profile_repository"
        ) as mock_repo:
            mock_repo.get_by_user_id = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=created)

            # Act
            result = await service.get_or_create(mock_session, user_id=99)

        # Assert
        assert result is created
        mock_repo.get_by_user_id.assert_awaited_once_with(mock_session, 99)
        mock_repo.create.assert_awaited_once()
        # The created profile should have the correct user_id set
        created_arg = mock_repo.create.call_args[0][1]
        assert created_arg.user_id == 99
        assert created_arg.name == "Athlete"


# ---------------------------------------------------------------------------
# get_or_create — singleton fallback (user_id=None)
# ---------------------------------------------------------------------------


class TestGetOrCreateSingleton:
    async def test_get_or_create_returns_singleton_when_exists(self) -> None:
        # Arrange
        service = ProfileService()
        singleton = AthleteProfile(id=1, name="Athlete")
        mock_session = _make_session()

        with patch(
            "src.services.profile_service.profile_repository"
        ) as mock_repo:
            mock_repo.get_singleton = AsyncMock(return_value=singleton)

            # Act
            result = await service.get_or_create(mock_session, user_id=None)

        # Assert
        assert result is singleton
        mock_repo.get_singleton.assert_awaited_once_with(mock_session)
        mock_repo.create.assert_not_called()

    async def test_get_or_create_creates_singleton_when_missing(self) -> None:
        # Arrange
        service = ProfileService()
        new_profile = AthleteProfile(id=1, name="Athlete")
        mock_session = _make_session()

        with patch(
            "src.services.profile_service.profile_repository"
        ) as mock_repo:
            mock_repo.get_singleton = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=new_profile)

            # Act
            result = await service.get_or_create(mock_session, user_id=None)

        # Assert
        assert result is new_profile
        mock_repo.get_singleton.assert_awaited_once_with(mock_session)
        mock_repo.create.assert_awaited_once()
        # Singleton has no user_id
        created_arg = mock_repo.create.call_args[0][1]
        assert created_arg.user_id is None


# ---------------------------------------------------------------------------
# update — field mutation and zone recalc
# ---------------------------------------------------------------------------


class TestUpdate:
    async def test_update_changes_field_and_commits(self) -> None:
        # Arrange
        service = ProfileService()
        profile = AthleteProfile(id=1, name="Old Name", max_hr=180, user_id=1)
        mock_session = _make_session()

        with patch.object(service, "get_or_create", AsyncMock(return_value=profile)):
            # Act
            result = await service.update(
                mock_session, {"name": "New Name", "max_hr": 190}, user_id=1
            )

        # Assert
        assert result.name == "New Name"
        assert result.max_hr == 190
        mock_session.add.assert_called()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()

    async def test_update_ignores_none_values(self) -> None:
        # Arrange
        service = ProfileService()
        profile = AthleteProfile(id=1, name="Runner", max_hr=180, user_id=1)
        mock_session = _make_session()

        with patch.object(service, "get_or_create", AsyncMock(return_value=profile)):
            # Act
            await service.update(
                mock_session, {"name": None, "max_hr": 190}, user_id=1
            )

        # Assert — name unchanged because value was None
        assert profile.name == "Runner"
        assert profile.max_hr == 190

    async def test_update_ignores_unchanged_values(self) -> None:
        # Arrange
        service = ProfileService()
        profile = AthleteProfile(id=1, name="Runner", max_hr=180, user_id=1)
        mock_session = _make_session()

        with patch.object(service, "get_or_create", AsyncMock(return_value=profile)):
            with patch(
                "src.services.zone_service.zone_service"
            ) as mock_zone_service:
                mock_zone_service.recalculate_hr_zones = AsyncMock()
                # Act — send the same max_hr value, no lthr
                await service.update(
                    mock_session, {"max_hr": 180}, user_id=1
                )

        # Assert — no zone recalc triggered (field not changed)
        mock_zone_service.recalculate_hr_zones.assert_not_called()

    async def test_update_lthr_triggers_hr_zone_recalc(self) -> None:
        # Arrange
        service = ProfileService()
        profile = AthleteProfile(id=1, name="Runner", lthr=155, user_id=1)
        mock_session = _make_session()

        with patch.object(service, "get_or_create", AsyncMock(return_value=profile)):
            with patch(
                "src.services.zone_service.zone_service"
            ) as mock_zone_service:
                mock_zone_service.recalculate_hr_zones = AsyncMock()
                mock_zone_service.recalculate_pace_zones = AsyncMock()

                # Act
                await service.update(mock_session, {"lthr": 162}, user_id=1)

        # Assert
        mock_zone_service.recalculate_hr_zones.assert_awaited_once_with(
            mock_session, profile
        )
        mock_zone_service.recalculate_pace_zones.assert_not_called()

    async def test_update_threshold_pace_triggers_pace_zone_recalc(self) -> None:
        # Arrange
        service = ProfileService()
        profile = AthleteProfile(id=1, name="Runner", threshold_pace=280.0, user_id=1)
        mock_session = _make_session()

        with patch.object(service, "get_or_create", AsyncMock(return_value=profile)):
            with patch(
                "src.services.zone_service.zone_service"
            ) as mock_zone_service:
                mock_zone_service.recalculate_hr_zones = AsyncMock()
                mock_zone_service.recalculate_pace_zones = AsyncMock()

                # Act
                await service.update(
                    mock_session, {"threshold_pace": 270.0}, user_id=1
                )

        # Assert
        mock_zone_service.recalculate_pace_zones.assert_awaited_once_with(
            mock_session, profile
        )
        mock_zone_service.recalculate_hr_zones.assert_not_called()

    async def test_update_lthr_to_none_does_not_trigger_recalc(self) -> None:
        # Arrange — profile already has no lthr; update sends only non-threshold field
        service = ProfileService()
        profile = AthleteProfile(id=1, name="Runner", lthr=None, user_id=1)
        mock_session = _make_session()

        with patch.object(service, "get_or_create", AsyncMock(return_value=profile)):
            with patch(
                "src.services.zone_service.zone_service"
            ) as mock_zone_service:
                mock_zone_service.recalculate_hr_zones = AsyncMock()

                # Act — only changing name, not lthr
                await service.update(mock_session, {"name": "New"}, user_id=1)

        # Assert — lthr not in changed_fields → no recalc
        mock_zone_service.recalculate_hr_zones.assert_not_called()

    async def test_update_both_lthr_and_threshold_pace_triggers_both_recalcs(
        self,
    ) -> None:
        # Arrange
        service = ProfileService()
        profile = AthleteProfile(
            id=1, name="Runner", lthr=150, threshold_pace=280.0, user_id=1
        )
        mock_session = _make_session()

        with patch.object(service, "get_or_create", AsyncMock(return_value=profile)):
            with patch(
                "src.services.zone_service.zone_service"
            ) as mock_zone_service:
                mock_zone_service.recalculate_hr_zones = AsyncMock()
                mock_zone_service.recalculate_pace_zones = AsyncMock()

                # Act
                await service.update(
                    mock_session,
                    {"lthr": 162, "threshold_pace": 270.0},
                    user_id=1,
                )

        # Assert
        mock_zone_service.recalculate_hr_zones.assert_awaited_once()
        mock_zone_service.recalculate_pace_zones.assert_awaited_once()
