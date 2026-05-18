# Plan Coach — Feature Plan

Design spec: `docs/superpowers/specs/2026-03-17-plan-coach-design.md`
Step format grammar: `features/plan-coach/CLAUDE.md` → **Step Text Format (Import Grammar)**
Implementation plan: `docs/superpowers/plans/indexed-twirling-phoenix.md`

Strength extension: `docs/superpowers/plans/2026-05-18-strength-workouts.md`

---

## Overview

Two ways to create a multi-week training plan:
1. **CSV Import** — upload a CSV (from any LLM or by hand), validate per-row, import to calendar
2. **Plan Coach Chat** — conversational AI (Gemini Flash) with athlete's zones + recent history; outputs structured JSON that feeds the same validate/commit pipeline

Both paths produce WorkoutTemplates in the library and ScheduledWorkouts on the calendar.
One active plan per user at a time. Re-import shows a diff before replacing.

---

## Phase 0 — Scaffold ✅ (this PR)

- [x] Update design spec with final decisions
- [x] Create this PLAN.md + CLAUDE.md
- [x] Update STATUS.md
- [x] Update root CLAUDE.md (revise-claude-md)
- [x] Update root PLAN.md

---

## Phase 1 — Backend `feature/plan-coach-phase-1`

### New models (`backend/src/db/models.py`)
- `TrainingPlan` — id, user_id, name, source, status (draft/active/superseded), parsed_workouts (JSON), start_date
- `ScheduledWorkout` — add nullable `training_plan_id` FK
- `PlanCoachMessage` — added in Phase 4

### Alembic migration
`alembic revision --autogenerate -m "add_training_plan"` — creates `trainingplan` table, adds `training_plan_id` to `scheduledworkout`.

### New services
- `backend/src/services/plan_step_parser.py` — pure parser, zero I/O, 95%+ unit coverage
- `backend/src/services/plan_import_service.py` — validate, commit, delete, get_active, cleanup_stale_drafts

### New router
`backend/src/api/routers/plans.py` — registered in `backend/src/api/app.py`

| Method | Path | Action |
|--------|------|--------|
| POST | `/api/v1/plans/validate` | cleanup drafts → parse → diff vs active → store draft |
| POST | `/api/v1/plans/{id}/commit` | supersede active → create templates + scheduled workouts |
| GET | `/api/v1/plans/active` | current active plan or 204 |
| DELETE | `/api/v1/plans/{id}` | delete plan + its scheduled workouts; templates stay |

### Tests
- `tests/unit/test_plan_step_parser.py` — all notation variants + error cases
- `tests/integration/test_api_plans.py` — validate, commit, replace, delete, auth checks

---

## Phase 2 — CSV Import UI `feature/plan-coach-phase-2`

### Route: `/plan-coach`
Two tabs: **Plan** (default) | **Chat** (disabled — Phase 4)

### New frontend files
- `frontend/src/pages/PlanCoachPage.tsx`
- `frontend/src/components/plan-coach/CsvImportTab.tsx`
- `frontend/src/components/plan-coach/ValidationTable.tsx` — reused in Phase 3 + 4
- `frontend/src/components/plan-coach/LlmPromptTemplate.tsx`
- API types + client functions for validate, commit, getActivePlan, deletePlan

### UX (no active plan)
LLM prompt template → CSV format reference → file upload → ValidationTable → Import button

### Sidebar
Add "Plan Coach" nav item after Workout Builder, before Settings.

### Tests
RTL: CSV parse, ValidationTable, Import button state, redirect on success.

---

## Phase 3 — Active Plan View + Re-import Diff `feature/plan-coach-phase-3` ✅

### Active plan state
- [x] `ActivePlanCard.tsx` — name, start date, workout count, Upload New Plan + Delete Plan buttons
- [x] `DeletePlanModal.tsx` — confirmation before destructive delete (count in body)
- [x] `DiffTable.tsx` — added/removed/changed rows from `validate` response
- [x] `CsvImportTab.tsx` — shows DiffTable when `result.diff != null`; button label "Apply Changes" vs "Import"
- [x] `PlanCoachPage.tsx` — fetches active plan on mount; shows ActivePlanCard; toggles CSV upload view; delete flow
- [x] `training_plan_id` added to `ScheduledWorkout` frontend type
- [x] Plan badge on `WorkoutCard.tsx` + `TemplateCard.tsx` when `training_plan_id` is set
- [x] `CalendarPage.tsx` fetches active plan name; threads through CalendarView → WeekView/MonthView → DayCell → WorkoutCard

### Tests
- [x] RTL: active plan card, delete modal, diff table on re-upload, Apply Changes calls commit
- [x] 29 total PlanCoach.test.tsx tests (17 new in Phase 3)

---

## Phase 4 — Chat (Gemini Flash) `feature/plan-coach-phase-4`

