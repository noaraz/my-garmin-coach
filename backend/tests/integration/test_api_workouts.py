from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlmodel import Session

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

    def test_create(self, client: TestClient, session: Session) -> None:
        # Arrange
        payload = {
            "name": "Easy Run",
            "description": "A nice easy run",
            "sport_type": "running",
            "tags": ["easy"],
            "steps": self._make_steps(),
        }

        # Act
        response = client.post("/api/workouts", json=payload)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Easy Run"

    def test_list(self, client: TestClient, session: Session) -> None:
        # Arrange
        for i in range(3):
            session.add(WorkoutTemplate(name=f"Run {i}", sport_type="running"))
        session.commit()

        # Act
        response = client.get("/api/workouts")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_update(self, client: TestClient, session: Session) -> None:
        # Arrange
        template = WorkoutTemplate(name="Old Name", sport_type="running")
        session.add(template)
        session.commit()
        session.refresh(template)

        # Act
        response = client.put(
            f"/api/workouts/{template.id}",
            json={"name": "New Name", "description": "Updated"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "Updated"

    def test_delete(self, client: TestClient, session: Session) -> None:
        # Arrange
        template = WorkoutTemplate(name="To Delete", sport_type="running")
        session.add(template)
        session.commit()
        session.refresh(template)

        # Act
        response = client.delete(f"/api/workouts/{template.id}")

        # Assert
        assert response.status_code == 204
        deleted = session.get(WorkoutTemplate, template.id)
        assert deleted is None
