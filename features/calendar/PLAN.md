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
- [ ] Scaffold React + Vite + TypeScript + Tailwind
- [ ] Write `frontend/Dockerfile.dev`
- [ ] Add frontend service to `docker-compose.yml`
- [ ] Verify: `docker compose up` runs both backend + frontend
- [ ] Write `src/api/types.ts` — TypeScript interfaces matching backend models
- [ ] Write `src/api/client.ts` — typed fetch wrappers for all API endpoints
- [ ] Implement `layout/AppShell.tsx` + `layout/Sidebar.tsx`

### Zone Manager
- [ ] Write all tests in `ZoneManager.test.tsx` (see test table)
- [ ] Run tests → RED
- [ ] Implement `ZoneManager.tsx`, `HRZoneTable.tsx`, `PaceZoneTable.tsx`
- [ ] Implement `ThresholdInput.tsx`, `MethodSelector.tsx`
- [ ] Run tests → GREEN

### Calendar View
- [ ] Write all tests in `Calendar.test.tsx` (see test table)
- [ ] Run tests → RED
- [ ] Implement `CalendarView.tsx`, `WeekView.tsx`, `MonthView.tsx`
- [ ] Implement `DayCell.tsx`, `WorkoutCard.tsx`, `WorkoutPicker.tsx`
- [ ] Run tests → GREEN

### API Client Tests
- [ ] Write all tests in `client.test.ts` (see test table)
- [ ] Run tests → RED
- [ ] Implement API client functions
- [ ] Run tests → GREEN

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
| `test_card_name_duration` | card → name, "45 min" |
| `test_card_sync_status` | synced → green icon |
| `test_click_day_opens_picker` | click empty day → modal |
| `test_drag_reschedules` | drag to new day → API call |
| `test_toggle_week_month` | toggle → view switches |
| `test_navigate_prev_next` | arrows → dates shift |
| `test_sync_all_button` | click → POST called |

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

## Implementation Files

```
frontend/src/
  api/ — client.ts, types.ts
  components/zones/ — ZoneManager, HRZoneTable, PaceZoneTable, ThresholdInput, MethodSelector
  components/calendar/ — CalendarView, WeekView, MonthView, DayCell, WorkoutCard, WorkoutPicker
  components/layout/ — AppShell, Sidebar
  pages/ — CalendarPage, ZonesPage, SettingsPage
  hooks/ — useProfile, useZones, useCalendar
  utils/ — formatting.ts (pace "4:30", duration "1h 15m")
```
