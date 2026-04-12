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

### Re-import Diff — Smart Merge (Phase 5 + Phase 8)

`DiffResult` now has 6 buckets. `WorkoutDiff` carries optional before/after fields:

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
    past_locked: list[WorkoutDiff]      # date < today, absent from new plan — re-associated, never deleted
```

**Priority rule**: `completed_locked` takes precedence over `past_locked`. A workout that is both past-dated and has a matched activity is classified as `completed_locked`.

`_compute_diff` signature (third arg defaults to `None`, resolved to `set()` inside):

```python
def _compute_diff(
    incoming: list[ParsedWorkout],
    active_parsed: list[dict],
    completed_dates: set[str] | None = None,
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
- **Bulk re-associate kept SWs**: after bulk delete, run `session.execute(update(ScheduledWorkout).where(ScheduledWorkout.id.in_(kept_sw_ids)).values(training_plan_id=plan_id))`. Without this, unchanged/completed_locked rows still reference the superseded plan and `workout_count` queries on the new plan return a lower count than actual.
- Single commit after all mutations

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

### Chat Transaction Pattern
`send_chat_message` must: load existing history → call Gemini → persist user + assistant in one commit. **Never commit the user message before calling Gemini** — a Gemini failure leaves an orphaned user row that corrupts the alternating user/model turn history on the next send.

### Gemini Safety Blocks
`response.text` raises `ValueError` (not `ClientError`) when Gemini's safety filter blocks a response. `gemini_client.py` must catch both.

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
    PlanCoachPage.tsx           # route /plan-coach — no tabs, CSV-only flow
  components/plan-coach/
    CsvImportTab.tsx            # prompt builder + upload + validate + commit
    ValidationTable.tsx         # per-row ✓/✗ table (reused in Phase 3)
    PlanPromptBuilder.tsx       # form-driven prompt generator (Phase 4b, replaces LlmPromptTemplate)
    LlmPromptTemplate.tsx       # legacy static prompt — no longer used (kept for reference)
    ActivePlanCard.tsx          # shows active plan name/count/actions (Phase 3)
    DiffTable.tsx               # added/removed/changed rows (Phase 3)
    DeletePlanModal.tsx         # confirmation modal (Phase 3)
    ChatTab.tsx                 # Gemini chat — hidden, backend still present
```

### PlanPromptBuilder (Phase 4b)
Form inputs → generated prompt that the user copies to Claude/ChatGPT/Gemini:
- **Goal distance**: select (5K / 10K / Half Marathon / Marathon / 50K Ultra)
- **Race date**: date picker → auto-computes weeks until race
- **Preferred training days**: Mon–Sun toggle buttons (multi-select); count shown as Nx/week
- **Long run day**: select filtered to chosen training days (falls back to all days if none selected)
- Generated prompt updates live; "Copy" button → clipboard (with `execCommand` fallback)
- Prompt ends with: `"Output the full CSV only — no explanation, no markdown fences."`
- `LlmPromptTemplate.tsx` is superseded — do not re-use it in new code

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

---

## PlanPromptBuilder — Updated Patterns (added 2026-03-22)

### State
- `activities: GarminActivity[]` — renamed from `recentActivities`; initialises to `[]` (no auto-fetch)
- `healthNotes: string` — free text; empty string = omit from prompt
- `fetchState: 'idle' | 'fetching' | 'done' | 'empty'` — drives fetch button label/feedback

### Fetch button state machine
`idle → fetching → done | empty | error`. Re-clicking "Refresh"/"Retry" always goes through `fetching` first.
`activities` is never cleared on re-fetch or error — old activities stay in the prompt until new ones load successfully.

State semantics:
- `done` — fetch succeeded, one or more activities returned
- `empty` — fetch succeeded with zero results (genuine "no runs in last 14 days")
- `error` — fetch threw (network failure, 401, etc.); badge shows "Fetch failed — previous activities still included" when stale data exists, "Fetch failed" otherwise
- **Do not collapse `error` into `empty`** — the user cannot tell whether they have no runs or whether Garmin is disconnected

### Date window
`start.setDate(start.getDate() - 13)` → exactly 14 days inclusive (today + 13 prior days). Backend range is inclusive on both ends.

### Label casing convention
All field labels use lowercase source strings (e.g. `"Current health & shape"`) and rely on `fieldLabel` style's `textTransform: 'uppercase'` for display. Do NOT write uppercase in the literal — it breaks the pattern when `textTransform` is later modified.

### Prompt order (health notes + activity section)
After long run day line: `My current health & shape: [notes]` (only when non-empty)
Then: `## Recent Training (last 14 days)` (only when `activities.length > 0`)

### Why `useEffect` was removed
Silent auto-fetch hid what context was being injected. The explicit button lets the user see which
activities are included before copying the prompt.
