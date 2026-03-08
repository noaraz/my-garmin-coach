from __future__ import annotations

from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import WorkoutTemplate


class TestWorkoutsAPI:
    def _make_steps(self) -> list[dict]:
        return [
            {
                "order": 1,
                "type": "warmup",
                "duration_type": "time",
                "duration_value": 600,
                "duration_unit": "seconds",
                "target_type": "hr_zone",
                "target_zone": 1,
                "steps": [],
            }
        ]

    async def test_create(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        payload = {
            "name": "Easy Run",
            "description": "A nice easy run",
            "sport_type": "running",
            "tags": ["easy"],
            "steps": self._make_steps(),
        }

        # Act
        response = await client.post("/api/v1/workouts", json=payload)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Easy Run"

    async def test_list(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange — templates owned by the mock test user (id=1)
        for i in range(3):
            session.add(WorkoutTemplate(name=f"Run {i}", sport_type="running", user_id=1))
        await session.commit()

        # Act
        response = await client.get("/api/v1/workouts")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    async def test_update(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="Old Name", sport_type="running")
        session.add(template)
        await session.commit()
        await session.refresh(template)

        # Act
        response = await client.put(
            f"/api/v1/workouts/{template.id}",
            json={"name": "New Name", "description": "Updated"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "Updated"

    async def test_delete(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="To Delete", sport_type="running")
        session.add(template)
        await session.commit()
        await session.refresh(template)

        # Act
        response = await client.delete(f"/api/v1/workouts/{template.id}")

        # Assert
        assert response.status_code == 204
        deleted = await session.get(WorkoutTemplate, template.id)
        assert deleted is None
