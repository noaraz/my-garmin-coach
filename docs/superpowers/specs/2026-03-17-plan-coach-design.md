# Plan Coach — Design Spec
_Date: 2026-03-17 · Updated: 2026-03-20_

## Context

GarminCoach currently lets athletes build individual workouts and schedule them manually. There is no way to create or import a multi-week training plan. This feature adds two plan-creation paths: a conversational AI coach (Gemini Flash) and a CSV import. Both paths produce the same output: WorkoutTemplates in the library and ScheduledWorkouts on the calendar, ready for zone resolution and Garmin sync.

Implementation plan: `docs/superpowers/plans/indexed-twirling-phoenix.md`

---

## Phases

| Phase | Scope | Branch |
|-------|-------|--------|
| 0 | Feature directory, PLAN.md, CLAUDE.md, STATUS.md update | `feature/plan-coach-scaffold` |
| 1 | Backend: step parser + validate/commit API (no UI) | `feature/plan-coach-phase-1` |
| 2 | Frontend: CSV Import page | `feature/plan-coach-phase-2` |
| 3 | Frontend: Active Plan View + Re-import Diff | `feature/plan-coach-phase-3` |
| 4 | Frontend + Backend: Chat (Gemini Flash) | `feature/plan-coach-phase-4` |

Each phase is a separate PR. New session recommended per phase (PLAN.md is the persistent context).

---

## Data Model

### New: `TrainingPlan`
```
id              int PK
user_id         FK → User
name            str
source          "csv" | "chat"
status          "draft" | "active" | "superseded"
parsed_workouts JSON   ← stored by /validate, consumed by /commit (see schema below)
start_date      date
created_at      datetime
updated_at      datetime
```

**One active plan per user**: only one `status=active` TrainingPlan is allowed per user at a time. `commit` handles replacement atomically: sets old active plan to `"superseded"`, deletes its ScheduledWorkouts, then activates the new one.

**`parsed_workouts` schema** — stored as a JSON array of `ParsedWorkout` objects:
```python
class ParsedWorkout(BaseModel):
    date: str              # ISO date "2025-03-01"
    name: str
    description: str = ""
    sport_type: str = "running"
    steps: list[dict]      # list of BuilderStep dicts (same format as WorkoutTemplate.steps)
```

Draft plans are excluded from all list queries. Stale draft cleanup: `POST /plans/validate` auto-deletes any `status=draft` rows for the user that are older than 24h before creating the new draft.

### Modified: `ScheduledWorkout`
- Add `training_plan_id` (nullable FK → TrainingPlan) — all existing rows default to NULL, no breakage.

### New (Phase 4): `PlanCoachMessage`
```
id          int PK
user_id     FK → User
role        "user" | "assistant"
content     text
created_at  datetime
```

Chat history is a **single global thread per user** — no plan_id FK. The thread persists across sessions; the user can always scroll back to find a prior plan and re-validate it.

---

## Step Text Format

The import format uses the same notation as `generateDescription()` (`frontend/src/utils/generateDescription.ts`) **for pace zones only**. The `@Z1(HR)` HR-zone suffix emitted by `generateDescription()` is not part of the import grammar — all import steps reference pace zones (Z1–Z5) only. This keeps the format simple for LLM/CSV authors.

```
10m@Z1, 45m@Z2, 5m@Z1          # time-based steps (m = minutes, s = seconds)
2K@Z1, 5K@Z3, 1K@Z1            # distance-based (K = km)
6x(400m@Z5 + 200m@Z1)          # repeat group
10m@Z1, 6x(400m@Z5 + 200m@Z1), 5m@Z1   # mixed
```

Units: `m` = minutes, `s` = seconds, `K` = km. Zones: `Z1`–`Z5` only. `sport_type` defaults to `"running"` if omitted.

Parser lives in `backend/src/services/plan_step_parser.py` — pure function, zero I/O, fully unit-testable.

---

## Phase 1 — Import Service (Backend Only)

### API

