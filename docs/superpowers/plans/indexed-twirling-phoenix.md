# Plan Coach — Implementation Plan

## Context

The spec at `docs/superpowers/specs/2026-03-17-plan-coach-design.md` was written and reviewed.
This plan applies spec updates then implements all phases.

Spec: `docs/superpowers/specs/2026-03-17-plan-coach-design.md`

### State of main as of 2026-03-20 (post PR #31 merge)

- **GarminActivity model** exists in `backend/src/db/models.py` ✓
- **ScheduledWorkout** has `matched_activity_id` but NO `training_plan_id` yet — we add it in Phase 1
- **Workout Detail Panel** is fully complete (STATUS.md all ✅) but root `PLAN.md` still shows Feature 10 as ⬜ — fix in Phase 0
- **`calendar_service.schedule()`** still exists at line 123 ✓
- **datetime convention**: all new models must use `lambda: datetime.now(timezone.utc).replace(tzinfo=None)` (matching `GarminActivity` pattern, ruff DTZ rules enforced)
- **Current branch**: `fix/google-token-audience-validation` with one uncommitted change in `auth/service.py` — unrelated to this feature. Branch from `main` for scaffold work.

---

## Step 0 — Update Spec First

Apply these changes to the spec file before any code:

1. **Draft cleanup → Phase 1**: `POST /plans/validate` deletes all `status=draft` TrainingPlan rows older than 24h for the current user before creating the new draft. Remove from Future Work.

2. **One active plan per user**: only one `status=active` TrainingPlan allowed per user. `commit` handles replacement (deactivates old plan, removes its ScheduledWorkouts, activates new one).

3. **Re-import diff → part of this feature** (not Future Work): when user already has an active plan, `validate` returns a diff. Phase 3 (Active Plan View) surfaces this as a diff table before the user confirms re-import.

4. **Re-import diff meaning**: "When user uploads a new CSV or gets a new plan from chat while an active plan already exists, `validate` computes added/removed/changed workouts vs the active plan and returns them. Frontend shows the diff table before commit. Commit atomically deletes old plan's ScheduledWorkouts and creates the new ones."

5. **Plan progress view → Future Work, blocked**: "Blocked by Garmin activity fetch. Cannot show adherence % without completed activities."

6. **Garmin history in chat → Phase 4** (was Future Work): `GarminActivity` records now exist from PR #31. `build_system_prompt` queries last 4 weeks and includes them. Remove from Future Work.

7. **Chat history truncation → Phase 4** (was Future Work): cap Gemini context to last 40 messages (20 pairs). Remove from Future Work.

8. **Phase 0 → add root CLAUDE.md update**: run `/claude-md-management:revise-claude-md`.

---

## Phase 0 — Scaffold  `feature/plan-coach-scaffold`

1. Update spec doc (changes above)
2. Create `features/plan-coach/PLAN.md` — opens with link to spec + link to this implementation plan; then phase-by-phase task breakdown
3. Create `features/plan-coach/CLAUDE.md` — step format spec, API reference, component patterns, link to spec
4. Update `STATUS.md`:
   - Change "Current Focus" to Plan Coach
   - Add `Design spec: docs/superpowers/specs/2026-03-17-plan-coach-design.md`
   - Add `Implementation plan: docs/superpowers/plans/indexed-twirling-phoenix.md`
   - Add per-phase task table
5. Run `/claude-md-management:revise-claude-md` — adds plan-coach to features table in root `CLAUDE.md`
6. Update root `PLAN.md`:
   - Mark Feature 10 (Workout Detail Panel) ✅
   - Add Plan Coach as Feature 11 ⬜ with path `features/plan-coach/` and note "depends on: calendar, garmin-activity-fetch"
   - Add `Design spec: docs/superpowers/specs/2026-03-17-plan-coach-design.md` reference in the Feature 11 row or as a note below the table
7. Commit + PR

> Branch from `main` (not from `fix/google-token-audience-validation`).

---

## Phase 1 — Backend  `feature/plan-coach-phase-1`

