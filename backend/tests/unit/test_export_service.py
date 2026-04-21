from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

from src.garmin.adapter_protocol import GarminAdapterError
from src.services.export_service import export_service


class TestExportService:
    async def test_build_export_returns_correct_shape(self):
        # Arrange
        session = AsyncMock()
        user_id = 1
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)

        # Mock DB response with no activities
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        garmin = MagicMock()

        # Act
        result = await export_service.build_export(session, user_id, garmin, start, end)

        # Assert
        assert "exported_at" in result
        assert "date_range" in result
        assert "activities" in result
        assert result["date_range"]["start"] == "2026-01-01"
        assert result["date_range"]["end"] == "2026-01-31"
        assert isinstance(result["activities"], list)

    async def test_build_export_includes_laps(self):
        # Arrange
        session = AsyncMock()
        user_id = 1
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)

        # Mock a single activity
        from src.db.models import GarminActivity
        activity = GarminActivity(
            id=1,
            user_id=user_id,
            garmin_activity_id="123456",
            name="Morning Run",
            date=date(2026, 1, 15),
            activity_type="running",
            distance_m=5000.0,
            duration_sec=1500.0,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [activity]
        session.execute.return_value = mock_result

        garmin = MagicMock()
        garmin.get_activity.return_value = {
            "activityId": "123456",
            "activityName": "Morning Run",
            "distance": 5000.0,
        }
        garmin.get_activity_splits.return_value = [
            {"lapIndex": 0, "distance": 1000.0, "duration": 300.0},
            {"lapIndex": 1, "distance": 1000.0, "duration": 305.0},
        ]

        # Act
        result = await export_service.build_export(session, user_id, garmin, start, end)

        # Assert
        assert len(result["activities"]) == 1
        assert result["activities"][0]["garmin_activity_id"] == "123456"
        assert result["activities"][0]["name"] == "Morning Run"
        assert "laps" in result["activities"][0]
        assert len(result["activities"][0]["laps"]) == 2
        assert result["activities"][0]["laps"][0]["lapIndex"] == 0

    async def test_build_export_activity_error_does_not_abort(self):
        # Arrange
        session = AsyncMock()
        user_id = 1
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)

        from src.db.models import GarminActivity
        activity1 = GarminActivity(
            id=1,
            user_id=user_id,
            garmin_activity_id="111",
            name="Run 1",
            date=date(2026, 1, 10),
            activity_type="running",
        )
        activity2 = GarminActivity(
            id=2,
            user_id=user_id,
            garmin_activity_id="222",
            name="Run 2",
            date=date(2026, 1, 20),
            activity_type="running",
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [activity1, activity2]
        session.execute.return_value = mock_result

        garmin = MagicMock()
        # First activity fails, second succeeds — use function side_effect to avoid
        # order-sensitivity when tasks run concurrently via asyncio.gather.
        def get_activity_side_effect(activity_id: str):
            if activity_id == "111":
                raise GarminAdapterError("Network error")
            return {"activityId": activity_id, "activityName": "Run 2"}

        def get_splits_side_effect(activity_id: str):
            if activity_id == "111":
                raise GarminAdapterError("Network error")
            return [{"lapIndex": 0}]

        garmin.get_activity.side_effect = get_activity_side_effect
        garmin.get_activity_splits.side_effect = get_splits_side_effect

        # Act
        result = await export_service.build_export(session, user_id, garmin, start, end)

        # Assert
        assert len(result["activities"]) == 2
        # First activity should have error
        assert result["activities"][0]["garmin_activity_id"] == "111"
        assert result["activities"][0]["error"] == "fetch_failed"
        assert "laps" not in result["activities"][0]
        # Second activity should succeed
        assert result["activities"][1]["garmin_activity_id"] == "222"
        assert "error" not in result["activities"][1]
        assert "laps" in result["activities"][1]

    async def test_build_export_empty_range(self):
        # Arrange
        session = AsyncMock()
        user_id = 1
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        garmin = MagicMock()

        # Act
        result = await export_service.build_export(session, user_id, garmin, start, end)

        # Assert
        assert result["activities"] == []
        garmin.get_activity.assert_not_called()
        garmin.get_activity_splits.assert_not_called()
