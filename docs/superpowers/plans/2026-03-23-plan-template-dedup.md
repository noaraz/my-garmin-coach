# Plan Template Dedup — Name + Steps Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When committing a plan, deduplicate workout templates by **(name + steps JSON)** instead of name alone, so two workouts with the same name but identical steps share one library entry, while same-name-different-steps workouts each get their own template.

**Architecture:** Single-file backend change in `commit_plan()` — swap the dict key from `t.name` to `(t.name, t.steps or "")`. The in-loop insertion uses the matching key so within-import dedup stays intact. No schema change, no API change, no frontend change.

**Tech Stack:** Python 3.11, SQLModel, pytest, SQLite in-memory for integration tests.

---

## Chunk 1: Docs + Tests + Implementation

### Task 0: Update Docs

**Files:**
- Modify: `features/plan-coach/PLAN.md`
- Modify: `STATUS.md`

- [ ] **Step 1: Update `features/plan-coach/PLAN.md`**

Add a bullet under the "Template library" section (or equivalent):

```
- [x] Deduplicate templates by (name + steps JSON) on plan commit —
      same name + same steps → single shared template;
      same name + different steps → separate templates
```

- [ ] **Step 2: Note in `STATUS.md`**

Under the Plan Coach feature row, add:
```
Template dedup fix: name+steps key (was name-only)
```

- [ ] **Step 3: Commit docs**

```bash
git add features/plan-coach/PLAN.md STATUS.md
git commit -m "docs: note template dedup fix in plan-coach plan + status"
```

---

### Task 1: Write Two Failing Tests

**Files:**
- Modify: `backend/tests/integration/test_api_plans.py`

Insert both tests into the existing `TestCommit` class (starts at line ~225), after the last `test_commit_*` test.

**Note on auth:** The conftest globally overrides `get_current_user` to return `User(id=1, ...)`. No `Authorization` header is needed in any request; assertions hardcode `user_id == 1`.

- [ ] **Step 1: Write the first test — same name + same steps → single template (regression guard)**

This test verifies the happy-path dedup still works after the key change. It is expected to pass even before the fix (name-only dedup handles this case), so it serves as a regression guard, not a RED test.

```python
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
```

- [ ] **Step 2: Write the second test — same name + different steps → two templates (the real RED test)**

This test is expected to FAIL before the fix (name-only dedup incorrectly reuses the first template for the second workout).

```python
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
                    "steps_spec": "5m@Z1, 50m@Z2",   # different steps
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
```

- [ ] **Step 3: Run both new tests — expect Test 1 GREEN (regression guard), Test 2 RED**

```bash
cd backend
.venv/bin/pytest tests/integration/test_api_plans.py \
  -k "test_commit_same_name" -v
```

Expected output:
```
PASSED test_commit_same_name_same_steps_deduplicates_template
FAILED test_commit_same_name_different_steps_creates_separate_templates
```

If both pass, the bug was already fixed. If both fail, check conftest auth setup.

---

### Task 2: Implement the Fix

**Files:**
- Modify: `backend/src/services/plan_import_service.py`

Find the `# Batch-load/create templates` section (~line 425). Make these two changes:

**Change 1 — dict build (loading existing templates from DB):**

```python
# BEFORE
existing_templates = {t.name: t for t in templates_result.all()}

# AFTER
# Key: (name, steps_json) — json.dumps is called with default settings,
# matching how t.steps was originally stored (same call, same library).
# sort_keys=False is fine because Python dicts preserve insertion order
# and the parser always produces the same key order.
existing_templates: dict[tuple[str, str], WorkoutTemplate] = {
    (t.name, t.steps or ""): t for t in templates_result.all()
}
```

**Change 2 — lookup + insert inside the `for pw_dict in sws_to_create:` loop:**

```python
# BEFORE
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

# AFTER
steps_json = json.dumps(pw.steps) if pw.steps else None
dedup_key = (pw.name, steps_json or "")
if dedup_key in existing_templates:
    template = existing_templates[dedup_key]
else:
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
    existing_templates[dedup_key] = template
```

- [ ] **Step 4: Run the two new tests — both should now be GREEN**

```bash
cd backend
.venv/bin/pytest tests/integration/test_api_plans.py \
  -k "test_commit_same_name" -v
```

Expected: PASS PASS.

- [ ] **Step 5: Run the full plans test suite — no regressions**

```bash
cd backend
.venv/bin/pytest tests/integration/test_api_plans.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Lint**

```bash
cd backend
.venv/bin/ruff check src/services/plan_import_service.py \
                      tests/integration/test_api_plans.py
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add backend/src/services/plan_import_service.py \
        backend/tests/integration/test_api_plans.py
git commit -m "fix: dedup workout templates by name+steps on plan commit

Previously, same-name templates were reused regardless of steps content.
Now the dedup key is (name, steps_json), so:
- Same name + same steps → share one template in the library
- Same name + different steps → create separate templates"
```

---

## Verification

1. Import `garmin_coach_plan.csv` (14 runs) via Plan Coach → Commit
2. Open the Workout Library — expect **8 unique templates** (not 14):
   - Easy - A+100 ×1
   - Easy - A+101 ×1 (appears twice in the plan with identical steps)
   - Progressive Run +110 ×1
   - Easy - A+108 ×1 (appears twice)
   - Easy - A+110 ×1 (appears twice)
   - Friel Pace Test ×1
   - Easy - A+115 ×1 (appears three times)
   - Easy - A+125 ×1 (appears twice)
