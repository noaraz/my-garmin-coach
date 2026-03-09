from __future__ import annotations

from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile, HRZone


class TestProfileAPI:
    async def test_get_profile(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange — seed a profile owned by the mock test user (id=1)
        profile = AthleteProfile(name="Runner", max_hr=185, lthr=162, user_id=1)
        session.add(profile)
        await session.commit()

        # Act
        response = await client.get("/api/v1/profile")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Runner"
        assert data["max_hr"] == 185
        assert data["lthr"] == 162

    async def test_update_profile(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange — seed a profile owned by the mock test user (id=1)
        profile = AthleteProfile(name="Runner", max_hr=180, user_id=1)
        session.add(profile)
        await session.commit()

        # Act
        response = await client.put("/api/v1/profile", json={"name": "Updated Runner", "max_hr": 190})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Runner"
        assert data["max_hr"] == 190

    async def test_update_lthr_triggers_recalc(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange — seed a profile with LTHR owned by the mock test user (id=1)
        profile = AthleteProfile(name="Runner", max_hr=185, lthr=155, user_id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        profile_id = profile.id

        # Act — update LTHR, which should trigger HR zone recalculation
        response = await client.put("/api/v1/profile", json={"lthr": 162})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["lthr"] == 162

        # Zones should now exist in the DB (recalculated)
        result = await session.exec(
            select(HRZone).where(HRZone.profile_id == profile_id)
        )
        hr_zones = result.all()
        assert len(hr_zones) == 5
