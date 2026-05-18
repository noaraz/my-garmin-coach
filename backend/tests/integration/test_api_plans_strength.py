"""Integration tests for strength-sport plan flow.

Convention: asyncio_mode = "auto" in pyproject.toml means class-based async tests
run without @pytest.mark.asyncio. Do not add it.
"""
from __future__ import annotations

from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession


class TestStrengthPlanFlow:
    async def test_validate_strength_csv_creates_strength_draft(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        csv = (
            "date,name,steps\n"
            "2027-06-01,Lower body,Squat 3x5@80kg; RDL 3x8@RPE8; Plank 3x45s\n"
        )
        r = await client.post(
            "/api/v1/plans/validate",
            json={"sport": "strength", "csv": csv},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["sport"] == "strength"
        assert len(body["rows"]) == 1
        assert body["rows"][0]["status"] == "valid"

    async def test_strength_validate_with_unknown_exercise_is_error(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        csv = "date,name,steps\n2027-06-01,X,Nordic Curl 3x6@bw\n"
        r = await client.post(
            "/api/v1/plans/validate",
            json={"sport": "strength", "csv": csv},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["plan_id"] == -1
        row = body["rows"][0]
        assert row["status"] == "error"
        assert any(e["code"] == "unknown_exercise" for e in row["errors"])

    async def test_commit_strength_plan_does_not_supersede_running_plan(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Validate + commit a running plan
        run_csv = [{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "45m@Z2"}]
        v = await client.post(
            "/api/v1/plans/validate",
            json={"sport": "run", "workouts": run_csv},
        )
        assert v.status_code == 200
        run_plan_id = v.json()["plan_id"]
        await client.post(f"/api/v1/plans/{run_plan_id}/commit")

        # Validate + commit a strength plan
        str_csv = "date,name,steps\n2027-06-02,Lower body,Squat 3x5@80kg\n"
        v2 = await client.post(
            "/api/v1/plans/validate",
            json={"sport": "strength", "csv": str_csv},
        )
        assert v2.status_code == 200
        str_plan_id = v2.json()["plan_id"]
        await client.post(f"/api/v1/plans/{str_plan_id}/commit")

        # Both plans must be active independently
        run_active = await client.get("/api/v1/plans/active?sport=run")
        str_active = await client.get("/api/v1/plans/active?sport=strength")
        assert run_active.status_code == 200
        assert str_active.status_code == 200
        assert run_active.json()["plan_id"] == run_plan_id
        assert str_active.json()["plan_id"] == str_plan_id

    async def test_reimport_strength_supersedes_only_strength(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Commit initial strength plan
        csv1 = "date,name,steps\n2027-06-02,Lower body,Squat 3x5@80kg\n"
        _first_id = await _validate_and_commit(client, "strength", csv1)
        # Commit a replacement strength plan
        csv2 = "date,name,steps\n2027-06-09,Lower body 2,Squat 3x5@85kg\n"
        second_id = await _validate_and_commit(client, "strength", csv2)
        # The active strength plan should now be the second one
        r = await client.get("/api/v1/plans/active?sport=strength")
        assert r.status_code == 200
        assert r.json()["plan_id"] == second_id


async def _validate_and_commit(client: AsyncClient, sport: str, csv: str) -> int:
    v = await client.post(
        "/api/v1/plans/validate",
        json={"sport": sport, "csv": csv},
    )
    assert v.status_code == 200, f"Validate failed: {v.json()}"
    plan_id = v.json()["plan_id"]
    assert plan_id > 0, f"Expected valid plan_id, got {plan_id}. Rows: {v.json()['rows']}"
    await client.post(f"/api/v1/plans/{plan_id}/commit")
    return plan_id
