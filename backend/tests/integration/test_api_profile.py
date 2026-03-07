from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.db.models import AthleteProfile, HRZone


class TestProfileAPI:
    def test_get_profile(self, client: TestClient, session: Session) -> None:
        # Arrange — seed a profile
        profile = AthleteProfile(name="Runner", max_hr=185, lthr=162)
        session.add(profile)
        session.commit()

        # Act
        response = client.get("/api/profile")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Runner"
        assert data["max_hr"] == 185
        assert data["lthr"] == 162

    def test_update_profile(self, client: TestClient, session: Session) -> None:
        # Arrange — seed a profile
        profile = AthleteProfile(name="Runner", max_hr=180)
        session.add(profile)
        session.commit()

        # Act
        response = client.put("/api/profile", json={"name": "Updated Runner", "max_hr": 190})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Runner"
        assert data["max_hr"] == 190

    def test_update_lthr_triggers_recalc(
        self, client: TestClient, session: Session
    ) -> None:
        # Arrange — seed a profile with LTHR
        profile = AthleteProfile(name="Runner", max_hr=185, lthr=155)
        session.add(profile)
        session.commit()
        session.refresh(profile)
        profile_id = profile.id

        # Act — update LTHR, which should trigger HR zone recalculation
        response = client.put("/api/profile", json={"lthr": 162})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["lthr"] == 162

        # Zones should now exist in the DB (recalculated)
        session.expire_all()
        hr_zones = session.exec(
            select(HRZone).where(HRZone.profile_id == profile_id)
        ).all()
        assert len(hr_zones) == 5
