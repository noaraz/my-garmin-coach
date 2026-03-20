# Calendar — PLAN

## Description

Frontend training calendar with week and month views. Shows scheduled workouts
as colored cards, supports drag-to-reschedule, click-to-schedule from library,
and sync status indicators. Also includes the Zone Manager page for setting
thresholds and viewing/editing zones.

This is the first frontend feature — includes React scaffolding and shared
layout (AppShell, Sidebar, API client).

Track progress in **STATUS.md**.

---

## Tasks

### Frontend Scaffolding (first time)
- [x] Scaffold React + Vite + TypeScript + Tailwind
- [x] Write `frontend/Dockerfile.dev`
- [x] Add frontend service to `docker-compose.yml`
- [x] Verify: `docker compose up` runs both backend + frontend
- [x] Write `src/api/types.ts` — TypeScript interfaces matching backend models
- [x] Write `src/api/client.ts` — typed fetch wrappers for all API endpoints
- [x] Implement `layout/AppShell.tsx` + `layout/Sidebar.tsx`

### Zone Manager
- [x] Write all tests in `ZoneManager.test.tsx` (see test table)
- [x] Run tests → RED
- [x] Implement `ZoneManager.tsx`, `HRZoneTable.tsx`, `PaceZoneTable.tsx`
- [x] Implement `ThresholdInput.tsx`, `MethodSelector.tsx`
- [x] Run tests → GREEN

### Calendar View
- [x] Write all tests in `Calendar.test.tsx` (see test table)
- [x] Run tests → RED
- [x] Implement `CalendarView.tsx`, `WeekView.tsx`, `MonthView.tsx`
- [x] Implement `DayCell.tsx`, `WorkoutCard.tsx`, `WorkoutPicker.tsx`
- [x] Run tests → GREEN

### Post-Ship Polish (2026-03-09)
- [x] `WorkoutPicker` — convert Tailwind classes to CSS vars (respects dark/light theme)
- [x] `DayCell` — expand click area to entire day column (not just "+ Add workout" button)
- [x] `CalendarView` — add `activationConstraint: { distance: 8 }` to PointerSensor for reliable drag
- [x] `WorkoutCard` — make remove button visible (grey, red on hover); replace hardcoded colors with CSS vars
- [x] `WorkoutCard` — show `template.description` one-liner below name (stacked per comma-segment)
- [x] `WorkoutCard` — clock-format duration + distance summary (uses `workoutStats.ts` shared utils with steps fallback)
- [x] Color token audit — 40+ hardcoded hex values replaced with CSS vars across all calendar components
- [x] Dark theme lightened for readability; `--accent`, `--accent-subtle`, `--text-on-accent`, `--zone-default` tokens added
- [x] Remove drag-and-drop from calendar (scheduling via picker only; drag-to-reschedule removed for UX simplicity)
- [x] Vite proxy fallback — `vite.config.ts` target uses `process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'` so dev outside Docker works without `ENOTFOUND backend`
- [x] `workoutStats.ts` + 41 new edge-case tests — `computeDurationFromSteps`, `computeDistanceFromSteps`, `formatClock`, `formatKm`; `Calendar.test.tsx` updated with steps-fallback + no-data tests

### API Client Tests
- [x] Write all tests in `client.test.ts` (see test table)
- [x] Run tests → RED
- [x] Implement API client functions
- [x] Run tests → GREEN

