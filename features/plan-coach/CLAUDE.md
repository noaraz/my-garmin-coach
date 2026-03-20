# Plan Coach — Feature Reference

Design spec: `docs/superpowers/specs/2026-03-17-plan-coach-design.md`
Implementation plan: `docs/superpowers/plans/indexed-twirling-phoenix.md`
Feature plan: `features/plan-coach/PLAN.md`

---

## Step Text Format (Import Grammar)

The same notation as `generateDescription()` in `frontend/src/utils/generateDescription.ts`, but **pace zones only** (no `@Z1(HR)` suffix).

```
10m@Z1, 45m@Z2, 5m@Z1          # time-based (m = minutes, s = seconds)
2K@Z1, 5K@Z3, 1K@Z1            # distance-based (K = km)
6x(400m@Z5 + 200m@Z1)          # repeat group
10m@Z1, 6x(400m@Z5 + 200m@Z1), 5m@Z1   # mixed
```

Units: `m` = minutes, `s` = seconds, `K` = km. Zones: `Z1`–`Z5` only.
Parser: `backend/src/services/plan_step_parser.py` — pure function, raises `StepParseError` on invalid input.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/plans/validate` | Parse + validate workouts; cleanup stale drafts; compute diff vs active plan; store draft. Returns `{ plan_id, rows, diff }` |
| POST | `/api/v1/plans/{id}/commit` | Supersede active plan + create WorkoutTemplates + ScheduledWorkouts |
| GET | `/api/v1/plans/active` | Current active plan or 204 |
| DELETE | `/api/v1/plans/{id}` | Delete plan + its ScheduledWorkouts; templates stay in library |
| GET | `/api/v1/plans/chat/history` | Full PlanCoachMessage thread for user |
| POST | `/api/v1/plans/chat/message` | Send message, get Gemini response |

Router: `backend/src/api/routers/plans.py`
Service: `backend/src/services/plan_import_service.py`
Chat service: `backend/src/services/plan_coach_service.py`

---

## Data Model

### TrainingPlan
```
status: "draft" | "active" | "superseded"
```
- Only one `active` plan per user at a time
- `validate` deletes stale `draft` rows (>24h) before creating a new one
- `commit` sets old active → `superseded`, bulk-deletes its ScheduledWorkouts
- `parsed_workouts`: JSON array of `ParsedWorkout` — stored at validate time, consumed at commit time

### ScheduledWorkout
- `training_plan_id`: nullable FK → TrainingPlan; NULL for manually scheduled workouts
- Existing column: `matched_activity_id` (FK → GarminActivity) — unrelated, already present

### PlanCoachMessage (Phase 4)
- Single global thread per user — no plan_id FK
- Full history stored in DB; only last 40 messages sent to Gemini

---

## Key Patterns

### Validate → Commit (staged import)
```
POST /validate → creates draft, returns plan_id + diff
POST /{id}/commit → reads draft, creates WorkoutTemplates + ScheduledWorkouts, sets active
```
No re-parsing at commit time — `parsed_workouts` JSON is the source of truth.

### Re-import Diff
`validate` compares incoming workouts against the active plan's `parsed_workouts`:
- `added`: date in new plan, not in active
- `removed`: date in active plan, not in new
- `changed`: same date, different name or steps

Frontend renders `DiffTable` when `diff != null`. "Apply Changes" calls commit.

### One-Plan Constraint + Atomic Replace
```python
# in commit_plan():
if active := await get_active_plan(session, user_id):
    await session.execute(
        delete(ScheduledWorkout).where(ScheduledWorkout.training_plan_id == active.id)
    )
    active.status = "superseded"
    session.add(active)
# then create new ScheduledWorkouts and set new plan active
await session.commit()
```

### Chat System Prompt
`build_system_prompt(profile, hr_zones, pace_zones, recent_activities)` — pure function.
- Injects zones + step format spec + last 4 weeks of GarminActivity (date, type, duration, distance, avg pace)
- `recent_activities=[]` → section omitted silently
- Output instruction: emit fenced ` ```json ` block with array of `{ date, name, description, steps_spec, sport_type }`

### Plan Detection (Frontend)
```typescript
const planJsonRegex = /```json\n([\s\S]+?)\n```/;
```
Detected in assistant messages → shows "Preview & Validate →" button → same validate/commit flow as CSV tab.

### Plan Badge on Workout Cards
`WorkoutCard.tsx` and `TemplateCard.tsx` show a subtle badge when `training_plan_id != null`.
Read plan name from `GET /plans/active` — cache at page/context level, not per-card.

---

## datetime Convention

All new models must use:
```python
created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
```
**Not** `datetime.utcnow` — ruff DTZ rules enforce this.

---

## Frontend Component Structure

```
frontend/src/
  pages/
    PlanCoachPage.tsx           # route /plan-coach, tab switcher
  components/plan-coach/
    CsvImportTab.tsx            # LLM prompt + upload + validate + commit (Phase 2)
    ValidationTable.tsx         # per-row ✓/✗ table (Phase 2, reused in 3 + 4)
    LlmPromptTemplate.tsx       # prompt with filled placeholders (Phase 2)
    ActivePlanCard.tsx          # shows active plan name/count/actions (Phase 3)
    DiffTable.tsx               # added/removed/changed rows (Phase 3)
    DeletePlanModal.tsx         # confirmation modal (Phase 3)
    ChatTab.tsx                 # Gemini chat thread + plan detection (Phase 4)
```

---

## Active Plan State Patterns (added 2026-03-20)

- `PlanCoachPage` fetches active plan on mount with `getActivePlan()` — sets `activePlan` state
- No active plan → only show `CsvImportTab`
- Active plan → show `ActivePlanCard` at top; `showUpload` toggle reveals `CsvImportTab` below
- `onImported` callback prop on `CsvImportTab` — when provided, called on successful commit instead of navigating to `/calendar`; used by `PlanCoachPage` to re-fetch active plan after replace
- `DeletePlanModal` takes `plan: ActivePlan` prop — shows plan name + workout count in warning body
- `DiffTable` renders nothing (returns `null`) when all three arrays are empty — safe to always render when `result.diff != null`
- Plan badge threading: `activePlanName` flows CalendarPage → CalendarView → WeekView/MonthView → DayCell → WorkoutCard as `planName` prop. Badge only renders when `!compact` (hidden in month view compact cards). TemplateCard accepts `planName?` prop but caller decides when to pass it.
- `training_plan_id: number | null` added to `ScheduledWorkout` frontend type (`api/types.ts`)

## Copy Button Gotchas (added 2026-03-20)
- `navigator.clipboard.writeText` throws "Document is not focused" in Chrome — always add `execCommand('copy')` fallback using a `ref` on the `<code>` element
- Use `'idle' | 'copied' | 'error'` state (not boolean) to drive both label and color
- FastAPI 422 `body.detail` can be string, `{msg}[]`, or object — branch on type in `client.ts` or object detail coerces to `"[object Object]"` and breaks regex error recovery

---

## Test Coverage Targets

| Module | Target |
|--------|--------|
| `plan_step_parser.py` | 95%+ (pure logic) |
| `plan_import_service.py` | 80%+ |
| `plan_coach_service.py` | 80%+ |
| Frontend components | RTL per-component |
