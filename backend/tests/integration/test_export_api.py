from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.routers.sync import _get_garmin_sync_service
from src.auth.dependencies import get_current_user
from src.db.models import GarminActivity


async def _mock_get_garmin_sync_service():
    """Mock Garmin sync service for tests."""
    mock = MagicMock()
    mock.get_activity.return_value = {"activityId": "12345"}
    mock.get_activity_splits.return_value = []
    return mock


class TestExportAPI:
    async def test_export_returns_json_file(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange: seed one activity
        activity = GarminActivity(
            user_id=1,
            garmin_activity_id="12345",
            name="Morning Run",
            date=date(2026, 1, 15),
            start_time=datetime(2026, 1, 15, 7, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None),
            activity_type="running",
            distance_m=5000.0,
            duration_sec=1500.0,
        )
        session.add(activity)
        await session.commit()

        # Mock export_service.build_export
        mock_export_data = {
            "exported_at": "2026-04-21T10:00:00",
            "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
            "activities": [
                {
                    "garmin_activity_id": "12345",
                    "name": "Morning Run",
                    "date": "2026-01-15",
                    "activity_type": "running",
                    "summary": {"distance": 5000.0},
                    "laps": [{"lapIndex": 0}],
                }
            ],
        }

        # Mock the Garmin sync service
        from src.api.app import create_app
        from src.api.dependencies import get_session
        from httpx import ASGITransport

        app = create_app()

        async def override_session():
            yield session

        async def _mock_current_user():
            from src.auth.models import User
            return User(id=1, email="test@example.com", is_active=True)

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_user] = _mock_current_user
        app.dependency_overrides[_get_garmin_sync_service] = _mock_get_garmin_sync_service

        with patch(
            "src.services.export_service.export_service.build_export",
            new_callable=AsyncMock,
        ) as mock_build:
            mock_build.return_value = mock_export_data

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
                # Act
                response = await test_client.get(
                    "/api/v1/calendar/activities/export?start=2026-01-01&end=2026-01-31"
                )

                # Assert
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/json"
                assert "attachment" in response.headers.get("content-disposition", "")
                assert "garmin-export-2026-01-01-2026-01-31.json" in response.headers.get(
                    "content-disposition", ""
                )

                data = response.json()
                assert data["exported_at"] == "2026-04-21T10:00:00"
                assert len(data["activities"]) == 1
                assert data["activities"][0]["garmin_activity_id"] == "12345"

        app.dependency_overrides.clear()

    async def test_export_empty_range_returns_empty_list(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange: no activities in DB
        mock_export_data = {
            "exported_at": "2026-04-21T10:00:00",
            "date_range": {"start": "2026-02-01", "end": "2026-02-28"},
            "activities": [],
        }

        # Mock the Garmin sync service
        from src.api.app import create_app
        from src.api.dependencies import get_session
        from httpx import ASGITransport

        app = create_app()

        async def override_session():
            yield session

        async def _mock_current_user():
            from src.auth.models import User
            return User(id=1, email="test@example.com", is_active=True)

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_user] = _mock_current_user
        app.dependency_overrides[_get_garmin_sync_service] = _mock_get_garmin_sync_service

        with patch(
            "src.services.export_service.export_service.build_export",
            new_callable=AsyncMock,
        ) as mock_build:
            mock_build.return_value = mock_export_data

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
                # Act
                response = await test_client.get(
                    "/api/v1/calendar/activities/export?start=2026-02-01&end=2026-02-28"
                )

                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["activities"] == []

        app.dependency_overrides.clear()

    async def test_export_requires_auth(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange: clear the auth override to simulate no token
        from src.api.app import create_app
        from src.api.dependencies import get_session

        app = create_app()

        async def override_session():
            yield session

        # Intentionally do NOT override get_current_user — will fail auth
        app.dependency_overrides[get_session] = override_session

        from httpx import ASGITransport

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as no_auth_client:
            # Act
            response = await no_auth_client.get(
                "/api/v1/calendar/activities/export?start=2026-01-01&end=2026-01-31"
            )

            # Assert
            assert response.status_code == 401

    async def test_export_requires_garmin(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from fastapi import HTTPException
        from src.api.app import create_app
        from src.api.dependencies import get_session
        from src.api.routers.sync import _get_garmin_sync_service
        from httpx import ASGITransport

        app = create_app()

        async def override_session():
            yield session

        async def _mock_current_user():
            from src.auth.models import User
            return User(id=1, email="test@example.com", is_active=True)

        async def _garmin_not_connected():
            raise HTTPException(status_code=403, detail="Garmin not connected")

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_user] = _mock_current_user
        app.dependency_overrides[_get_garmin_sync_service] = _garmin_not_connected

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
            response = await test_client.get(
                "/api/v1/calendar/activities/export?start=2026-01-01&end=2026-01-31"
            )
            assert response.status_code == 403

        app.dependency_overrides.clear()
