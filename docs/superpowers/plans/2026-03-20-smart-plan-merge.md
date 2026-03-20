# Smart Plan Merge Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `commit_plan` do a smart merge — keeping unchanged and completed workouts in place, replacing only what changed, and surfacing all 5 statuses (added/removed/changed/unchanged/completed_locked) in the validate diff UI.

**Architecture:** Extend `DiffResult` with two new buckets (`unchanged`, `completed_locked`) and enrich `WorkoutDiff` with before/after fields for changed rows. `validate_plan` fetches completed dates in one extra query and passes them to `_compute_diff`. `commit_plan` does two batch queries (SWs + templates), classifies each workout, bulk-deletes only what needs replacing, and batch-adds only new rows — single commit. Frontend `DiffTable` renders all 5 row variants.

**Spec:** `docs/superpowers/specs/2026-03-20-smart-plan-merge-design.md`

**Tech Stack:** FastAPI, SQLModel, SQLAlchemy async, React 18, TypeScript, Vitest, pytest

---

## Chunk 1: Docs Update

### Task 1: Update `features/plan-coach/PLAN.md`

**Files:**
- Modify: `features/plan-coach/PLAN.md`

- [ ] **Step 1: Append Phase 5 section**

Append to `features/plan-coach/PLAN.md`:

```markdown
## Phase 5 — Smart Plan Merge `feature/smart-plan-merge`

### Backend
- `_compute_diff` — new `completed_dates: set[str]` param; 5 output buckets
- `validate_plan` — one extra query for completed dates
- `commit_plan` — smart merge: batch-load SWs + templates, classify, bulk delete, batch add

### Frontend
- `WorkoutDiff` type — add `old_name?`, `old_steps_spec?`, `new_steps_spec?`
- `DiffResult` type — add `unchanged[]`, `completed_locked[]`
- `DiffTable.tsx` — 5 row variants + before→after for changed

### Tests
- Backend unit: `test_compute_diff_*` (3 new)
- Backend integration: `test_commit_plan_*` (3 new)
- Frontend: `DiffTable` (4 new RTL tests)
```

- [ ] **Step 2: Commit**

```bash
git add features/plan-coach/PLAN.md
git commit -m "docs: add Phase 5 smart plan merge to plan-coach PLAN.md"
```

---

### Task 2: Update `features/plan-coach/CLAUDE.md`

**Files:**
- Modify: `features/plan-coach/CLAUDE.md`

- [ ] **Step 1: Add Smart Merge section after the existing Re-import Diff section**

Find the `### Re-import Diff` section in `features/plan-coach/CLAUDE.md`. After its closing paragraph, insert:

````markdown
### Re-import Diff — Smart Merge (Phase 5)

`DiffResult` now has 5 buckets. `WorkoutDiff` carries optional before/after fields:

```python
class WorkoutDiff(BaseModel):
    date: str
    name: str
    old_name: str | None = None        # changed only
    old_steps_spec: str | None = None  # changed only
    new_steps_spec: str | None = None  # changed only

class DiffResult(BaseModel):
    added: list[WorkoutDiff]
    removed: list[WorkoutDiff]
    changed: list[WorkoutDiff]
    unchanged: list[WorkoutDiff]        # kept as-is (no DB change)
    completed_locked: list[WorkoutDiff] # matched_activity_id IS NOT NULL — never touched
```

`_compute_diff` signature (third arg has default for backward compat):

```python
def _compute_diff(
    incoming: list[ParsedWorkout],
    active_parsed: list[dict],
    completed_dates: set[str] = set(),
) -> DiffResult
```

### Smart Merge in `commit_plan`

`commit_plan` accepts an optional `garmin: Any | None = None` parameter and does:
1. Batch-load all SWs for active plan — one query
2. Batch-load their templates — one query (`WHERE id IN (template_ids)`)
3. Classify: completed_locked/unchanged → skip; changed/added → recreate; removed → delete
4. Garmin cleanup for deleted garmin_workout_ids
5. Bulk `DELETE WHERE id IN (...)` — single statement
6. Batch `session.add()` all new SWs — single `session.commit()`

### Neon Rules
- No N+1: SWs and templates loaded in 2 queries, looked up from dicts
- `completed_dates`: only the `date` column loaded (not full ORM objects)
- Bulk delete via `sqlalchemy.delete(...).where(ScheduledWorkout.id.in_(ids))`
- Single commit after all mutations
````

- [ ] **Step 2: Commit**

```bash
git add features/plan-coach/CLAUDE.md
git commit -m "docs: update plan-coach CLAUDE.md with smart merge patterns"
```

---

### Task 3: Update `STATUS.md`

**Files:**
- Modify: `STATUS.md`

- [ ] **Step 1: Add Phase 5 section and update last-updated line**

