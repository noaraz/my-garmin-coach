# Validation View — Template Library Status

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a "Library" column in the plan validation table so users can see, per row, whether the workout would create a NEW template or reuse an existing one.

**Architecture:** Purely additive. `ValidateRow` gets a new `template_status` field (default `"new"`). `validate_plan()` runs one extra DB query to load the user's existing templates, then annotates each valid row using the same `(name, _normalize_steps(steps))` dedup key already used at commit time. The frontend renders a small "NEW" badge or muted "in library" indicator in a new Library column.

**Tech Stack:** Python 3.11 / FastAPI / SQLModel (backend) · React 18 / TypeScript / Vitest / RTL (frontend)

---

## Files

| File | Change |
|------|--------|
| `backend/src/services/plan_import_service.py` | Add `template_status` to `ValidateRow`; annotate rows in `validate_plan()` |
| `backend/tests/integration/test_api_plans.py` | New test in `TestValidate` |
| `frontend/src/api/types.ts` | Add optional `template_status` to `ValidateRow` |
| `frontend/src/components/plan-coach/ValidationTable.tsx` | Add Library column header + cell |
| `frontend/src/tests/PlanCoach.test.tsx` | 3 new tests in `describe('ValidationTable', ...)` |

---

## Chunk 1: Docs + Backend

### Task 0: Update Docs

**Files:** `features/plan-coach/PLAN.md`, `STATUS.md`

- [ ] **Step 1: Add Phase 7 section to `features/plan-coach/PLAN.md`**

Add after the last existing phase:

```markdown
## Phase 7 — Validation Template Status Column

- [ ] `ValidateRow.template_status: Literal["new", "existing"] = "new"`
- [ ] `validate_plan()`: single WorkoutTemplate query, per-valid-row annotation
- [ ] Integration test: `test_validate_template_status_new_and_existing`
- [ ] `ValidateRow` frontend type: optional `template_status?: 'new' | 'existing'`
- [ ] `ValidationTable`: Library column + NEW badge / in library cell
- [ ] 3 RTL tests in `describe('ValidationTable', ...)`
```

- [ ] **Step 2: Add note to `STATUS.md`**

Under Plan Coach, add:
```
Phase 7: validation view shows NEW / in-library status per row (in progress)
```

- [ ] **Step 3: Commit**

```bash
git add features/plan-coach/PLAN.md STATUS.md
git commit -m "docs: add Phase 7 validation template status to plan-coach plan"
```

---

### Task 1: Backend — Extend ValidateRow and validate_plan

**Files:**
- Modify: `backend/src/services/plan_import_service.py`
- Test: `backend/tests/integration/test_api_plans.py`

#### Step 1: Write the failing test

Add to the `TestValidate` class in `backend/tests/integration/test_api_plans.py`, after the last existing test in that class:

```python
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
```

- [ ] **Step 2: Run the test — confirm RED**

```bash
cd backend
.venv/bin/pytest tests/integration/test_api_plans.py::TestValidate::test_validate_template_status_new_and_existing -v
```

Expected: FAIL with `KeyError: 'template_status'` or similar.

- [ ] **Step 3: Implement — extend `ValidateRow` and `validate_plan()`**

In `backend/src/services/plan_import_service.py`:

**3a. Add `Literal` to the typing import at the top:**
```python
from typing import Any, Literal
```

**3b. Add `template_status` field to `ValidateRow`:**
```python
class ValidateRow(BaseModel):
    row: int
    date: str
    name: str
    steps_spec: str
    sport_type: str
    valid: bool
    error: str | None = None
    template_status: Literal["new", "existing"] = "new"
```

**3c. In `validate_plan()`, add a template annotation pass after the parsing loop.**

Find the section that builds `parsed_list` and `rows`. The function has an early return when `not all_valid` — **place this block after that guard**, just before the draft plan is created. That guarantees `len(valid_rows) == len(parsed_list)` so the `zip` is safe:

```python
# Annotate valid rows with template_status (new vs existing in library).
# Must be placed after the `if not all_valid: ...` early-return guard —
# only runs when every row is valid, so zip(valid_rows, parsed_list) is aligned.
if parsed_list:
    tmpl_result = await session.exec(
        select(WorkoutTemplate).where(WorkoutTemplate.user_id == user_id)
    )
    existing_keys: set[tuple[str, str]] = {
        (t.name, _normalize_steps(t.steps)) for t in tmpl_result.all()
    }
    valid_rows = [r for r in rows if r.valid]
    for vrow, pw in zip(valid_rows, parsed_list):   # parsed_list is list[ParsedWorkout]
        steps_json = json.dumps(pw.steps, sort_keys=True) if pw.steps else None
        incoming_key = (pw.name, steps_json or "")  # matches commit_plan key exactly
        if incoming_key in existing_keys:
            vrow.template_status = "existing"
```

