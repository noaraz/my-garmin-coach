from __future__ import annotations

import json
from datetime import date

from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile, HRZone, PaceZone, ScheduledWorkout, WorkoutTemplate
from src.repositories.zones import hr_zone_repository, pace_zone_repository


class TestHRZonesAPI:
    async def _seed_profile_with_lthr(
        self, session: AsyncSession, lthr: int = 162
    ) -> AthleteProfile:
        profile = AthleteProfile(name="Runner", max_hr=185, lthr=lthr, user_id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile

    async def test_get_hr_zones(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        profile = await self._seed_profile_with_lthr(session)
        for i in range(1, 6):
            session.add(
                HRZone(
                    profile_id=profile.id,
                    zone_number=i,
                    name=f"Zone {i}",
                    lower_bpm=100.0 + i * 10,
                    upper_bpm=110.0 + i * 10,
                    calculation_method="coggan",
                    pct_lower=0.60,
                    pct_upper=0.70,
                )
            )
        await session.commit()

        # Act
        response = await client.get("/api/v1/zones/hr")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    async def test_set_hr_zones_custom(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        await self._seed_profile_with_lthr(session)
        custom_zones = [
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

        # Act
        response = await client.put("/api/v1/zones/hr", json=custom_zones)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert all(z["calculation_method"] == "custom" for z in data)

    async def test_recalculate_hr_zones(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        await self._seed_profile_with_lthr(session, lthr=162)

        # Act
        response = await client.post("/api/v1/zones/hr/recalculate")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        # Coggan Zone 4 should be ~94-105% of LTHR
        zone4 = next(z for z in data if z["zone_number"] == 4)
        assert abs(zone4["lower_bpm"] - 162 * 0.94) < 1.0

    async def test_get_pace_zones(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", threshold_pace=270.0, user_id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        for i in range(1, 6):
            session.add(
                PaceZone(
                    profile_id=profile.id,
                    zone_number=i,
                    name=f"Pace Zone {i}",
                    lower_pace=300.0,
                    upper_pace=270.0,
                    calculation_method="pct_threshold",
                    pct_lower=1.10,
                    pct_upper=1.00,
                )
            )
        await session.commit()

        # Act
        response = await client.get("/api/v1/zones/pace")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    async def test_recalculate_pace_zones(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange
        profile = AthleteProfile(name="Runner", threshold_pace=270.0, user_id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        # Act
        response = await client.post("/api/v1/zones/pace/recalculate")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    async def test_get_hr_zones_empty_when_none_exist(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange — profile with no zones
        session.add(AthleteProfile(name="Runner", user_id=1))
        await session.commit()

        # Act
        response = await client.get("/api/v1/zones/hr")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_pace_zones_empty_when_none_exist(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange — profile with no pace zones
        session.add(AthleteProfile(name="Runner", user_id=1))
        await session.commit()

        # Act
        response = await client.get("/api/v1/zones/pace")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    async def test_zone_change_re_resolves(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Arrange — profile with LTHR owned by the mock test user (id=1)
        profile = AthleteProfile(name="Runner", max_hr=185, lthr=155, user_id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        # Create a workout template with HR zone reference
        steps = [
            {
                "order": 1, "type": "active", "duration_type": "time",
                "duration_value": 1800, "duration_unit": "seconds",
                "target_type": "hr_zone", "target_zone": 3,
                "steps": []
            }
        ]
        template = WorkoutTemplate(
            name="Tempo", sport_type="running", steps=json.dumps(steps)
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)

        # Schedule a future workout (date in future)
        scheduled = ScheduledWorkout(
            date=date(2027, 1, 1),
            workout_template_id=template.id,
            sync_status="synced",
        )
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)

        # Act — recalculate HR zones with new LTHR (triggers cascade)
        response = await client.post("/api/v1/zones/hr/recalculate")

        # Assert
        assert response.status_code == 200
        updated = await session.get(ScheduledWorkout, scheduled.id)
        # resolved_steps should be populated and sync_status updated to "modified"
        assert updated.resolved_steps is not None
        assert updated.sync_status == "modified"


class TestZoneRepository:
    """Direct repository tests covering get_by_profile and delete_by_profile."""

    async def _seed_profile(self, session: AsyncSession) -> AthleteProfile:
        profile = AthleteProfile(name="Runner", user_id=1)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile

    async def test_hr_zone_get_by_profile_returns_ordered_zones(
        self, session: AsyncSession, client: AsyncClient
    ) -> None:
        # Arrange
        profile = await self._seed_profile(session)
        for i in [3, 1, 5, 2, 4]:  # insert out-of-order
            session.add(
                HRZone(
                    profile_id=profile.id,
                    zone_number=i,
                    name=f"Zone {i}",
                    lower_bpm=100.0 + i * 10,
                    upper_bpm=110.0 + i * 10,
                    calculation_method="coggan",
                    pct_lower=0.60,
                    pct_upper=0.70,
                )
            )
        await session.commit()

        # Act
        zones = await hr_zone_repository.get_by_profile(session, profile.id)

        # Assert — zones returned in ascending zone_number order
        assert [z.zone_number for z in zones] == [1, 2, 3, 4, 5]

    async def test_hr_zone_get_by_profile_returns_empty_list_for_unknown_profile(
        self, session: AsyncSession, client: AsyncClient
    ) -> None:
        # Act
        zones = await hr_zone_repository.get_by_profile(session, 9999)

        # Assert
        assert zones == []

    async def test_hr_zone_delete_by_profile_removes_all_zones(
        self, session: AsyncSession, client: AsyncClient
    ) -> None:
        # Arrange
        profile = await self._seed_profile(session)
        for i in range(1, 4):
            session.add(
                HRZone(
                    profile_id=profile.id,
                    zone_number=i,
                    name=f"Zone {i}",
                    lower_bpm=100.0,
                    upper_bpm=120.0,
                    calculation_method="coggan",
                    pct_lower=0.60,
                    pct_upper=0.70,
                )
            )
        await session.commit()

        # Act
        await hr_zone_repository.delete_by_profile(session, profile.id)

        # Assert
        remaining = await hr_zone_repository.get_by_profile(session, profile.id)
        assert remaining == []

    async def test_pace_zone_get_by_profile_returns_ordered_zones(
        self, session: AsyncSession, client: AsyncClient
    ) -> None:
        # Arrange
        profile = await self._seed_profile(session)
        for i in [4, 2, 5, 1, 3]:  # insert out-of-order
            session.add(
                PaceZone(
                    profile_id=profile.id,
                    zone_number=i,
                    name=f"Pace Zone {i}",
                    lower_pace=300.0,
                    upper_pace=270.0,
                    calculation_method="pct_threshold",
                    pct_lower=1.10,
                    pct_upper=1.00,
                )
            )
        await session.commit()

        # Act
        zones = await pace_zone_repository.get_by_profile(session, profile.id)

        # Assert — zones returned in ascending zone_number order
        assert [z.zone_number for z in zones] == [1, 2, 3, 4, 5]

    async def test_pace_zone_get_by_profile_returns_empty_for_unknown_profile(
        self, session: AsyncSession, client: AsyncClient
    ) -> None:
        # Act
        zones = await pace_zone_repository.get_by_profile(session, 9999)

        # Assert
        assert zones == []

    async def test_pace_zone_delete_by_profile_removes_all_zones(
        self, session: AsyncSession, client: AsyncClient
    ) -> None:
        # Arrange
        profile = await self._seed_profile(session)
        for i in range(1, 4):
            session.add(
                PaceZone(
                    profile_id=profile.id,
                    zone_number=i,
                    name=f"Pace Zone {i}",
                    lower_pace=300.0,
                    upper_pace=270.0,
                    calculation_method="pct_threshold",
                    pct_lower=1.10,
                    pct_upper=1.00,
                )
            )
        await session.commit()

        # Act
        await pace_zone_repository.delete_by_profile(session, profile.id)

        # Assert
        remaining = await pace_zone_repository.get_by_profile(session, profile.id)
        assert remaining == []
