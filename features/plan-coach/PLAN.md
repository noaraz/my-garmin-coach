# Plan Coach — Feature Plan

Design spec: `docs/superpowers/specs/2026-03-17-plan-coach-design.md`
Implementation plan: `docs/superpowers/plans/indexed-twirling-phoenix.md`

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