### New backend
- `backend/src/services/gemini_client.py` — `google-generativeai` wrapper; `GEMINI_API_KEY` from env
- `backend/src/services/plan_coach_service.py`
  - `build_system_prompt(profile, hr_zones, pace_zones, recent_activities)` — pure; injects zones + last 4 weeks of `GarminActivity` + step format spec
  - `send_chat_message(session, user_id, content)` — saves messages, sends last 40 to Gemini

### New model: `PlanCoachMessage`
Alembic migration: `add_plan_coach_message`.

### New API endpoints
- `GET /api/v1/plans/chat/history`
- `POST /api/v1/plans/chat/message`

### New frontend
- `frontend/src/components/plan-coach/ChatTab.tsx` — thread, input, plan detection regex, inline validate/diff/commit flow

### Tests
Unit: system prompt with/without activities, truncation, detection regex.
Integration: chat message round-trip with mocked Gemini.
RTL: JSON detection → Validate → DiffTable → Import.

---

## Phase 5 — Smart Plan Merge `feature/smart-plan-merge`

### Backend
- `_compute_diff` — new `completed_dates: set[str]` param; 5 output buckets
- `validate_plan` — one extra query for completed dates
- `commit_plan` — smart merge: batch-load SWs + templates, classify, bulk delete, batch add
- [x] Deduplicate templates by (name + steps JSON) on plan commit —
      same name + same steps → single shared template;
      same name + different steps → separate templates

### Frontend
- `WorkoutDiff` type — add `old_name?`, `old_steps_spec?`, `new_steps_spec?`
- `DiffResult` type — add `unchanged[]`, `completed_locked[]`
- `DiffTable.tsx` — 5 row variants + before→after for changed

### Tests
- Backend unit: `test_compute_diff_*` (3 new)
- Backend integration: `test_commit_plan_*` (3 new)
- Frontend: `DiffTable` (4 new RTL tests)

---

## Phase 6 — Prompt Improvements `feature/plan-coach-prompt-improvements`

Design spec: `docs/superpowers/specs/2026-03-21-plan-coach-prompt-improvements-design.md`
Implementation plan: `docs/superpowers/plans/2026-03-21-plan-coach-prompt-improvements.md`

### Changes
- [x] `buildPrompt()` — rolling 2–3 week horizon, health notes param, re-run note, 14-day activity label
- [x] Remove `useEffect` auto-fetch; add `handleFetchActivities` with `fetchState` state machine
- [x] Add health textarea (after long run day select)
- [x] Add fetch button + inline feedback badge (above generated prompt)
- [x] Remove old "Recent training included in prompt" summary block
- [x] Code review fixes: `'error'` state in catch (not `'empty'`), date window -13 for exact 14 days inclusive, label literal lowercased (CSS textTransform handles casing)

---

## Phase 8 — Preserve Past Workouts on Plan Update

Design spec: `docs/superpowers/specs/2026-04-12-plan-update-preserve-past-workouts-design.md`

### Problem
Re-importing a shorter/revised plan deletes all past workouts absent from the new CSV — wiping training history. The diff screen incorrectly showed them as red "−" removals.

### Backend (`plan_import_service.py`)
- [x] Add `past_locked: list[WorkoutDiff] = []` to `DiffResult`
- [x] `_compute_diff()`: workouts in active plan, absent from new plan, with `date < today` → `past_locked` (not `removed`). `completed_locked` takes priority.
- [x] `commit_plan()`: workouts with `date < today` in the "Removed" loop → `kept_sw_ids` (re-associated, never deleted)

### Frontend
- [x] `types.ts`: add `past_locked?: WorkoutDiff[]` to `DiffResult`
- [x] `DiffTable.tsx`: new `past_locked` row kind with `↩` symbol, `(kept)` label, muted color; summary shows `↩N past (kept)`; table renders when only past_locked rows exist
- [x] `DiffTable.test.tsx`: new test file covering past_locked rendering, summary counts, render gate

### Tests
- [x] Backend: 5 new unit tests in `test_plan_import_service.py`
- [x] Frontend: `DiffTable.test.tsx`

### Bugfix (2026-04-23): rescheduled workout still removed on plan import
- [x] `_compute_diff()` + `commit_plan()`: `< today` → `<= today` — workouts moved to today are past_locked
- [x] `CalendarService.reschedule()`: update `TrainingPlan.parsed_workouts` when workout date changes
- [x] Tests: `test_today_workout_not_in_new_plan_is_past_locked`, `test_reschedule_updates_plan_parsed_workouts`, `test_reschedule_no_plan_does_not_raise`

---

## Phase 7 — Validation Template Status Column

### Backend
- [x] `ValidateRow.template_status: Literal["new", "existing"] = "new"`
- [x] `validate_plan()`: single WorkoutTemplate query, per-valid-row annotation
- [x] Integration test: `test_validate_template_status_new_and_existing`

### Frontend
- [x] `ValidateRow` type: optional `template_status?: 'new' | 'existing'`
- [x] `ValidationTable`: Library column + NEW badge / in library cell
- [x] 3 RTL tests in `describe('ValidationTable', ...)`