**`POST /api/v1/plans/validate`**
- Cleanup: delete all `status=draft` TrainingPlan rows for user older than 24h
- Body: `{ name, start_date, workouts: [{ date, name, description?, steps_spec, sport_type? }] }`
- Parses each `steps_spec` via `plan_step_parser` into `list[BuilderStep dicts]`
- **Any invalid**: returns 422 `{ plan_id: null, rows: [{ date, name, ok: false, error: "..." }] }` — no DB write
- **All valid + no active plan**: creates `TrainingPlan` (status=`draft`), returns `{ plan_id, rows, diff: null }`
- **All valid + active plan exists**: computes diff vs active plan, creates draft, returns `{ plan_id, rows, diff: DiffResult }`

**DiffResult schema:**
```python
class WorkoutDiff(BaseModel):
    date: str
    name: str

class DiffResult(BaseModel):
    added: list[WorkoutDiff]      # in new plan, not in active
    removed: list[WorkoutDiff]    # in active plan, not in new
    changed: list[WorkoutDiff]    # same date, different name or steps
```

**`POST /api/v1/plans/{plan_id}/commit`**
- Checks `training_plan.user_id == current_user.id` (403 otherwise)
- Reads draft (404 if not found or status != `draft`)
- If user has another active plan: bulk-delete its ScheduledWorkouts, set its status → `"superseded"`
- For each unique workout name: reuse existing `WorkoutTemplate` with same name+user (case-insensitive), or create new — templates land in shared library
- Creates `ScheduledWorkout` per date using `calendar_service.schedule()`, sets `training_plan_id`
- Sets `TrainingPlan.status` → `active`
- Returns `{ plan_id, name, workout_count, start_date }`

**`GET /api/v1/plans/active`**
- Returns the single active plan for current user, or 204 if none

**`DELETE /api/v1/plans/{plan_id}`**
- Checks `training_plan.user_id == current_user.id` (403 otherwise)
- Deletes ScheduledWorkouts with this `training_plan_id`
- Deletes the TrainingPlan record
- WorkoutTemplates remain in library (they may be reused across plans)

### Reused Internals
- `calendar_service.schedule()` + `resolve_builder_steps()` — `backend/src/services/calendar_service.py`
- `workout_template_repository`, `scheduled_workout_repository` — `backend/src/repositories/`
- `get_current_user` dependency — existing auth

### Tests (Phase 1)
- Unit: `plan_step_parser` — parametrized for all notation variants, invalid zones (Z6+), bad units, malformed repeats
- Integration: validate → commit happy path creates correct DB records; validate with any error returns 422 + no TrainingPlan created; commit on missing plan_id returns 404; commit on non-draft plan_id returns 404; delete removes ScheduledWorkouts but leaves WorkoutTemplates; delete with wrong user returns 403; commit replaces active plan atomically; stale draft cleanup triggered by validate

---

## Phase 2 — CSV Import UI

### Route
`/plan-coach` → "Import CSV" tab (default when no active plan)

### UX Flow (no active plan state)
1. **LLM Prompt Template** — shown expanded at top. "Copy" button auto-fills placeholders (`{lthr}`, `{threshold_pace}`, `{hr_zones}`, `{pace_zones}`) from the athlete's profile. Prompt is **model-agnostic** — user can paste into any LLM.
2. **CSV Format Reference** — example rows showing all columns.
3. **Upload zone** — drag-and-drop or browse. Client-side CSV parse on file select.
4. **Validation table** — calls `POST /plans/validate`. Per-row ✓ (green) / ✗ (red + error text). Shown immediately after upload.
5. **"Import to Calendar"** button — enabled only when all rows valid (`plan_id` returned by validate). Calls `POST /plans/{id}/commit`. On success: redirect to `/calendar` at `start_date`.

### CSV Columns
`date, name, description, steps_spec, sport_type`
`sport_type` is optional; defaults to `"running"`.

### Tests (Phase 2)
- RTL: CSV parse (valid + invalid files), validation table renders per-row errors, Import button disabled while errors exist, redirect on success
- API client: typed wrappers for `/plans/validate` and `/plans/{id}/commit` in `frontend/src/api/client.ts`

---

## Phase 3 — Active Plan View + Re-import Diff

### Active Plan State
When `GET /plans/active` returns a plan, the Plan Coach page shows the **Active Plan View** instead of CSV upload:

```
┌─────────────────────────────────────────────┐
│ Current Plan: "HM April 2026"               │
│ Started: 2026-03-20 · 48 workouts           │
│ (progress indicator — future, blocked)      │
│                                             │
│  [Upload New Plan]     [Delete Plan]        │
└─────────────────────────────────────────────┘
```