> Agent note: invoke `fastapi-templates` skill before writing new router/services — use its async patterns and dependency injection conventions.

### New models — `backend/src/db/models.py`

```python
class TrainingPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    name: str
    source: str                  # "csv" | "chat"
    status: str = "draft"        # "draft" | "active"
    parsed_workouts: Optional[str] = Field(default=None)  # JSON array of ParsedWorkout
    start_date: date
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
```

Add to `ScheduledWorkout`:
```python
training_plan_id: Optional[int] = Field(default=None, foreign_key="trainingplan.id")
```

`PlanCoachMessage` added in Phase 5 only.

### Alembic migration
Creates `trainingplan` table + adds `training_plan_id` to `scheduledworkout`. Use `render_as_batch=True`.

### New service — `backend/src/services/plan_step_parser.py`
Pure function, zero I/O, 95%+ unit test coverage.

```python
def parse_steps_spec(spec: str) -> list[dict]:
    """Parse "10m@Z1, 6x(400m@Z5 + 200m@Z1), 5m@Z1" → BuilderStep dicts."""
```
Units: `m` = minutes, `s` = seconds, `K` = km. Zones: `Z1`–`Z5` only.
Raises `StepParseError` with row-level detail on invalid input.

### New service — `backend/src/services/plan_import_service.py`

```python
async def validate_plan(session, user_id, body) -> ValidateResult
# - cleanup stale drafts (>24h old) for user
# - parse all steps_spec
# - if any parse error: return 422, no DB write
# - if user has active plan: compute diff vs active plan → include in response
# - create TrainingPlan(status="draft"), store parsed_workouts
# - return { plan_id, rows, diff: DiffResult | None }

async def commit_plan(session, user_id, plan_id) -> CommitResult
# - 404 if not found or not draft
# - 403 if wrong user
# - if user has active plan: delete its ScheduledWorkouts, set its status="superseded"
# - for each unique workout name: reuse matching WorkoutTemplate or create new
# - create ScheduledWorkout per date, set training_plan_id
# - set TrainingPlan.status = "active"
# - return { plan_id, name, workout_count, start_date }

async def delete_plan(session, user_id, plan_id) -> None
# - 403 if wrong user
# - delete ScheduledWorkouts with this training_plan_id
# - delete TrainingPlan; WorkoutTemplates are NOT deleted (shared library)

async def get_active_plan(session, user_id) -> TrainingPlan | None

async def _cleanup_stale_drafts(session, user_id) -> None
```

**DiffResult schema:**
```python
class WorkoutDiff(BaseModel):
    date: str
    name: str

class DiffResult(BaseModel):
    added: list[WorkoutDiff]
    removed: list[WorkoutDiff]
    changed: list[WorkoutDiff]   # same date, different name or steps
```

Reuses: `calendar_service.schedule()`, `workout_service.create_template()`, repos in `backend/src/repositories/`.

### New router — `backend/src/api/routers/plans.py`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/plans/validate` | cleanup → parse → diff vs active → store draft |
| POST | `/api/v1/plans/{plan_id}/commit` | replace active plan + create ScheduledWorkouts |
| GET | `/api/v1/plans/active` | returns active plan or 204 |
| DELETE | `/api/v1/plans/{plan_id}` | deletes ScheduledWorkouts + plan; templates stay |

Register in `backend/src/api/app.py`.

### Tests (Phase 1)

**Unit** — `tests/unit/test_plan_step_parser.py`:
Valid variants, invalid zones (Z6+), unknown units, malformed parens, whitespace.

**Integration** — `tests/integration/test_api_plans.py`:
- Validate happy path (no existing plan) → draft created, diff=null
- Validate happy path (active plan exists) → diff populated correctly
- Validate with bad step → 422, no DB write
- Commit (fresh) → active plan + correct ScheduledWorkout count
- Commit (replaces active) → old ScheduledWorkouts gone, new ones created
- Commit non-existent → 404; commit already-active → 404; wrong user → 403
- Delete → ScheduledWorkouts gone, WorkoutTemplates remain; wrong user → 403
- Stale draft cleanup: second validate call removes draft older than 24h

