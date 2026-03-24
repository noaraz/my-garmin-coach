from __future__ import annotations

from datetime import date, timedelta

from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import ScheduledWorkout, WorkoutTemplate


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
        template = WorkoutTemplate(name="Old Name", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        # Act — description is always derived from steps, not set directly
        response = await client.put(
            f"/api/v1/workouts/{template.id}",
            json={"name": "New Name", "steps": [{"type": "active", "duration_type": "time", "duration_sec": 600, "target_type": "pace_zone", "zone": 2}]},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "10m@Z2"

    async def test_delete(self, client: AsyncClient, session: AsyncSession) -> None:
        # Arrange
        template = WorkoutTemplate(name="To Delete", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        # Act
        response = await client.delete(f"/api/v1/workouts/{template.id}")

        # Assert
        assert response.status_code == 204
        deleted = await session.get(WorkoutTemplate, template.id)
        assert deleted is None

    async def test_update_marks_synced_future_workout_as_modified(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """PUT /workouts/{id} → linked future synced workout becomes modified."""
        # Arrange
        template = WorkoutTemplate(name="Speed Work", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        future_date = date.today() + timedelta(days=3)
        sw = ScheduledWorkout(
            workout_template_id=template.id,
            date=future_date,
            sync_status="synced",
            resolved_steps='[{"step": 1}]',
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        # Act
        response = await client.put(
            f"/api/v1/workouts/{template.id}",
            json={"name": "Speed Work v2"},
        )

        # Assert
        assert response.status_code == 200
        await session.refresh(sw)
        assert sw.sync_status == "modified"
        assert sw.resolved_steps is None

    async def test_update_also_marks_past_synced_workouts_as_modified(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """PUT /workouts/{id} → past non-completed synced workouts are re-queued.

        A workout scheduled for yesterday (or earlier) that is already 'synced'
        should also be marked 'modified' when the template changes, so Sync All
        can re-push it.  This prevents sync_all from returning 0 just because
        the only scheduled workout happens to be from the day before.
        """
        # Arrange
        template = WorkoutTemplate(name="Easy Run", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        past_date = date.today() - timedelta(days=5)
        sw = ScheduledWorkout(
            workout_template_id=template.id,
            date=past_date,
            sync_status="synced",
            resolved_steps='[{"step": 1}]',
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        # Act
        await client.put(
            f"/api/v1/workouts/{template.id}",
            json={"name": "Easy Run Renamed"},
        )

        # Assert — past non-completed workout IS now re-queued
        await session.refresh(sw)
        assert sw.sync_status == "modified"
        assert sw.resolved_steps is None

    async def test_update_leaves_pending_status_unchanged_but_clears_resolved_steps(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """PUT /workouts/{id} → pending future workout stays pending; resolved_steps cleared."""
        # Arrange
        template = WorkoutTemplate(name="Tempo", sport_type="running", user_id=1)
        session.add(template)
        await session.commit()
        await session.refresh(template)

        future_date = date.today() + timedelta(days=1)
        sw = ScheduledWorkout(
            workout_template_id=template.id,
            date=future_date,
            sync_status="pending",
            resolved_steps='[{"step": 1}]',
        )
        session.add(sw)
        await session.commit()
        await session.refresh(sw)

        # Act
        await client.put(
            f"/api/v1/workouts/{template.id}",
            json={"name": "Tempo v2"},
        )

        # Assert — status stays pending (already queued); stale cache cleared
        await session.refresh(sw)
        assert sw.sync_status == "pending"
        assert sw.resolved_steps is None
