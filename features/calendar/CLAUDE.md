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

## Workout Detail Panel (2026-03-20)

Design spec: `docs/superpowers/specs/2026-03-20-workout-detail-panel-design.md`

- **Panel replaces card navigation**: `WorkoutCard` no longer calls `navigate()`. Instead fires `onCardClick(workout)` prop. `UnplannedActivityCard` similarly fires `onCardClick(activity)`.
- **Callback threading**: `CalendarPage` → `CalendarView` → `WeekView`/`MonthView` → `DayCell` → cards. All pass `onWorkoutClick` and `onActivityClick` callbacks.
- **Panel state in CalendarPage**: `selectedWorkout: ScheduledWorkoutWithActivity | null` + `selectedActivity: GarminActivity | null`. Panel open when either is non-null.
- **Notes**: `ScheduledWorkout.notes` column already exists in DB model + schema. PATCH endpoint extended to accept `{ date?, notes? }`.
- **Escape/backdrop close**: `useEffect` with `keydown` listener for Escape. Backdrop `onClick` for outside clicks.