---

## Phase 2 — CSV Import UI  `feature/plan-coach-phase-2`

### Route
`/plan-coach` → `PlanCoachPage.tsx` — two tabs: "Plan" (default) | "Chat" (disabled, coming soon)

### State: no active plan
Shows CSV Import flow:
1. **LLM Prompt Template** (expanded) — Copy button fills `{lthr}`, `{threshold_pace}`, `{hr_zones}`, `{pace_zones}` from athlete profile
2. **CSV Format Reference** — static example rows (`date, name, description, steps_spec, sport_type`)
3. **Upload zone** — drag-and-drop or browse; client-side CSV parse on file select (`FileReader` + manual split)
4. **ValidationTable** — calls `POST /plans/validate`; per-row ✓ (green) / ✗ (red + error); no diff section yet (diff is Phase 3)
5. **"Import to Calendar"** button — enabled only when all rows valid; calls `POST /plans/{id}/commit`; on success: redirect to `/calendar`

### New files
- `frontend/src/pages/PlanCoachPage.tsx`
- `frontend/src/components/plan-coach/CsvImportTab.tsx`
- `frontend/src/components/plan-coach/ValidationTable.tsx` — reused in Phase 3 + Phase 5
- `frontend/src/components/plan-coach/LlmPromptTemplate.tsx`
- `frontend/src/api/client.ts` — add `validatePlan()`, `commitPlan()`, `getActivePlan()`, `deletePlan()`
- `frontend/src/api/types.ts` — add plan types including `DiffResult`

### Sidebar nav
Add "Plan Coach" nav item (e.g., `MapIcon`) — after Workout Builder, before Settings.

### Tests (Phase 2)
RTL: CSV parse (valid/invalid), ValidationTable per-row errors, Import button state, redirect on success, prompt placeholders filled from mocked profile.

---

## Phase 3 — Active Plan View + Re-import Diff  `feature/plan-coach-phase-3`

### State: active plan exists
When `GET /plans/active` returns a plan, `PlanCoachPage` shows the **Active Plan View** instead of CSV upload:

```
┌─────────────────────────────────────────────┐
│ Current Plan: "HM April 2026"               │
│ Started: 2026-03-20 · 48 workouts           │
│ (progress indicator — future)               │
│                                             │
│  [Upload New Plan]     [Delete Plan]        │
└─────────────────────────────────────────────┘
```

**Delete Plan** — shows confirmation modal ("This will remove all 48 scheduled workouts. This cannot be undone.") → `DELETE /plans/{plan_id}` → returns to CSV import view.

**Upload New Plan** — shows CSV upload flow below the plan card. On validate, if `diff` is non-null, renders **DiffTable** before the Import button:

```
Changes vs current plan:
  + 3 workouts added     (green rows)
  - 2 workouts removed   (red rows)
  ~ 4 workouts changed   (yellow rows)
```

Import button label changes to "Apply Changes to Calendar". Commit atomically replaces the active plan.

### New components
- `frontend/src/components/plan-coach/ActivePlanCard.tsx`
- `frontend/src/components/plan-coach/DiffTable.tsx`
- `frontend/src/components/plan-coach/DeletePlanModal.tsx`

### Plan badge on workout cards
`WorkoutCard.tsx` + `TemplateCard.tsx` — show subtle plan-name badge when `training_plan_id` is set.
Read plan name from `GET /plans/active` (cached in a simple React context or component-level state).

### Tests (Phase 3)
- RTL: active plan card renders name + count; delete modal shown on click; confirm delete calls API + shows import view; upload with diff renders DiffTable; Apply Changes calls commit
- Integration: re-import replaces active plan ScheduledWorkouts correctly (end-to-end)

---

## Phase 4 — Chat (Gemini Flash)  `feature/plan-coach-phase-4`