In `STATUS.md`, change the first line to:
```
Last updated: 2026-03-20 (Smart Plan Merge — Phase 5 in progress)
```

After the `### Plan Coach — Phase 4b` block, add:

```markdown
### Plan Coach — Phase 5: Smart Plan Merge `feature/smart-plan-merge` 🟡
| Task | Status |
|------|--------|
| Docs: PLAN.md, CLAUDE.md, STATUS.md, root CLAUDE.md | 🟡 |
| Backend: enrich WorkoutDiff + DiffResult schema | ⬜ |
| Backend: _compute_diff with completed_dates + 5 buckets | ⬜ |
| Backend: validate_plan completed_dates query | ⬜ |
| Backend: commit_plan smart merge (batch load, classify, bulk delete) | ⬜ |
| Backend unit tests: _compute_diff (3 tests) | ⬜ |
| Backend integration tests: commit_plan smart merge (3 tests) | ⬜ |
| Frontend: WorkoutDiff + DiffResult types | ⬜ |
| Frontend: DiffTable — 5 row variants + before→after changed | ⬜ |
| Frontend: DiffTable RTL tests (4 tests) | ⬜ |
```

- [ ] **Step 2: Commit**

```bash
git add STATUS.md
git commit -m "docs: add Phase 5 smart plan merge to STATUS.md"
```

---

### Task 4: Update root `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update Plan Coach feature table entry**

In `CLAUDE.md`, find the Plan Coach row in the Features table and update the description column to:

```
Multi-week training plan via CSV import or Gemini Flash chat; validate/diff/commit pipeline; smart merge (keep unchanged + completed workouts on re-import)
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update root CLAUDE.md Plan Coach description for smart merge"
```

---

## Chunk 2: Backend Schema + `_compute_diff`

### Task 5: Extend `WorkoutDiff`, `DiffResult`, and rewrite `_compute_diff`

**Files:**
- Modify: `backend/src/services/plan_import_service.py`
- Create: `backend/tests/unit/test_plan_import_service.py`

- [ ] **Step 1: Write failing unit tests**

Create `backend/tests/unit/test_plan_import_service.py`:

```python
"""Unit tests for plan_import_service diff logic."""
from __future__ import annotations

from src.services.plan_import_service import (
    ParsedWorkout,
    _compute_diff,
)


def _pw(date: str, name: str, steps_spec: str) -> ParsedWorkout:
    return ParsedWorkout(date=date, name=name, steps_spec=steps_spec, steps=[])


def _active(date: str, name: str, steps_spec: str) -> dict:
    return {"date": date, "name": name, "steps_spec": steps_spec}


class TestComputeDiff:
    def test_unchanged_when_same_name_and_steps(self) -> None:
        incoming = [_pw("2026-04-07", "Easy Run", "30m@Z2")]
        active = [_active("2026-04-07", "Easy Run", "30m@Z2")]

        result = _compute_diff(incoming, active, completed_dates=set())

        assert len(result.unchanged) == 1
        assert result.unchanged[0].date == "2026-04-07"
        assert len(result.added) == 0
        assert len(result.changed) == 0

    def test_changed_when_steps_differ_populates_before_after(self) -> None:
        incoming = [_pw("2026-04-07", "Easy Run", "40m@Z2")]
        active = [_active("2026-04-07", "Easy Run", "30m@Z2")]

        result = _compute_diff(incoming, active, completed_dates=set())

        assert len(result.changed) == 1
        diff = result.changed[0]
        assert diff.old_steps_spec == "30m@Z2"
        assert diff.new_steps_spec == "40m@Z2"
        assert diff.old_name == "Easy Run"
        assert len(result.unchanged) == 0

    def test_completed_locked_overrides_changed(self) -> None:
        incoming = [_pw("2026-04-07", "Easy Run", "40m@Z2")]
        active = [_active("2026-04-07", "Easy Run", "30m@Z2")]

        result = _compute_diff(incoming, active, completed_dates={"2026-04-07"})

        assert len(result.completed_locked) == 1
        assert result.completed_locked[0].date == "2026-04-07"
        assert len(result.changed) == 0
        assert len(result.unchanged) == 0
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
docker compose exec backend pytest tests/unit/test_plan_import_service.py -v
```

Expected: `TypeError` — `_compute_diff` does not yet accept `completed_dates`, and `DiffResult` has no `unchanged`/`completed_locked`.

- [ ] **Step 3: Extend `WorkoutDiff`**

In `backend/src/services/plan_import_service.py`, replace the `WorkoutDiff` class:

```python
class WorkoutDiff(BaseModel):
    date: str
    name: str
    old_name: str | None = None        # populated for "changed" only
    old_steps_spec: str | None = None  # populated for "changed" only
    new_steps_spec: str | None = None  # populated for "changed" only
```

