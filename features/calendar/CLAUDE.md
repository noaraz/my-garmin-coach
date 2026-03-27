# Calendar — CLAUDE

## UI Design

- **Tone**: Athletic, utilitarian, clean — Strava meets Notion
- **Colors**: Dark sidebar, light main. Zone colors: blue (z1) → red (z5)
- **Typography**: Clean sans-serif. Monospace for pace/time values.
- **Cards**: Colored blocks showing zone distribution, name, duration, sync icon.

## Frontend Scaffold (First Time Only)

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install tailwindcss @tailwindcss/vite
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

Also add `Dockerfile.dev` and update `docker-compose.yml` to include frontend service.

## Card Click → Detail Panel (updated 2026-03-20)

`WorkoutCard` fires `onCardClick(workout)` callback instead of navigating to builder.
`UnplannedActivityCard` fires `onCardClick(activity)` callback.
`CalendarPage` holds panel state and renders `WorkoutDetailPanel` overlay.

Previously: `WorkoutCard` navigated to `/builder?id={workout_template_id}`. Now: "Edit in Builder" action is available inside the panel.

## Testing: `useNavigate` Requires a Router

`CalendarPage` uses `useNavigate()` for the "Edit in Builder" action. Tests must wrap in `MemoryRouter`:

```typescript
import { MemoryRouter } from 'react-router-dom'

const renderPage = (props: { initialDate?: Date } = {}) =>
  render(<MemoryRouter><CalendarPage {...props} /></MemoryRouter>)
```

Apply this wrapper whenever any child component uses `useNavigate`, `useParams`, `useLocation`, etc.

## WorkoutCard Description Display (updated 2026-03-23)

- Description always shows — guards `!compact` and `!workout.activity` removed
- Compact mode (month view): 9px font, 1.3 line-height; full mode: 10px, 1.4
- Each comma-segment on its own line with `whiteSpace: nowrap` + `textOverflow: ellipsis`
- **`MobileCalendarDayView` DRIFT RISK**: This component renders its own card markup inline and does NOT use `WorkoutCard`. Any description display change in `WorkoutCard` must also be applied manually to `MobileCalendarDayView.tsx`. Both files have a cross-reference comment to flag this.
- Month view: `minHeight: 90px` removed from day cells — cells expand to content height; outer container already has `overflow: auto`

## Workout Detail Panel (2026-03-20)

Design spec: `docs/superpowers/specs/2026-03-20-workout-detail-panel-design.md`

- **Panel replaces card navigation**: `WorkoutCard` no longer calls `navigate()`. Instead fires `onCardClick(workout)` prop. `UnplannedActivityCard` similarly fires `onCardClick(activity)`.
- **Callback threading**: `CalendarPage` → `CalendarView` → `WeekView`/`MonthView` → `DayCell` → cards. All pass `onWorkoutClick` and `onActivityClick` callbacks.
- **Panel state in CalendarPage**: `selectedWorkout: ScheduledWorkoutWithActivity | null` + `selectedActivity: GarminActivity | null`. Panel open when either is non-null.
- **Notes**: `ScheduledWorkout.notes` column already exists in DB model + schema. PATCH endpoint extended to accept `{ date?, notes? }`.
- **Escape/backdrop close**: `useEffect` with `keydown` listener for Escape. Backdrop `onClick` for outside clicks.

## Workout Removal Confirmation (added 2026-03-26)

- **RemoveWorkoutModal** (`frontend/src/components/calendar/RemoveWorkoutModal.tsx`): styled confirmation dialog following `DeletePlanModal` pattern. Props: `workoutName`, `workoutDate`, `isSyncedToGarmin`, `onConfirm`, `onCancel`, `isRemoving`.
- **State in CalendarPage**: `pendingRemoveWorkout: ScheduledWorkoutWithActivity | null` + `isRemoving: boolean`. All `onRemove` callbacks set `pendingRemoveWorkout` instead of calling `remove()` directly. Modal renders when non-null.
- **3 trigger points** (all go through the same modal):
  1. `WorkoutCard` X button (desktop) — `CalendarPage:363`
  2. `MobileCalendarDayView` remove button — `CalendarPage:351`
  3. `WorkoutDetailPanel` "Remove" button — `CalendarPage:401`
- **Garmin warning**: Modal conditionally shows "will also be removed from Garmin" when `garmin_workout_id` is set on the workout.
- **Panel auto-close**: `handleConfirmRemove` closes `WorkoutDetailPanel` if the removed workout is currently selected.

## Today Button (added 2026-03-27)

- **Placement**: Before the `‹` prev arrow — Google Calendar convention: `[Today] ‹ date ›`
- **Handler**: `handleToday()` — sets `currentDate` to `new Date()`, resets `selectedDay` on mobile
- **Disabled state**: `isCurrentPeriod` derived boolean — compares week start (week view) or month/year (month view) to today. Button gets `opacity: 0.4` and `disabled` when already showing current period.
- **Style**: Same height (27px) and border as arrow buttons. `IBM Plex Sans Condensed`, 11px, fontWeight 600.

## Month View Week Start
- `weekStartsOn: 0` in `date-fns` = Sunday start. `1` = Monday.
- The day-header array in `MonthView.tsx` is hardcoded — must be reordered alongside the `weekStartsOn` change.

## Reschedule & Sync (added 2026-03-24)

- **Reschedule must mark sync_status=modified**: `CalendarService.reschedule()` sets `sync_status = "modified"` when `new_date != scheduled.date` and the workout was `"synced"`. Without this, `sync_all` (filters on `pending/modified/failed`) silently skips rescheduled workouts and returns `{synced:0}`. Notes-only and same-date reschedules leave status unchanged.
- **`currentDate` invariant**: `CalendarPage.handlePrev`/`handleNext` do `±7 days from currentDate` — it must always be a Sunday week-start. Use `setCurrentDate(getWeekStart(newDate))`, never `setCurrentDate(newDate)` (arbitrary mid-week date breaks navigation anchor).
- **Mobile reschedule navigation**: After reschedule on mobile, call `setSelectedDay(date)` AND `setCurrentDate(getWeekStart(newDate))` so the day strip shows the workout on its new date.