### Workout Detail Panel (2026-03-20)
- [ ] Backend: extend PATCH /calendar/{id} to accept optional `notes` field
- [ ] Backend: tests for notes update
- [ ] Frontend: `formatPace` utility (already exists in formatting.ts)
- [ ] Frontend: `WorkoutDetailPanel.tsx` — panel shell (overlay, slide, close)
- [ ] Frontend: `WorkoutDetailPlanned.tsx` — planned workout content
- [ ] Frontend: `WorkoutDetailCompleted.tsx` — completed workout content
- [ ] Frontend: `WorkoutDetailUnplanned.tsx` — unplanned activity content
- [ ] Frontend: Update `WorkoutCard` — replace navigate with `onCardClick` callback
- [ ] Frontend: Update `UnplannedActivityCard` — add `onCardClick` callback
- [ ] Frontend: Thread `onCardClick` through CalendarView, WeekView, MonthView, DayCell
- [ ] Frontend: `CalendarPage` — panel state management + render panel
- [ ] Frontend: `useCalendar` hook — add `updateNotes` method
- [ ] Frontend: API client — add `updateWorkoutNotes` function
- [ ] Frontend: Tests for WorkoutDetailPanel

---

## Tests

### ZoneManager.test.tsx

| Test | Scenario |
|------|----------|
| `test_renders_5_hr_zone_rows` | zones loaded → 5 rows |
| `test_renders_5_pace_zone_rows` | zones loaded → 5 rows |
| `test_lthr_input_shows_current` | profile loaded → LTHR shown |
| `test_change_lthr_and_save` | type new LTHR, save → PUT called |
| `test_recalculate_button` | click → POST recalculate |
| `test_zone_boundaries_editable` | click zone → inline edit |
| `test_method_dropdown` | click → coggan/friel/daniels/custom |
| `test_success_feedback` | save succeeds → toast |
| `test_error_on_failure` | save fails → error message |

### Calendar.test.tsx

| Test | Scenario |
|------|----------|
| `test_week_view_7_days` | render → 7 columns |
| `test_month_view_correct_days` | March 2026 → 31 days |
| `test_workouts_on_dates` | 3 workouts → 3 cards |
| `test_card_name_duration` | card → name + clock duration ("45:00") |
| `test_card_sync_status` | synced → green icon |
| `test_click_day_opens_picker` | click empty day → modal |
| `test_toggle_week_month` | toggle → view switches |
| `test_navigate_prev_next` | arrows → dates shift |
| `test_sync_all_button` | click → POST called |
| `test_card_duration_from_steps_fallback` | null estimated + steps JSON → clock from steps |
| `test_card_no_summary_when_no_data` | null duration + null steps → no clock text |

### client.test.ts

| Test | Scenario |
|------|----------|
| `test_fetchProfile` | mock GET → profile object |
| `test_fetchHRZones` | mock GET → 5 zones |
| `test_fetchCalendarRange` | mock GET → workout list |
| `test_scheduleWorkout` | POST with date+template_id |
| `test_rescheduleWorkout` | PATCH with new date |
| `test_triggerSync` | POST sync |
| `test_handles_network_error` | mock failure → error |

---

## Design

Use the **`frontend-design`** skill (`.claude/skills/frontend-design/`) when implementing React components. Invoke via the Skill tool to get distinctive, production-grade UI that avoids generic AI aesthetics.

Design spec (from CLAUDE.md):
- Tone: Athletic, utilitarian, clean — Strava meets Notion
- Colors: Dark sidebar (`bg-gray-900`), light main (`bg-gray-50`). Zone colors: blue (z1) → red (z5)
- Typography: Clean sans-serif, monospace for pace/time values
- Cards: Colored blocks with zone distribution, name, duration, sync icon

## Implementation Files

```
frontend/src/
  api/ — client.ts, types.ts
  components/zones/ — ZoneManager, HRZoneTable, PaceZoneTable, ThresholdInput, MethodSelector
  components/calendar/ — CalendarView, WeekView, MonthView, DayCell, WorkoutCard, WorkoutPicker, WorkoutDetailPanel, WorkoutDetailPlanned, WorkoutDetailCompleted, WorkoutDetailUnplanned
  components/layout/ — AppShell, Sidebar
  pages/ — CalendarPage, ZonesPage, SettingsPage
  hooks/ — useProfile, useZones, useCalendar
  utils/ — workoutStats.ts (computeDurationFromSteps, computeDistanceFromSteps, formatClock, formatKm)
```