- [ ] **Step 4: Extend `DiffResult`**

Replace the `DiffResult` class:

```python
class DiffResult(BaseModel):
    added: list[WorkoutDiff]
    removed: list[WorkoutDiff]
    changed: list[WorkoutDiff]
    unchanged: list[WorkoutDiff] = []
    completed_locked: list[WorkoutDiff] = []
```

- [ ] **Step 5: Rewrite `_compute_diff`**

Replace the entire `_compute_diff` function. The new signature adds `completed_dates` with a default of `frozenset()` so existing callers (`validate_plan` before Task 6 updates it) continue to work:

```python
def _compute_diff(
    incoming: list[ParsedWorkout],
    active_parsed: list[dict],
    completed_dates: set[str] = set(),
) -> DiffResult:
    """Compute added/removed/changed/unchanged/completed_locked vs the active plan."""
    active_by_date = {w["date"]: w for w in active_parsed}
    incoming_by_date = {w.date: w for w in incoming}

    added: list[WorkoutDiff] = []
    removed: list[WorkoutDiff] = []
    changed: list[WorkoutDiff] = []
    unchanged: list[WorkoutDiff] = []
    completed_locked: list[WorkoutDiff] = []

    for date_str, workout in incoming_by_date.items():
        if date_str in completed_dates:
            completed_locked.append(WorkoutDiff(date=date_str, name=workout.name))
        elif date_str not in active_by_date:
            added.append(WorkoutDiff(date=date_str, name=workout.name))
        else:
            active = active_by_date[date_str]
            same_name = active.get("name") == workout.name
            same_steps = active.get("steps_spec") == workout.steps_spec
            if same_name and same_steps:
                unchanged.append(WorkoutDiff(date=date_str, name=workout.name))
            else:
                changed.append(WorkoutDiff(
                    date=date_str,
                    name=workout.name,
                    old_name=active.get("name"),
                    old_steps_spec=active.get("steps_spec"),
                    new_steps_spec=workout.steps_spec,
                ))

    for date_str, active in active_by_date.items():
        if date_str not in incoming_by_date and date_str not in completed_dates:
            removed.append(WorkoutDiff(date=date_str, name=active.get("name", "")))

    return DiffResult(
        added=added,
        removed=removed,
        changed=changed,
        unchanged=unchanged,
        completed_locked=completed_locked,
    )
```

- [ ] **Step 6: Run unit tests — expect PASS**

