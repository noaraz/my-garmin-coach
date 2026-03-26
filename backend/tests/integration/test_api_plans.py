"""Integration tests for the plans API (Phase 1 + Phase 4 chat)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from unittest.mock import patch

from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import PlanCoachMessage, ScheduledWorkout, TrainingPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _workout(
    date_str: str,
    name: str = "Easy Run",
    steps_spec: str = "10m@Z1, 30m@Z2, 5m@Z1",
    sport_type: str = "running",
) -> dict[str, Any]:
    return {
        "date": date_str,
        "name": name,
        "steps_spec": steps_spec,
        "sport_type": sport_type,
    }


def _next_monday() -> str:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7
    return (today + timedelta(days=days_ahead)).isoformat()


# Use fixed future dates so tests are deterministic
_D1 = "2027-04-07"
_D2 = "2027-04-08"
_D3 = "2027-04-09"


class TestValidate:
    async def test_validate_happy_path_no_existing_plan(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Test Plan",
            "workouts": [_workout(_D1), _workout(_D2)],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_id"] > 0
        assert len(data["rows"]) == 2
        assert all(r["valid"] for r in data["rows"])
        assert data["diff"] is None

    async def test_validate_returns_draft_plan_in_db(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Draft Plan",
            "workouts": [_workout(_D1)],
        })
        plan_id = resp.json()["plan_id"]

        plan = await session.get(TrainingPlan, plan_id)
        assert plan is not None
        assert plan.status == "draft"
        assert plan.name == "Draft Plan"

    async def test_validate_bad_step_returns_422(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Bad Plan",
            "workouts": [_workout(_D1, steps_spec="INVALID")],
        })
        assert resp.status_code == 422
        rows = resp.json()["detail"]["rows"]
        assert rows[0]["valid"] is False
        assert rows[0]["error"]

    async def test_validate_bad_step_no_db_write(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "No-write Plan",
            "workouts": [_workout(_D1, steps_spec="BADTOKEN@Z1")],
        })
        assert resp.status_code == 422
        # No TrainingPlan should exist in DB for user 1
        from sqlmodel import select
        result = await session.exec(
            select(TrainingPlan).where(TrainingPlan.user_id == 1)
        )
        plans = result.all()
        assert len(plans) == 0

    async def test_validate_with_active_plan_returns_diff(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # First: import an active plan
        resp1 = await client.post("/api/v1/plans/validate", json={
            "name": "Plan A",
            "workouts": [_workout(_D1, name="Run A"), _workout(_D2, name="Run B")],
        })
        plan_id = resp1.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")

        # Second: validate a new plan (with one added, one removed, one changed)
        resp2 = await client.post("/api/v1/plans/validate", json={
            "name": "Plan B",
            "workouts": [
                _workout(_D1, name="Run A MODIFIED"),  # changed
                _workout(_D3, name="Run C"),            # added
                # D2 removed
            ],
        })
        assert resp2.status_code == 200
        diff = resp2.json()["diff"]
        assert diff is not None

        added_dates = {w["date"] for w in diff["added"]}
        removed_dates = {w["date"] for w in diff["removed"]}
        changed_dates = {w["date"] for w in diff["changed"]}

        assert _D3 in added_dates
        assert _D2 in removed_dates
        assert _D1 in changed_dates

    async def test_validate_missing_required_fields_returns_422(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Bad",
            "workouts": [{"name": "Run", "sport_type": "running"}],  # missing date + steps_spec
        })
        assert resp.status_code == 422

    async def test_validate_shows_completed_locked_when_workout_is_done(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Completed workouts appear in completed_locked, not changed, on re-validate."""
        from src.db.models import WorkoutTemplate

        # Create an active plan with one workout
        plan = TrainingPlan(
            user_id=1,
            name="Old Plan",
            source="csv",
            status="active",
            parsed_workouts='[{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "30m@Z2", "sport_type": "running", "steps": []}]',
            start_date=date(2027, 6, 1),
        )
        session.add(plan)
        await session.flush()

        # Create the corresponding template and scheduled workout (completed)
        template = WorkoutTemplate(user_id=1, name="Easy Run", sport_type="running")
        session.add(template)
        await session.flush()
        sw = ScheduledWorkout(
            user_id=1,
            date=date(2027, 6, 1),
            workout_template_id=template.id,
            training_plan_id=plan.id,
            matched_activity_id=42,  # marks as completed
        )
        session.add(sw)
        await session.commit()

        # Re-validate with different steps on the same date
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "New Plan",
            "workouts": [{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "40m@Z2"}],
        })

        assert resp.status_code == 200
        diff = resp.json()["diff"]
        assert len(diff["completed_locked"]) == 1
        assert diff["completed_locked"][0]["date"] == "2027-06-01"
        assert len(diff["changed"]) == 0

    async def test_validate_stale_draft_cleanup(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """A second validate call deletes drafts older than 24h."""
        from datetime import datetime, timedelta, timezone

        # Manually insert a stale draft
        stale = TrainingPlan(
            user_id=1,
            name="Stale",
            source="csv",
            status="draft",
            start_date=date.today(),
            parsed_workouts="[]",
            created_at=(datetime.now(timezone.utc) - timedelta(hours=25)).replace(tzinfo=None),
            updated_at=(datetime.now(timezone.utc) - timedelta(hours=25)).replace(tzinfo=None),
        )
        session.add(stale)
        await session.commit()
        await session.refresh(stale)

        # Validate again — should trigger cleanup
        await client.post("/api/v1/plans/validate", json={
            "name": "Fresh",
            "workouts": [_workout(_D1)],
        })

        # Verify stale draft was cleaned up (query by name, not ID, to avoid SQLite ID reuse)
        from sqlmodel import select
        result = await session.exec(
            select(TrainingPlan).where(
                TrainingPlan.user_id == 1,
                TrainingPlan.name == "Stale",
            )
        )
        stale_plans = result.all()
        assert len(stale_plans) == 0

    async def test_validate_template_status_new_and_existing(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Rows annotated 'existing' when template already in DB, 'new' otherwise."""
        # Create an existing template by committing a plan first
        setup = await client.post(
            "/api/v1/plans/validate",
            json={
                "name": "Setup Plan",
                "workouts": [
                    {
                        "date": "2027-08-01",
                        "name": "Easy Run",
                        "steps_spec": "10m@Z1, 30m@Z2",
                        "sport_type": "running",
                    },
                ],
            },
        )
        assert setup.status_code == 200
        await client.post(f"/api/v1/plans/{setup.json()['plan_id']}/commit")

        # Now validate a new plan: "Easy Run" (same steps = existing) + "Tempo" (new)
        resp = await client.post(
            "/api/v1/plans/validate",
            json={
                "name": "New Plan",
                "workouts": [
                    {
                        "date": "2027-09-01",
                        "name": "Easy Run",
                        "steps_spec": "10m@Z1, 30m@Z2",
                        "sport_type": "running",
                    },
                    {
                        "date": "2027-09-03",
                        "name": "Tempo",
                        "steps_spec": "10m@Z1, 20m@Z3, 5m@Z1",
                        "sport_type": "running",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        rows = resp.json()["rows"]
        assert len(rows) == 2

        easy_row = next(r for r in rows if r["name"] == "Easy Run")
        tempo_row = next(r for r in rows if r["name"] == "Tempo")

        assert easy_row["template_status"] == "existing", (
            f"Easy Run has same name+steps as existing template — expected 'existing', got {easy_row['template_status']!r}"
        )
        assert tempo_row["template_status"] == "new", (
            f"Tempo is brand new — expected 'new', got {tempo_row['template_status']!r}"
        )


class TestCommit:
    async def test_commit_fresh_plan_creates_scheduled_workouts(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Spring Plan",
            "workouts": [_workout(_D1), _workout(_D2), _workout(_D3)],
        })
        plan_id = resp.json()["plan_id"]

        commit_resp = await client.post(f"/api/v1/plans/{plan_id}/commit")
        assert commit_resp.status_code == 200
        data = commit_resp.json()
        assert data["plan_id"] == plan_id
        assert data["workout_count"] == 3
        assert data["name"] == "Spring Plan"

        # Check DB: plan is active
        plan = await session.get(TrainingPlan, plan_id)
        assert plan is not None
        assert plan.status == "active"

        # Check ScheduledWorkouts
        from sqlmodel import select
        sw_result = await session.exec(
            select(ScheduledWorkout).where(ScheduledWorkout.training_plan_id == plan_id)
        )
        sws = sw_result.all()
        assert len(sws) == 3

    async def test_commit_creates_workout_templates(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from src.db.models import WorkoutTemplate
        from sqlmodel import select

        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Template Plan",
            "workouts": [
                _workout(_D1, name="Speed Session"),
                _workout(_D2, name="Easy Run"),
            ],
        })
        plan_id = resp.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")

        result = await session.exec(
            select(WorkoutTemplate).where(WorkoutTemplate.user_id == 1)
        )
        templates = {t.name for t in result.all()}
        assert "Speed Session" in templates
        assert "Easy Run" in templates

    async def test_commit_replaces_active_plan_scheduled_workouts(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from sqlmodel import select

        # First plan: 2 workouts
        resp1 = await client.post("/api/v1/plans/validate", json={
            "name": "Plan A",
            "workouts": [_workout(_D1), _workout(_D2)],
        })
        plan_a_id = resp1.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_a_id}/commit")

        # Second plan: 1 workout
        resp2 = await client.post("/api/v1/plans/validate", json={
            "name": "Plan B",
            "workouts": [_workout(_D3)],
        })
        plan_b_id = resp2.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_b_id}/commit")

        # Old plan should be superseded
        plan_a = await session.get(TrainingPlan, plan_a_id)
        assert plan_a is not None
        assert plan_a.status == "superseded"

        # Old plan's ScheduledWorkouts should be gone
        old_sws = await session.exec(
            select(ScheduledWorkout).where(ScheduledWorkout.training_plan_id == plan_a_id)
        )
        assert len(old_sws.all()) == 0

        # New plan's workouts should exist
        new_sws = await session.exec(
            select(ScheduledWorkout).where(ScheduledWorkout.training_plan_id == plan_b_id)
        )
        assert len(new_sws.all()) == 1

    async def test_commit_nonexistent_plan_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/99999/commit")
        assert resp.status_code == 404

    async def test_commit_already_active_plan_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Active",
            "workouts": [_workout(_D1)],
        })
        plan_id = resp.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")

        # Try to commit again (plan is now active, not draft)
        resp2 = await client.post(f"/api/v1/plans/{plan_id}/commit")
        assert resp2.status_code == 404

    async def test_commit_wrong_user_returns_403(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Create a plan owned by user 2
        plan = TrainingPlan(
            user_id=2,
            name="Other User",
            source="csv",
            status="draft",
            start_date=date.today(),
            parsed_workouts='[{"date":"2027-04-07","name":"Run","steps_spec":"10m@Z1","sport_type":"running","steps":[{"type":"active","duration_type":"time","duration_sec":600.0,"zone":1}]}]',
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)

        resp = await client.post(f"/api/v1/plans/{plan.id}/commit")
        assert resp.status_code == 403

    async def test_commit_keeps_unchanged_sw_row_and_garmin_id(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Unchanged workout: existing ScheduledWorkout row is kept (same id), not recreated."""
        from src.db.models import WorkoutTemplate
        from sqlmodel import select

        # Create active plan + SW with a garmin_workout_id
        plan = TrainingPlan(
            user_id=1, name="Old", source="csv", status="active",
            parsed_workouts='[{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "30m@Z2", "sport_type": "running", "steps": []}]',
            start_date=date(2027, 6, 1),
        )
        session.add(plan)
        await session.flush()
        template = WorkoutTemplate(user_id=1, name="Easy Run", sport_type="running")
        session.add(template)
        await session.flush()
        sw = ScheduledWorkout(
            user_id=1, date=date(2027, 6, 1),
            workout_template_id=template.id, training_plan_id=plan.id,
            garmin_workout_id="garmin-123",
        )
        session.add(sw)
        await session.commit()
        original_sw_id = sw.id

        # Validate + commit with identical workout
        val_resp = await client.post("/api/v1/plans/validate", json={
            "name": "New",
            "workouts": [{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "30m@Z2"}],
        })
        plan_id = val_resp.json()["plan_id"]
        commit_resp = await client.post(f"/api/v1/plans/{plan_id}/commit")
        assert commit_resp.status_code == 200

        # The original SW row must still exist with same id and garmin_workout_id
        result = await session.exec(
            select(ScheduledWorkout).where(ScheduledWorkout.id == original_sw_id)
        )
        kept = result.first()
        assert kept is not None
        assert kept.garmin_workout_id == "garmin-123"

    async def test_commit_skips_completed_sw_even_when_changed(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Completed workout (matched_activity_id set) is not touched even if steps changed."""
        from src.db.models import WorkoutTemplate
        from sqlmodel import select

        plan = TrainingPlan(
            user_id=1, name="Old", source="csv", status="active",
            parsed_workouts='[{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "30m@Z2", "sport_type": "running", "steps": []}]',
            start_date=date(2027, 6, 1),
        )
        session.add(plan)
        await session.flush()
        template = WorkoutTemplate(user_id=1, name="Easy Run", sport_type="running")
        session.add(template)
        await session.flush()
        sw = ScheduledWorkout(
            user_id=1, date=date(2027, 6, 1),
            workout_template_id=template.id, training_plan_id=plan.id,
            matched_activity_id=99,
        )
        session.add(sw)
        await session.commit()
        original_sw_id = sw.id

        # Validate + commit with changed steps
        val_resp = await client.post("/api/v1/plans/validate", json={
            "name": "New",
            "workouts": [{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "50m@Z2"}],
        })
        plan_id = val_resp.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")

        # Completed SW must still exist with matched_activity_id intact
        result = await session.exec(
            select(ScheduledWorkout).where(ScheduledWorkout.id == original_sw_id)
        )
        kept = result.first()
        assert kept is not None
        assert kept.matched_activity_id == 99

    async def test_commit_replaces_changed_workout(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Changed workout: old SW row deleted, new SW row created for new plan."""
        from src.db.models import WorkoutTemplate
        from sqlmodel import select

        plan = TrainingPlan(
            user_id=1, name="Old", source="csv", status="active",
            parsed_workouts='[{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "30m@Z2", "sport_type": "running", "steps": []}]',
            start_date=date(2027, 6, 1),
        )
        session.add(plan)
        await session.flush()
        old_plan_id = plan.id
        template = WorkoutTemplate(user_id=1, name="Easy Run", sport_type="running")
        session.add(template)
        await session.flush()
        sw = ScheduledWorkout(
            user_id=1, date=date(2027, 6, 1),
            workout_template_id=template.id, training_plan_id=plan.id,
        )
        session.add(sw)
        await session.commit()

        val_resp = await client.post("/api/v1/plans/validate", json={
            "name": "New",
            "workouts": [{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "50m@Z2"}],
        })
        plan_id = val_resp.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")

        # No SW should belong to the old plan anymore
        old_plan_sws = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.training_plan_id == old_plan_id,
            )
        )
        assert old_plan_sws.first() is None

        # New SW must exist for same date, linked to new plan
        new_result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.user_id == 1,
                ScheduledWorkout.date == date(2027, 6, 1),
                ScheduledWorkout.training_plan_id == plan_id,
            )
        )
        assert new_result.first() is not None

    async def test_commit_same_name_same_steps_deduplicates_template(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Two workouts with identical name + steps_spec share ONE template."""
        from sqlmodel import select
        from src.db.models import ScheduledWorkout, WorkoutTemplate

        resp = await client.post(
            "/api/v1/plans/validate",
            json={
                "name": "Dedup Test Plan",
                "workouts": [
                    {
                        "date": "2027-05-05",
                        "name": "Easy Run",
                        "steps_spec": "10m@Z1, 30m@Z2",
                        "sport_type": "running",
                    },
                    {
                        "date": "2027-05-07",
                        "name": "Easy Run",
                        "steps_spec": "10m@Z1, 30m@Z2",
                        "sport_type": "running",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        plan_id = resp.json()["plan_id"]

        commit_resp = await client.post(f"/api/v1/plans/{plan_id}/commit")
        assert commit_resp.status_code == 200

        templates = (
            await session.exec(
                select(WorkoutTemplate).where(
                    WorkoutTemplate.user_id == 1,
                    WorkoutTemplate.name == "Easy Run",
                )
            )
        ).all()
        assert len(templates) == 1, f"Expected 1 template, got {len(templates)}"

        sws = (
            await session.exec(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.training_plan_id == plan_id
                )
            )
        ).all()
        assert len(sws) == 2
        assert sws[0].workout_template_id == sws[1].workout_template_id

    async def test_commit_same_name_different_steps_creates_separate_templates(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Two workouts with same name but different steps_spec get separate templates."""
        from sqlmodel import select
        from src.db.models import ScheduledWorkout, WorkoutTemplate

        resp = await client.post(
            "/api/v1/plans/validate",
            json={
                "name": "Split Template Plan",
                "workouts": [
                    {
                        "date": "2027-06-02",
                        "name": "Easy Run",
                        "steps_spec": "10m@Z1, 30m@Z2",
                        "sport_type": "running",
                    },
                    {
                        "date": "2027-06-04",
                        "name": "Easy Run",
                        "steps_spec": "5m@Z1, 50m@Z2",
                        "sport_type": "running",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        plan_id = resp.json()["plan_id"]

        commit_resp = await client.post(f"/api/v1/plans/{plan_id}/commit")
        assert commit_resp.status_code == 200

        templates = (
            await session.exec(
                select(WorkoutTemplate).where(
                    WorkoutTemplate.user_id == 1,
                    WorkoutTemplate.name == "Easy Run",
                )
            )
        ).all()
        assert len(templates) == 2, f"Expected 2 templates, got {len(templates)}"

        sws = (
            await session.exec(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.training_plan_id == plan_id
                )
            )
        ).all()
        assert len(sws) == 2
        assert sws[0].workout_template_id != sws[1].workout_template_id

    async def test_commit_reuses_template_when_reimporting_same_workout(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Re-importing a plan with a new date for an existing workout reuses the template."""
        from sqlmodel import select

        from src.db.models import ScheduledWorkout, WorkoutTemplate

        # Commit plan A — one "Easy Run" workout, creates template T1
        resp_a = await client.post(
            "/api/v1/plans/validate",
            json={
                "name": "Plan A",
                "workouts": [
                    {
                        "date": "2027-07-01",
                        "name": "Easy Run",
                        "steps_spec": "10m@Z1, 30m@Z2",
                        "sport_type": "running",
                    },
                ],
            },
        )
        assert resp_a.status_code == 200
        await client.post(f"/api/v1/plans/{resp_a.json()['plan_id']}/commit")

        # Re-import plan B — same workout at a new date added
        resp_b = await client.post(
            "/api/v1/plans/validate",
            json={
                "name": "Plan B",
                "workouts": [
                    {
                        "date": "2027-07-01",
                        "name": "Easy Run",
                        "steps_spec": "10m@Z1, 30m@Z2",
                        "sport_type": "running",
                    },
                    {
                        "date": "2027-07-03",  # new date, same workout
                        "name": "Easy Run",
                        "steps_spec": "10m@Z1, 30m@Z2",
                        "sport_type": "running",
                    },
                ],
            },
        )
        assert resp_b.status_code == 200
        plan_b_id = resp_b.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_b_id}/commit")

        # Still only ONE template — re-import reuses it
        templates = (
            await session.exec(
                select(WorkoutTemplate).where(
                    WorkoutTemplate.user_id == 1,
                    WorkoutTemplate.name == "Easy Run",
                )
            )
        ).all()
        assert len(templates) == 1, f"Expected 1 template after re-import, got {len(templates)}"

        # Both SWs in plan B point to the same template
        sws = (
            await session.exec(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.training_plan_id == plan_b_id
                )
            )
        ).all()
        assert len(sws) == 2
        assert sws[0].workout_template_id == sws[1].workout_template_id


class TestGetActive:
    async def test_get_active_when_no_plan_returns_204(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.get("/api/v1/plans/active")
        assert resp.status_code == 204

    async def test_get_active_returns_plan(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Active Plan",
            "workouts": [_workout(_D1)],
        })
        plan_id = resp.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")

        resp2 = await client.get("/api/v1/plans/active")
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["name"] == "Active Plan"
        assert data["status"] == "active"
        assert data["workout_count"] == 1  # one workout committed


class TestDelete:
    async def test_delete_removes_plan_and_scheduled_workouts(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from sqlmodel import select

        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Delete Me",
            "workouts": [_workout(_D1), _workout(_D2)],
        })
        plan_id = resp.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")

        del_resp = await client.delete(f"/api/v1/plans/{plan_id}")
        assert del_resp.status_code == 204

        # Plan gone
        plan = await session.get(TrainingPlan, plan_id)
        assert plan is None

        # ScheduledWorkouts gone
        sws = await session.exec(
            select(ScheduledWorkout).where(ScheduledWorkout.training_plan_id == plan_id)
        )
        assert len(sws.all()) == 0

    async def test_delete_keeps_workout_templates(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from src.db.models import WorkoutTemplate
        from sqlmodel import select

        resp = await client.post("/api/v1/plans/validate", json={
            "name": "Keep Templates",
            "workouts": [_workout(_D1, name="Tempo Run")],
        })
        plan_id = resp.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")
        await client.delete(f"/api/v1/plans/{plan_id}")

        result = await session.exec(
            select(WorkoutTemplate).where(
                WorkoutTemplate.user_id == 1,
                WorkoutTemplate.name == "Tempo Run",
            )
        )
        templates = result.all()
        assert len(templates) == 1  # template still exists

    async def test_delete_nonexistent_plan_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.delete("/api/v1/plans/99999")
        assert resp.status_code == 404

    async def test_delete_wrong_user_returns_403(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        plan = TrainingPlan(
            user_id=2,
            name="Other",
            source="csv",
            status="active",
            start_date=date.today(),
            parsed_workouts="[]",
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)

        resp = await client.delete(f"/api/v1/plans/{plan.id}")
        assert resp.status_code == 403

    async def test_delete_plan_garmin_cleanup_does_not_affect_other_users_workouts(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """IDOR security test: user B attempting to delete user A's plan must NOT
        trigger Garmin deletions for user A's workouts."""
        from collections.abc import AsyncGenerator
        from unittest.mock import Mock

        from httpx import ASGITransport
        from src.api.app import create_app
        from src.api.dependencies import get_session
        from src.api.routers.sync import get_optional_garmin_sync_service
        from src.auth.dependencies import get_current_user
        from src.auth.models import User
        from src.db.models import WorkoutTemplate

        # User A (id=2) creates a plan with a synced workout
        plan_a = TrainingPlan(
            user_id=2,
            name="User A Plan",
            source="csv",
            status="active",
            start_date=date(2027, 6, 1),
            parsed_workouts='[{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "30m@Z2", "sport_type": "running", "steps": []}]',
        )
        session.add(plan_a)
        await session.flush()

        template_a = WorkoutTemplate(user_id=2, name="Easy Run", sport_type="running")
        session.add(template_a)
        await session.flush()

        sw_a = ScheduledWorkout(
            user_id=2,
            date=date(2027, 6, 1),
            workout_template_id=template_a.id,
            training_plan_id=plan_a.id,
            garmin_workout_id="garmin-999",  # synced workout
        )
        session.add(sw_a)
        await session.commit()
        await session.refresh(plan_a)

        # Mock the Garmin sync service
        mock_delete = Mock()
        mock_garmin = Mock()
        mock_garmin.delete_workout = mock_delete

        async def mock_garmin_dependency() -> Mock:
            return mock_garmin

        async def override_session() -> AsyncGenerator[AsyncSession, None]:
            yield session

        async def override_user() -> User:
            return User(id=1, email="test@example.com", is_active=True)

        # Create a new app and client with mocked dependencies
        app = create_app()
        app.dependency_overrides[get_optional_garmin_sync_service] = mock_garmin_dependency
        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_user] = override_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            # User B (id=1, the default test user) attempts to delete user A's plan
            resp = await test_client.delete(f"/api/v1/plans/{plan_a.id}")

        # User B should get a 403 (ownership check fails in delete_plan)
        assert resp.status_code == 403

        # The critical security check: Garmin delete_workout must NOT have been called
        # If it was called, that means we fetched user A's workouts before checking ownership
        mock_delete.assert_not_called()


# ---------------------------------------------------------------------------
# Phase 4 — Chat endpoints
# ---------------------------------------------------------------------------

_FAKE_REPLY = "Great goal! Let me put together a 10-week plan for you."
_FAKE_PLAN_REPLY = (
    "Here is your plan:\n\n"
    "```json\n"
    '[{"date":"2027-04-07","name":"Easy Run","description":"Recovery","steps_spec":"30m@Z2","sport_type":"running"}]\n'
    "```"
)


class TestChatHistory:
    async def test_history_empty_when_no_messages(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.get("/api/v1/plans/chat/history")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_history_returns_messages_oldest_first(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from datetime import datetime, timezone

        # Seed two messages directly
        msg1 = PlanCoachMessage(
            user_id=1,
            role="user",
            content="Hello",
            created_at=datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None),
        )
        msg2 = PlanCoachMessage(
            user_id=1,
            role="assistant",
            content="Hi there!",
            created_at=datetime(2026, 4, 1, 10, 0, 1, tzinfo=timezone.utc).replace(tzinfo=None),
        )
        session.add(msg1)
        session.add(msg2)
        await session.commit()

        resp = await client.get("/api/v1/plans/chat/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Hello"
        assert data[1]["role"] == "assistant"

    async def test_history_excludes_other_users_messages(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # Message owned by user_id=2 — should not appear for user 1
        msg = PlanCoachMessage(
            user_id=2,
            role="user",
            content="Other user's message",
        )
        session.add(msg)
        await session.commit()

        resp = await client.get("/api/v1/plans/chat/history")
        assert resp.status_code == 200
        assert resp.json() == []


class TestSendChatMessage:
    async def test_send_message_returns_assistant_reply(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        with patch(
            "src.services.plan_coach_service.chat_completion",
            return_value=_FAKE_REPLY,
        ):
            resp = await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "I want to run a half marathon in 10 weeks"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "assistant"
        assert data["content"] == _FAKE_REPLY
        assert "id" in data
        assert "created_at" in data

    async def test_send_message_persists_both_messages(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from sqlmodel import select

        with patch(
            "src.services.plan_coach_service.chat_completion",
            return_value=_FAKE_REPLY,
        ):
            await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "Plan me a 5K"},
            )

        result = await session.exec(
            select(PlanCoachMessage)
            .where(PlanCoachMessage.user_id == 1)
            .order_by(PlanCoachMessage.created_at)
        )
        messages = result.all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Plan me a 5K"
        assert messages[1].role == "assistant"
        assert messages[1].content == _FAKE_REPLY

    async def test_send_empty_content_returns_422(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        resp = await client.post(
            "/api/v1/plans/chat/message",
            json={"content": "   "},
        )
        assert resp.status_code == 422

    async def test_send_message_no_api_key_returns_503(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        with patch(
            "src.services.plan_coach_service.chat_completion",
            side_effect=RuntimeError("GEMINI_API_KEY is not configured"),
        ):
            resp = await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "Help me train"},
            )
        assert resp.status_code == 503
        assert "GEMINI_API_KEY" in resp.json()["detail"]

    async def test_send_message_history_grows_with_each_turn(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        with patch(
            "src.services.plan_coach_service.chat_completion",
            return_value="First reply",
        ):
            await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "Turn 1"},
            )

        with patch(
            "src.services.plan_coach_service.chat_completion",
            return_value="Second reply",
        ):
            await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "Turn 2"},
            )

        resp = await client.get("/api/v1/plans/chat/history")
        assert resp.status_code == 200
        assert len(resp.json()) == 4  # 2 user + 2 assistant


# ---------------------------------------------------------------------------
# Garmin dedup on commit_plan
# ---------------------------------------------------------------------------


class TestCommitPlanGarminDedup:
    """Tests for Garmin workout dedup during plan commit."""

    async def test_commit_plan_pre_links_garmin_workout_by_name(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """New SWs are pre-linked to existing Garmin workouts by name."""
        from unittest.mock import MagicMock

        from sqlmodel import select

        from src.services.plan_import_service import commit_plan, validate_plan

        # Validate a plan
        result = await validate_plan(
            session,
            user_id=1,
            workouts=[_workout(_D1, name="Easy Run"), _workout(_D2, name="Tempo Run")],
            plan_name="Dedup Plan",
        )

        # Create a mock garmin with existing workouts on Garmin
        mock_garmin = MagicMock()
        mock_garmin.adapter.get_workouts.return_value = [
            {"workoutId": "gw-easy", "workoutName": "Easy Run"},
            {"workoutId": "gw-tempo", "workoutName": "Tempo Run"},
        ]

        # Commit with garmin dedup
        await commit_plan(session, user_id=1, plan_id=result.plan_id, garmin=mock_garmin)

        # Check: new SWs should have garmin_workout_id pre-linked
        sws_result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.training_plan_id == result.plan_id
            )
        )
        sws = sws_result.all()
        assert len(sws) == 2

        garmin_ids = {sw.garmin_workout_id for sw in sws}
        assert "gw-easy" in garmin_ids
        assert "gw-tempo" in garmin_ids

        # All pre-linked SWs should be "modified" (not "pending")
        assert all(sw.sync_status == "modified" for sw in sws)

    async def test_commit_plan_skips_dedup_when_garmin_is_none(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """When garmin is None, SWs are created with pending status and no garmin_workout_id."""
        from sqlmodel import select

        from src.services.plan_import_service import commit_plan, validate_plan

        result = await validate_plan(
            session,
            user_id=1,
            workouts=[_workout(_D1, name="Easy Run")],
            plan_name="No Garmin Plan",
        )

        await commit_plan(session, user_id=1, plan_id=result.plan_id, garmin=None)

        sws_result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.training_plan_id == result.plan_id
            )
        )
        sws = sws_result.all()
        assert len(sws) == 1
        assert sws[0].garmin_workout_id is None
        assert sws[0].sync_status == "pending"

    async def test_commit_plan_handles_get_workouts_failure(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Commit still succeeds if garmin.adapter.get_workouts() raises."""
        from unittest.mock import MagicMock

        from sqlmodel import select

        from src.services.plan_import_service import commit_plan, validate_plan

        result = await validate_plan(
            session,
            user_id=1,
            workouts=[_workout(_D1, name="Easy Run")],
            plan_name="Garmin Failure Plan",
        )

        mock_garmin = MagicMock()
        mock_garmin.adapter.get_workouts.side_effect = RuntimeError("API down")

        # Should not raise
        await commit_plan(session, user_id=1, plan_id=result.plan_id, garmin=mock_garmin)

        sws_result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.training_plan_id == result.plan_id
            )
        )
        sws = sws_result.all()
        assert len(sws) == 1
        # Falls back to pending with no garmin_workout_id
        assert sws[0].garmin_workout_id is None
        assert sws[0].sync_status == "pending"