Make sure `WorkoutTemplate` is imported at the top of the file (it should already be — check existing imports).

- [ ] **Step 4: Run the test — confirm GREEN**

```bash
cd backend
.venv/bin/pytest tests/integration/test_api_plans.py::TestValidate::test_validate_template_status_new_and_existing -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite — no regressions**

```bash
cd backend
.venv/bin/pytest tests/integration/test_api_plans.py -v
```

Expected: all 36 tests pass.

- [ ] **Step 6: Lint**

```bash
cd backend
.venv/bin/ruff check src/services/plan_import_service.py
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add backend/src/services/plan_import_service.py \
        backend/tests/integration/test_api_plans.py
git commit -m "feat: annotate ValidateRow with template_status (new / existing)

validate_plan() runs one extra query to load the user's WorkoutTemplate
records, then marks each valid row 'existing' if the same (name, steps)
key is already in the library, or 'new' otherwise. Uses the same
_normalize_steps dedup key as commit_plan()."
```

---

## Chunk 2: Frontend

### Task 2: Frontend Types

**Files:**
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: Add `template_status` to `ValidateRow` interface**

Find `export interface ValidateRow` in `frontend/src/api/types.ts` and add the optional field:

```typescript
export interface ValidateRow {
  row: number
  date: string
  name: string
  steps_spec: string
  sport_type: string
  valid: boolean
  error: string | null
  template_status?: 'new' | 'existing'   // ← add this line
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/types.ts
git commit -m "feat(types): add optional template_status to ValidateRow"
```

---

### Task 3: Frontend UI — Library Column

**Files:**
- Modify: `frontend/src/components/plan-coach/ValidationTable.tsx`
- Modify: `frontend/src/tests/PlanCoach.test.tsx`

#### Step 1: Write three failing tests

Add inside the existing `describe('ValidationTable', () => { ... })` block in `frontend/src/tests/PlanCoach.test.tsx`:

```typescript
it('shows NEW badge when template_status is "new"', async () => {
  await renderValidationTable([validRow({ template_status: 'new' })])
  expect(screen.getByText('NEW')).toBeInTheDocument()
})

it('shows "in library" when template_status is "existing"', async () => {
  await renderValidationTable([validRow({ template_status: 'existing' })])
  expect(screen.getByText('in library')).toBeInTheDocument()
})

it('shows no library indicator when template_status is absent', async () => {
  await renderValidationTable([validRow()])   // no template_status
  expect(screen.queryByText('NEW')).not.toBeInTheDocument()
  expect(screen.queryByText('in library')).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests — confirm RED**

```bash
cd frontend
npm test -- --run src/tests/PlanCoach.test.tsx
```

Expected: 3 new tests FAIL (Library column doesn't exist yet).

- [ ] **Step 3: Implement the Library column in `ValidationTable.tsx`**

In `frontend/src/components/plan-coach/ValidationTable.tsx`:

**3a. Add a Library column header** (after the Steps `<th>`, before the OK `<th>`):

```tsx
<th style={{ ...th, width: 72, textAlign: 'center' }}>Library</th>
```

**3b. Add a Library `<td>` cell** per row (after the steps cell, before the OK cell):

```tsx
<td style={{ ...td, textAlign: 'center' }}>
  {row.template_status === 'new' && (
    <span style={{
      fontSize: '10px',
      fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
      fontWeight: 600,
      padding: '2px 6px',
      borderRadius: '3px',
      background: 'var(--accent)',
      color: 'var(--text-on-accent)',
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
    }}>NEW</span>
  )}
  {row.template_status === 'existing' && (
    <span style={{
      fontSize: '11px',
      color: 'var(--text-muted)',
      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
    }}>in library</span>
  )}
</td>
```

- [ ] **Step 4: Run tests — confirm GREEN**

```bash
cd frontend
npm test -- --run src/tests/PlanCoach.test.tsx
```

Expected: all tests pass including the 3 new ones.

- [ ] **Step 5: Run full frontend suite**

```bash
npm test -- --run
```

Expected: no regressions.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/plan-coach/ValidationTable.tsx \
        frontend/src/tests/PlanCoach.test.tsx
git commit -m "feat: show NEW badge / in-library in ValidationTable Library column

Adds a Library column to the plan validation table. Rows with
template_status='new' show an accent-colored NEW badge; rows with
template_status='existing' show a muted 'in library' label. Rows with
no template_status (old API) render an empty cell for backward compat.
Three RTL tests cover both states and the absent-field path."
```

---

## Verification

1. In the app, go to Plan Coach → CSV Import
2. Upload `garmin_coach_plan.csv` (the 14-run plan) and click Validate
3. On **first import** (no existing templates): all 14 rows show **NEW** badge
4. Click Commit, then re-upload the same CSV and Validate again
5. On **re-import**: rows with previously committed workouts (e.g. "Easy - A+115") show **in library**; genuinely new workouts show **NEW**