**Delete Plan** — confirmation modal ("This will remove all N scheduled workouts. This cannot be undone.") → `DELETE /plans/{plan_id}` → returns to CSV import view.

**Upload New Plan** — shows CSV upload below the plan card. On validate, if `diff` is non-null (active plan exists), renders **DiffTable** before the Import button:

```
Changes vs current plan:
  + 3 workouts added     (green rows)
  - 2 workouts removed   (red rows)
  ~ 4 workouts changed   (yellow rows)
```

Import button label changes to "Apply Changes to Calendar". Commit atomically supersedes the old plan.

### Re-import Diff Meaning
When the user uploads a new CSV (or gets a new plan from chat) while an active plan already exists, `validate` computes added/removed/changed workouts vs the active plan and returns them as `DiffResult`. The frontend shows the diff table before the user confirms. Commit atomically deletes the old plan's ScheduledWorkouts and creates the new ones.

### Plan Badge on Workout Cards
Workout cards in Calendar and Library show a subtle plan-name badge when `training_plan_id` is set. Badge is display-only.

### Tests (Phase 3)
- RTL: active plan card renders; delete modal; confirm delete → CSV import view shown; CSV upload with diff renders DiffTable; Apply Changes calls commit
- Integration: re-import atomically replaces active plan ScheduledWorkouts

---

## Phase 4 — Plan Coach Chat

### Route
`/plan-coach` → "Chat" tab (default tab; "Import CSV" is the secondary tab)

### System Prompt Context
Injected on every request. Built by pure function `build_system_prompt(profile, hr_zones, pace_zones, recent_activities)` in `backend/src/services/plan_coach_service.py`:
- Athlete LTHR, threshold pace
- HR zones (Z1–Z5 with bpm ranges)
- Pace zones (Z1–Z5 with pace ranges)
- Step format spec (same grammar as the CSV import format)
- **Recent training history**: last 4 weeks of `GarminActivity` records (date, type, duration, distance, avg pace) — queried by `user_id` + `date >= today - 28 days`. Empty list = section omitted, no error.
- Output instruction: when plan is ready, emit a fenced JSON block containing an array of objects with fields `{ date, name, description, steps_spec, sport_type }` — identical shape to the CSV row schema.

### Chat History Truncation
`send_chat_message` sends only the **last 40 messages** (20 user/assistant pairs) to Gemini. Full history is always stored in DB and visible in the UI. Truncation is silent — no user-visible indicator.

### AI Provider
Gemini Flash (free tier). `GEMINI_API_KEY` in `.env`. Backend proxies all chat requests — key never exposed to frontend.

### Chat API
**`GET /api/v1/plans/chat/history`** — returns `PlanCoachMessage[]` for current user (full thread)
**`POST /api/v1/plans/chat/message`** — body: `{ content: str }`. Appends user message, calls Gemini with truncated history + system prompt, appends assistant response, returns assistant message.

### Plan Detection + Import Flow
1. Frontend detects a fenced JSON block in assistant message (regex on ` ```json ` ... ` ``` `)
2. Shows **"Preview & Validate →"** button inline below the message
3. Button calls `POST /plans/validate` with parsed JSON
4. Inline validation table + DiffTable (if active plan exists) render below the message
5. **"Import to Calendar"** / **"Apply Changes"** → `POST /plans/{id}/commit` → redirect to calendar
6. **"Back to chat"** dismisses the validation panel; user continues conversation to refine

### Tests (Phase 4)
- Unit: `build_system_prompt` with mock profile/zones/activities — activities section present/absent correctly; truncation sends only last 40 messages; detection regex matches/misses
- Integration: `POST /chat/message` appends both messages, returns assistant content; Gemini client mocked; recent activities queried from DB
- Frontend RTL: plan detection shows Validate button, validation panel + DiffTable render, same validate/commit flow as Phase 3

---

## Future Work
- **Plan progress view**: adherence % and current phase/week indicator. Blocked by Garmin activity fetch returning enough historical data for meaningful analysis.

---

## File Structure (created in Phase 0)

```
features/plan-coach/
  PLAN.md          ← phase-by-phase task breakdown (phases 1–4)
  CLAUDE.md        ← step format spec, API reference, component patterns
```
