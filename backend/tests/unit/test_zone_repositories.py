from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.db.models import HRZone, PaceZone
from src.repositories.zones import HRZoneRepository, PaceZoneRepository


class TestHRZoneRepositoryDeleteByProfile:
    """Tests for HRZoneRepository.delete_by_profile using bulk DELETE."""

    @pytest.mark.asyncio
    async def test_delete_by_profile_uses_bulk_delete(self) -> None:
        # Arrange
        repo = HRZoneRepository(HRZone)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # Act
        await repo.delete_by_profile(mock_session, profile_id=1)

        # Assert — execute called once with DELETE statement
        mock_session.execute.assert_awaited_once()
        call_args = mock_session.execute.call_args[0][0]
        # Verify it's a DELETE statement for HRZone table
        assert str(call_args).startswith("DELETE FROM hrzone")
        # Verify WHERE clause includes profile_id
        assert "hrzone.profile_id = " in str(call_args)

    @pytest.mark.asyncio
    async def test_delete_by_profile_does_not_commit(self) -> None:
        # Arrange
        repo = HRZoneRepository(HRZone)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        # Act
        await repo.delete_by_profile(mock_session, profile_id=1)

        # Assert — commit NOT called (caller commits)
        mock_session.commit.assert_not_awaited()


class TestPaceZoneRepositoryDeleteByProfile:
    """Tests for PaceZoneRepository.delete_by_profile using bulk DELETE."""

    @pytest.mark.asyncio
    async def test_delete_by_profile_uses_bulk_delete(self) -> None:
        # Arrange
        repo = PaceZoneRepository(PaceZone)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # Act
        await repo.delete_by_profile(mock_session, profile_id=1)

        # Assert — execute called once with DELETE statement
        mock_session.execute.assert_awaited_once()
        call_args = mock_session.execute.call_args[0][0]
        # Verify it's a DELETE statement for PaceZone table
        assert str(call_args).startswith("DELETE FROM pacezone")
        # Verify WHERE clause includes profile_id
        assert "pacezone.profile_id = " in str(call_args)

    @pytest.mark.asyncio
    async def test_delete_by_profile_does_not_commit(self) -> None:
        # Arrange
        repo = PaceZoneRepository(PaceZone)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        # Act
        await repo.delete_by_profile(mock_session, profile_id=1)

        # Assert — commit NOT called (caller commits)
        mock_session.commit.assert_not_awaited()
