from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from src.api.app import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