### New backend files
- `backend/src/services/gemini_client.py` — thin wrapper over `google-generativeai`; `GEMINI_API_KEY` from env
- `backend/src/services/plan_coach_service.py`
  - `build_system_prompt(profile, hr_zones, pace_zones, recent_activities) -> str` — pure function; injects zones + step format spec + last 4 weeks of `GarminActivity` records (date, type, duration, distance, avg pace). Queries `GarminActivity` by `user_id` + `date >= today - 28 days`. No history = empty list, no error.
  - `send_chat_message(session, user_id, content) -> str` — appends user message, calls Gemini with **truncated** history (last 40 messages — 20 user/assistant pairs) + system prompt, appends assistant response. Truncation is silent; full history is always stored in DB.

New model (add to `backend/src/db/models.py`):
```python
class PlanCoachMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    role: str           # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
```

Add alembic migration for `plancoachMessage` table.

Add to plans router:
- `GET /api/v1/plans/chat/history`
- `POST /api/v1/plans/chat/message`

### New frontend component
`frontend/src/components/plan-coach/ChatTab.tsx` — now enabled (replaces "coming soon"):
- Message thread (user/assistant bubbles)
- Input + send
- Plan detection: regex ```` /```json\n([\s\S]+?)\n```/ ```` on assistant messages
- "Preview & Validate →" inline button → calls `POST /plans/validate` → renders `ValidationTable` + `DiffTable` (if active plan exists)
- "Import to Calendar" / "Apply Changes" → `POST /plans/{id}/commit` → redirect

Reuses `ValidationTable`, `DiffTable`, `DeletePlanModal` from Phase 3.

### Tests (Phase 4)
- Unit: `build_system_prompt` with mock profile/zones/activities — activities section present when records exist, omitted when empty list; truncation: only last 40 messages sent to Gemini; detection regex matches/misses
- Integration: `POST /chat/message` saves both rows, returns assistant content; Gemini mocked; recent activities queried from DB
- RTL: JSON detected → Validate button → ValidationTable + DiffTable → Import redirects

---

## Verification

After each phase:
```bash
# Backend
docker compose exec backend pytest tests/unit/ -v
docker compose exec backend pytest tests/integration/ -v
docker compose exec backend pytest -v --cov=src --cov-report=term-missing

# Frontend
npm --prefix frontend test -- --run

# Manual smoke
# Phase 2: upload CSV → see validation → import → check calendar has workouts
# Phase 3: import again → see diff → apply → check old workouts gone, new ones present
# Phase 4: chat → get JSON block → validate → import
```

---

## Critical Files

| File | Change |
|------|--------|
| `backend/src/db/models.py` | Add `TrainingPlan`, `PlanCoachMessage`; add `training_plan_id` to `ScheduledWorkout` |
| `backend/src/api/app.py` | Register plans router |
| `backend/src/api/routers/plans.py` | New |
| `backend/src/services/plan_step_parser.py` | New (pure) |
| `backend/src/services/plan_import_service.py` | New |
| `backend/src/services/plan_coach_service.py` | New (Phase 4) |
| `backend/src/services/gemini_client.py` | New (Phase 4) |
| `backend/alembic/versions/` | New migration per phase |
| `frontend/src/pages/PlanCoachPage.tsx` | New |
| `frontend/src/components/plan-coach/` | New directory: CsvImportTab, ValidationTable, LlmPromptTemplate, ActivePlanCard, DiffTable, DeletePlanModal, ChatTab |
| `frontend/src/api/client.ts` | Add plan API functions |
| `frontend/src/api/types.ts` | Add plan types incl. DiffResult |
| `frontend/src/components/WorkoutCard.tsx` | Add plan badge |
| `frontend/src/components/TemplateCard.tsx` | Add plan badge |
| `frontend/src/App.tsx` | Add `/plan-coach` route |
| `docs/superpowers/specs/2026-03-17-plan-coach-design.md` | Spec updates |
| `CLAUDE.md` | Add plan-coach to features table (via revise-claude-md) |
| `STATUS.md` | Add plan-coach phases |
