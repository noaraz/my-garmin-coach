from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app


class TestGarminAuthVersionEndpoint:
    """Test the admin endpoint for switching garmin auth version."""

    @pytest.fixture
    def app(self):
        return create_app()

    @pytest.fixture
    async def client(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_set_garmin_auth_version_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated users cannot switch the auth version."""
        resp = await client.post(
            "/api/v1/admin/garmin-auth-version",
            json={"version": "v2"},
        )
        assert resp.status_code == 401

    async def test_get_garmin_auth_version_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated users cannot read the auth version."""
        resp = await client.get("/api/v1/admin/garmin-auth-version")
        assert resp.status_code == 401