```bash
docker compose exec backend pytest tests/unit/test_plan_import_service.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 7: Run existing integration tests — confirm no regression**

```bash
docker compose exec backend pytest tests/integration/test_api_plans.py -v
```

Expected: all existing tests PASS (new buckets default to `[]`; `completed_dates` defaults to `frozenset()`).

- [ ] **Step 8: Commit**

```bash
git add backend/src/services/plan_import_service.py backend/tests/unit/test_plan_import_service.py
git commit -m "feat: enrich WorkoutDiff + DiffResult with 5 diff buckets and rewrite _compute_diff"
```

---

### Task 6: Update `validate_plan` to pass `completed_dates`

**Files:**
- Modify: `backend/src/services/plan_import_service.py` (validate_plan function)
- Modify: `backend/tests/integration/test_api_plans.py`

- [ ] **Step 1: Write failing integration test**

In `backend/tests/integration/test_api_plans.py`, add inside the `TestValidate` class:

```python
    async def test_validate_shows_completed_locked_when_workout_is_done(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """Completed workouts appear in completed_locked, not changed, on re-validate."""
        from src.db.models import WorkoutTemplate
        from sqlmodel import select

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
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose exec backend pytest tests/integration/test_api_plans.py::TestValidate::test_validate_shows_completed_locked_when_workout_is_done -v
```

Expected: assertion fails — `completed_locked` is empty (completed_dates not yet queried in validate_plan).

- [ ] **Step 3: Update `validate_plan` diff computation block**

In `plan_import_service.py`, find the `validate_plan` function. Replace lines starting from `# Compute diff against active plan if one exists` through the `diff = _compute_diff(...)` call (approximately lines 218–223) with:

```python
    # Compute diff against active plan if one exists
    diff: DiffResult | None = None
    active = await get_active_plan(session, user_id)
    if active and active.parsed_workouts:
        active_parsed = json.loads(active.parsed_workouts)
        # Fetch completed dates — single query, date column only (no full ORM objects)
        completed_result = await session.exec(
            select(ScheduledWorkout.date).where(
                ScheduledWorkout.training_plan_id == active.id,
                ScheduledWorkout.matched_activity_id.isnot(None),  # type: ignore[union-attr]
            )
        )
        completed_dates = {str(row) for row in completed_result.all()}
        diff = _compute_diff(parsed_list, active_parsed, completed_dates)
```

The `diff: DiffResult | None = None` initialization on the first line is essential — it is the variable returned at the end of the function when there is no active plan.

- [ ] **Step 4: Run integration test — expect PASS**

```bash
docker compose exec backend pytest tests/integration/test_api_plans.py::TestValidate::test_validate_shows_completed_locked_when_workout_is_done -v
```

Expected: PASS.

- [ ] **Step 5: Run full plan test suite**

```bash
docker compose exec backend pytest tests/integration/test_api_plans.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/plan_import_service.py backend/tests/integration/test_api_plans.py
git commit -m "feat: validate_plan fetches completed_dates for smart diff"
```

---

## Chunk 3: Backend Smart Merge in `commit_plan`

### Task 7: Rewrite `commit_plan` with smart merge

**Files:**
- Modify: `backend/src/services/plan_import_service.py` (commit_plan function)
- Modify: `backend/src/api/routers/plans.py` (post_commit — pass garmin to commit_plan)
- Modify: `backend/tests/integration/test_api_plans.py`

- [ ] **Step 1: Write failing integration tests**

In `backend/tests/integration/test_api_plans.py`, add inside the `TestCommit` class:

```python
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
        """Changed workout: old SW row deleted, new SW row created."""
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
        )
        session.add(sw)
        await session.commit()
        old_sw_id = sw.id

        val_resp = await client.post("/api/v1/plans/validate", json={
            "name": "New",
            "workouts": [{"date": "2027-06-01", "name": "Easy Run", "steps_spec": "50m@Z2"}],
        })
        plan_id = val_resp.json()["plan_id"]
        await client.post(f"/api/v1/plans/{plan_id}/commit")

        # Old SW must be gone
        old_result = await session.exec(
            select(ScheduledWorkout).where(ScheduledWorkout.id == old_sw_id)
        )
        assert old_result.first() is None

        # New SW must exist for same date
        new_result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.user_id == 1,
                ScheduledWorkout.date == date(2027, 6, 1),
            )
        )
        new_sw = new_result.first()
        assert new_sw is not None
        assert new_sw.id != old_sw_id
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
docker compose exec backend pytest tests/integration/test_api_plans.py::TestCommit::test_commit_keeps_unchanged_sw_row_and_garmin_id tests/integration/test_api_plans.py::TestCommit::test_commit_skips_completed_sw_even_when_changed tests/integration/test_api_plans.py::TestCommit::test_commit_replaces_changed_workout -v
```

Expected: `test_commit_keeps_unchanged_sw_row_and_garmin_id` and `test_commit_skips_completed_sw_even_when_changed` FAIL (SW gets deleted and recreated). `test_commit_replaces_changed_workout` may PASS trivially (old behavior already replaces everything) — that's expected.

- [ ] **Step 3: Add module-level imports to `plan_import_service.py`**

At the top of `plan_import_service.py`, add these imports (alongside the existing ones). `from typing import Any` is already present — verify first:

```python
import logging
from datetime import date as date_type

logger = logging.getLogger(__name__)
```

`from datetime import datetime, timedelta, timezone` is already at line 12. Add `date as date_type` to that same import line:

```python
from datetime import date as date_type, datetime, timedelta, timezone
```

And add `import logging` + `logger = ...` at module level (after the existing imports, before the `# ---------------------------------------------------------------------------` section).

- [ ] **Step 4: Rewrite `commit_plan` with smart merge**

Replace the entire `commit_plan` function in `plan_import_service.py`:

```python
async def commit_plan(
    session: AsyncSession,
    user_id: int,
    plan_id: int,
    garmin: Any | None = None,
) -> CommitResult:
    """Commit a draft plan with smart merge.

    - Unchanged workouts (same date, name, steps_spec): kept as-is.
    - Completed workouts (matched_activity_id IS NOT NULL): never touched.
    - Changed workouts: old SW deleted (Garmin cleanup), new SW created.
    - Added workouts: new SW created.
    - Removed workouts (not in incoming, not completed): old SW deleted.
    """

    plan = await session.get(TrainingPlan, plan_id)
    if plan is None or plan.status != "draft":
        raise ValueError(f"TrainingPlan {plan_id} not found or not a draft")
    if plan.user_id != user_id:
        raise ValueError(f"TrainingPlan {plan_id} does not belong to user {user_id}")

    parsed_workouts: list[dict] = json.loads(plan.parsed_workouts or "[]")

    active = await get_active_plan(session, user_id)

    # -----------------------------------------------------------------------
    # Smart merge setup: batch-load existing SWs and their templates
    # -----------------------------------------------------------------------
    sw_by_date: dict[str, ScheduledWorkout] = {}
    template_by_id: dict[int, WorkoutTemplate] = {}
    active_steps_by_date: dict[str, str] = {}
    active_name_by_date: dict[str, str] = {}
    completed_dates: set[str] = set()

    if active is not None:
        # Batch 1: all scheduled workouts for active plan — single query
        sw_result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.training_plan_id == active.id
            )
        )
        all_sws = sw_result.all()
        sw_by_date = {str(sw.date): sw for sw in all_sws}

        # Batch 2: all templates for those SWs — single query, no N+1
        template_ids = {sw.workout_template_id for sw in all_sws if sw.workout_template_id}
        if template_ids:
            tmpl_result = await session.exec(
                select(WorkoutTemplate).where(WorkoutTemplate.id.in_(template_ids))
            )
            template_by_id = {t.id: t for t in tmpl_result.all()}

        # Completed dates: only the date column — no full ORM objects
        completed_result = await session.exec(
            select(ScheduledWorkout.date).where(
                ScheduledWorkout.training_plan_id == active.id,
                ScheduledWorkout.matched_activity_id.isnot(None),  # type: ignore[union-attr]
            )
        )
        completed_dates = {str(row) for row in completed_result.all()}

        # Parse the active plan's steps_spec for comparison
        if active.parsed_workouts:
            for pw_dict in json.loads(active.parsed_workouts):
                d = pw_dict.get("date", "")
                active_steps_by_date[d] = pw_dict.get("steps_spec", "")
                active_name_by_date[d] = pw_dict.get("name", "")

        active.status = "superseded"
        active.updated_at = _now()
        session.add(active)

    # -----------------------------------------------------------------------
    # Classify each incoming workout
    # -----------------------------------------------------------------------
    ids_to_delete: list[int] = []
    garmin_ids_to_delete: list[str] = []
    sws_to_create: list[dict] = []
    incoming_dates: set[str] = set()

    for pw_dict in parsed_workouts:
        pw = ParsedWorkout(**pw_dict)
        incoming_dates.add(pw.date)
        existing_sw = sw_by_date.get(pw.date)

        if existing_sw is not None:
            # Completed — never touch
            if pw.date in completed_dates:
                continue

            # Compare using active plan's stored steps_spec (source of truth)
            same_name = active_name_by_date.get(pw.date) == pw.name
            same_steps = active_steps_by_date.get(pw.date) == pw.steps_spec
            if same_name and same_steps:
                continue  # unchanged — keep existing row as-is

            # Changed: queue old SW for deletion, queue new SW for creation
            ids_to_delete.append(existing_sw.id)  # type: ignore[arg-type]
            if existing_sw.garmin_workout_id:
                garmin_ids_to_delete.append(existing_sw.garmin_workout_id)

        sws_to_create.append(pw_dict)

    # Removed: in active plan, not in incoming, not completed
    for date_str, sw in sw_by_date.items():
        if date_str not in incoming_dates and date_str not in completed_dates:
            ids_to_delete.append(sw.id)  # type: ignore[arg-type]
            if sw.garmin_workout_id:
                garmin_ids_to_delete.append(sw.garmin_workout_id)

    # -----------------------------------------------------------------------
    # Garmin cleanup (must happen before DB delete — one API call per workout)
    # -----------------------------------------------------------------------
    if garmin is not None:
        for garmin_id in garmin_ids_to_delete:
            try:
                garmin.delete_workout(garmin_id)
                logger.info("Smart merge: deleted Garmin workout %s", garmin_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not delete Garmin workout %s: %s", garmin_id, exc)

    # -----------------------------------------------------------------------
    # Bulk delete — single statement
    # -----------------------------------------------------------------------
    if ids_to_delete:
        await session.execute(
            delete(ScheduledWorkout).where(ScheduledWorkout.id.in_(ids_to_delete))
        )

    # -----------------------------------------------------------------------
    # Batch-load/create templates; batch-add new SWs
    # -----------------------------------------------------------------------
    templates_result = await session.exec(
        select(WorkoutTemplate).where(WorkoutTemplate.user_id == user_id)
    )
    existing_templates = {t.name: t for t in templates_result.all()}

    now = _now()
    new_sw_count = 0

    for pw_dict in sws_to_create:
        pw = ParsedWorkout(**pw_dict)
        try:
            workout_date = date_type.fromisoformat(pw.date)
        except ValueError:
            continue

        if pw.name in existing_templates:
            template = existing_templates[pw.name]
        else:
            steps_json = json.dumps(pw.steps) if pw.steps else None
            template = WorkoutTemplate(
                user_id=user_id,
                name=pw.name,
                description=pw.description,
                sport_type=pw.sport_type,
                steps=steps_json,
                created_at=now,
                updated_at=now,
            )
            session.add(template)
            await session.flush()
            existing_templates[pw.name] = template

        sw = ScheduledWorkout(
            user_id=user_id,
            date=workout_date,
            workout_template_id=template.id,
            training_plan_id=plan_id,
            sync_status="pending",
            created_at=now,
            updated_at=now,
        )
        session.add(sw)
        new_sw_count += 1

    # Total = kept (unchanged + completed_locked) + newly created
    kept_count = len(sw_by_date) - len(ids_to_delete)
    total_workout_count = max(0, kept_count) + new_sw_count

    plan.status = "active"
    plan.updated_at = now
    session.add(plan)
    await session.commit()

    return CommitResult(
        plan_id=plan.id,  # type: ignore[arg-type]
        name=plan.name,
        workout_count=total_workout_count,
        start_date=plan.start_date.isoformat(),
    )
```

- [ ] **Step 5: Simplify `post_commit` router — remove duplicate Garmin logic**

The router's `post_commit` previously had its own Garmin cleanup block before calling `commit_plan`. That logic is now inside `commit_plan`. Replace `post_commit` in `backend/src/api/routers/plans.py`:

```python
@router.post("/{plan_id}/commit", response_model=CommitResult)
async def post_commit(
    plan_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    garmin: SyncOrchestrator | None = Depends(get_optional_garmin_sync_service),
) -> CommitResult:
    """Commit a draft plan using smart merge.

    Unchanged and completed workouts are preserved. Changed workouts trigger
    Garmin cleanup before replacement. All logic is in commit_plan.
    """
    try:
        return await commit_plan(
            session,
            user_id=current_user.id,  # type: ignore[arg-type]
            plan_id=plan_id,
            garmin=garmin,
        )
    except ValueError as exc:
        msg = str(exc)
        if "does not belong to" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=404, detail=msg) from exc
```

- [ ] **Step 6: Run all three new integration tests — expect PASS**

```bash
docker compose exec backend pytest tests/integration/test_api_plans.py::TestCommit::test_commit_keeps_unchanged_sw_row_and_garmin_id tests/integration/test_api_plans.py::TestCommit::test_commit_skips_completed_sw_even_when_changed tests/integration/test_api_plans.py::TestCommit::test_commit_replaces_changed_workout -v
```

Expected: all 3 PASS.

- [ ] **Step 7: Run full backend test suite**

```bash
docker compose exec backend pytest -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/services/plan_import_service.py backend/src/api/routers/plans.py backend/tests/integration/test_api_plans.py
git commit -m "feat: commit_plan smart merge — keep unchanged + completed, bulk delete changed"
```

---

## Chunk 4: Frontend Types + DiffTable

### Task 8: Update TypeScript types

**Files:**
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: Extend `WorkoutDiff` and `DiffResult`**

In `frontend/src/api/types.ts`, replace the `WorkoutDiff` and `DiffResult` interfaces:

```typescript
export interface WorkoutDiff {
  date: string
  name: string
  old_name?: string
  old_steps_spec?: string
  new_steps_spec?: string
}

export interface DiffResult {
  added: WorkoutDiff[]
  removed: WorkoutDiff[]
  changed: WorkoutDiff[]
  unchanged: WorkoutDiff[]
  completed_locked: WorkoutDiff[]
}
```

- [ ] **Step 2: Fix existing `diffResult` fixture and inline DiffTable test objects**

After adding `unchanged` and `completed_locked` as required fields, two places in `frontend/src/tests/PlanCoach.test.tsx` will fail TypeScript:

**Fix 1 — the `diffResult` constant (around line 300):**

```typescript
const diffResult: DiffResult = {
  added: [{ date: '2026-04-21', name: 'New Long Run' }],
  removed: [{ date: '2026-04-14', name: 'Old Tempo' }],
  changed: [{ date: '2026-04-07', name: 'Easy Run' }],
  unchanged: [],
  completed_locked: [],
}
```

**Fix 2 — inline diff object in existing DiffTable test (around line 406, the `renders nothing when diff has no changes` test):**

```typescript
render(<DiffTable diff={{ added: [], removed: [], changed: [], unchanged: [], completed_locked: [] }} />)
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors (existing fixtures updated; new fields added).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/tests/PlanCoach.test.tsx
git commit -m "feat: extend WorkoutDiff + DiffResult types for smart merge"
```

---

### Task 9: Rewrite `DiffTable.tsx` with 5 row variants

**Files:**
- Modify: `frontend/src/components/plan-coach/DiffTable.tsx`
- Modify: `frontend/src/tests/PlanCoach.test.tsx`

- [ ] **Step 1: Write failing RTL tests**

Add this describe block inside `frontend/src/tests/PlanCoach.test.tsx`. Use dynamic imports (matching the existing `DiffTable` test pattern in the file — do NOT add a static import at the file top):

```typescript
describe('DiffTable smart merge rows', () => {
  const baseDiff = {
    added: [],
    removed: [],
    changed: [],
    unchanged: [],
    completed_locked: [],
  }

  it('returns null when only unchanged rows (no actionable changes)', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const diff = { ...baseDiff, unchanged: [{ date: '2026-06-01', name: 'Easy Run' }] }
    const { container } = render(<DiffTable diff={diff} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders completed_locked row with lock symbol when other changes exist', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const diff = {
      ...baseDiff,
      added: [{ date: '2026-06-02', name: 'Tempo' }],
      completed_locked: [{ date: '2026-06-01', name: 'Easy Run' }],
    }
    render(<DiffTable diff={diff} />)
    expect(screen.getByTestId('diff-table')).toBeInTheDocument()
    expect(screen.getByText('⊘')).toBeInTheDocument()
    expect(screen.getByText(/locked/i)).toBeInTheDocument()
  })

  it('renders changed row with before→after steps_spec', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const diff = {
      ...baseDiff,
      changed: [{
        date: '2026-06-01',
        name: 'Easy Run',
        old_name: 'Easy Run',
        old_steps_spec: '30m@Z2',
        new_steps_spec: '40m@Z2',
      }],
    }
    render(<DiffTable diff={diff} />)
    expect(screen.getByText('30m@Z2')).toBeInTheDocument()
    expect(screen.getByText('40m@Z2')).toBeInTheDocument()
  })

  it('header shows unchanged and locked counts when non-zero', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const diff = {
      ...baseDiff,
      added: [{ date: '2026-06-02', name: 'Tempo' }],
      unchanged: [{ date: '2026-06-03', name: 'Rest' }],
      completed_locked: [{ date: '2026-06-01', name: 'Easy Run' }],
    }
    render(<DiffTable diff={diff} />)
    expect(screen.getByText(/=1\s*unchanged/)).toBeInTheDocument()
    expect(screen.getByText(/⊘1\s*locked/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd frontend && npm test -- --run --reporter=verbose 2>&1 | grep -E "(PASS|FAIL|smart merge|completed_locked|unchanged)"
```

Expected: new tests FAIL — `unchanged` and `completed_locked` not yet rendered in `DiffTable`.

- [ ] **Step 3: Rewrite `DiffTable.tsx`**

Replace the entire content of `frontend/src/components/plan-coach/DiffTable.tsx`:

```tsx
import type { DiffResult, WorkoutDiff } from '../../api/types'

interface DiffTableProps {
  diff: DiffResult
}

type RowKind = 'added' | 'removed' | 'changed' | 'unchanged' | 'completed_locked'

const ROW_CONFIG: Record<RowKind, { symbol: string; color: string; bgVar: string }> = {
  added:            { symbol: '+',  color: 'var(--color-success)',  bgVar: 'var(--color-success-bg)' },
  removed:          { symbol: '−',  color: 'var(--color-error)',    bgVar: 'var(--color-error-bg)' },
  changed:          { symbol: '~',  color: 'var(--color-warning)',  bgVar: 'var(--color-warning-bg)' },
  unchanged:        { symbol: '=',  color: 'var(--text-muted)',     bgVar: 'transparent' },
  completed_locked: { symbol: '⊘',  color: 'var(--text-muted)',     bgVar: 'transparent' },
}

function DiffRow({ item, kind }: { item: WorkoutDiff; kind: RowKind }) {
  const c = ROW_CONFIG[kind]
  const isChanged = kind === 'changed' && (item.old_steps_spec || item.new_steps_spec)
  const isLocked = kind === 'completed_locked'
  const nameChanged = isChanged && item.old_name && item.old_name !== item.name

  return (
    <>
      <tr style={{ background: c.bgVar }}>
        <td style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '12px',
          fontWeight: 700,
          color: c.color,
          padding: '5px 10px 5px 12px',
          width: '28px',
        }}>
          {c.symbol}
        </td>
        <td style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '11px',
          color: 'var(--text-muted)',
          padding: '5px 10px',
          whiteSpace: 'nowrap',
        }}>
          {item.date}
        </td>
        <td style={{
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '12px',
          color: isLocked || kind === 'unchanged' ? 'var(--text-muted)' : 'var(--text-primary)',
          padding: '5px 10px 5px 0',
        }}>
          {nameChanged
            ? <>{item.old_name} <span style={{ color: 'var(--text-muted)' }}>→</span> {item.name}</>
            : item.name}
          {isLocked && (
            <span style={{ marginLeft: '6px', fontSize: '10px', color: 'var(--text-muted)' }}>
              locked
            </span>
          )}
        </td>
      </tr>
      {isChanged && (item.old_steps_spec || item.new_steps_spec) && (
        <tr style={{ background: c.bgVar }}>
          <td />
          <td />
          <td style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '10px',
            color: 'var(--text-muted)',
            padding: '0 10px 5px 0',
          }}>
            <span style={{ color: 'var(--color-error)', opacity: 0.7 }}>{item.old_steps_spec}</span>
            {' → '}
            <span style={{ color: 'var(--color-success)', opacity: 0.7 }}>{item.new_steps_spec}</span>
          </td>
        </tr>
      )}
    </>
  )
}

export function DiffTable({ diff }: DiffTableProps) {
  const totalAdded = diff.added.length
  const totalRemoved = diff.removed.length
  const totalChanged = diff.changed.length
  const totalUnchanged = (diff.unchanged ?? []).length
  const totalLocked = (diff.completed_locked ?? []).length
  const hasActionable = totalAdded + totalRemoved + totalChanged > 0

  if (!hasActionable) return null

  return (
    <div
      data-testid="diff-table"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '5px',
        overflow: 'hidden',
        marginBottom: '16px',
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '8px 12px',
        background: 'var(--bg-surface-2)',
        borderBottom: '1px solid var(--border)',
      }}>
        <span style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontWeight: 700,
          fontSize: '10px',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: 'var(--text-secondary)',
        }}>
          Changes vs current plan
        </span>
        <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto', flexWrap: 'wrap' }}>
          {totalAdded > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--color-success)' }}>
              +{totalAdded} added
            </span>
          )}
          {totalRemoved > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--color-error)' }}>
              −{totalRemoved} removed
            </span>
          )}
          {totalChanged > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--color-warning)' }}>
              ~{totalChanged} changed
            </span>
          )}
          {totalUnchanged > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--text-muted)' }}>
              ={totalUnchanged} unchanged
            </span>
          )}
          {totalLocked > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--text-muted)' }}>
              ⊘{totalLocked} locked
            </span>
          )}
        </div>
      </div>

      {/* Rows — actionable first, then informational */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <tbody>
          {diff.added.map((item, i) => (
            <DiffRow key={`added-${i}`} item={item} kind="added" />
          ))}
          {diff.removed.map((item, i) => (
            <DiffRow key={`removed-${i}`} item={item} kind="removed" />
          ))}
          {diff.changed.map((item, i) => (
            <DiffRow key={`changed-${i}`} item={item} kind="changed" />
          ))}
          {(diff.unchanged ?? []).map((item, i) => (
            <DiffRow key={`unchanged-${i}`} item={item} kind="unchanged" />
          ))}
          {(diff.completed_locked ?? []).map((item, i) => (
            <DiffRow key={`locked-${i}`} item={item} kind="completed_locked" />
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4: Run RTL tests — expect PASS**

```bash
cd frontend && npm test -- --run --reporter=verbose 2>&1 | grep -E "(PASS|FAIL|smart merge)"
```

Expected: all 4 new tests PASS. All existing DiffTable and PlanCoach tests PASS.

- [ ] **Step 5: Run full frontend test suite**

```bash
cd frontend && npm test -- --run
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/plan-coach/DiffTable.tsx frontend/src/tests/PlanCoach.test.tsx
git commit -m "feat: DiffTable — 5 row variants with before→after for changed workouts"
```

---

### Task 10: Mark Phase 5 complete in STATUS.md

**Files:**
- Modify: `STATUS.md`

- [ ] **Step 1: Update Phase 5 table and last-updated line**

In `STATUS.md`, update the Phase 5 block:

```markdown
### Plan Coach — Phase 5: Smart Plan Merge `feature/smart-plan-merge` ✅
| Task | Status |
|------|--------|
| Docs: PLAN.md, CLAUDE.md, STATUS.md, root CLAUDE.md | ✅ |
| Backend: enrich WorkoutDiff + DiffResult schema | ✅ |
| Backend: _compute_diff with completed_dates + 5 buckets | ✅ |
| Backend: validate_plan completed_dates query | ✅ |
| Backend: commit_plan smart merge (batch load, classify, bulk delete) | ✅ |
| Backend unit tests: _compute_diff (3 tests) | ✅ |
| Backend integration tests: commit_plan smart merge (3 tests) | ✅ |
| Frontend: WorkoutDiff + DiffResult types | ✅ |
| Frontend: DiffTable — 5 row variants + before→after changed | ✅ |
| Frontend: DiffTable RTL tests (4 tests) | ✅ |
```

Update the first line:
```
Last updated: 2026-03-20 (Smart Plan Merge — Phase 5 complete)
```

- [ ] **Step 2: Commit**

```bash
git add STATUS.md
git commit -m "docs: mark Phase 5 smart plan merge complete in STATUS.md"
```
