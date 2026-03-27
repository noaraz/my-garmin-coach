# Design: Sync to Garmin from Workout Detail Panel

**Date:** 2026-03-27
**Status:** Approved

## Problem

Users can only trigger a Garmin sync from the "Sync All" button on the Calendar toolbar. There is no way to sync a single workout without syncing everything. This is slow and unnecessary when only one workout has changed or failed.

## Scope

- `WorkoutDetailPanel` — add sync button to planned (non-completed) workout view
- `useCalendar` hook — add `syncOneWorkout(id)` method
- `CalendarPage` — wire `onSync` handler
- `TodayPage` — wire `onSync` handler (same panel, same component)
- Mobile: covered automatically since both pages use the same `WorkoutDetailPanel`

## Design

### 1. `useCalendar` hook — `syncOneWorkout`

Add a new method alongside the existing `syncAllWorkouts`:

```typescript
syncOneWorkout: (id: number) => Promise<SyncStatusItem>
```

Implementation:
1. Calls `syncOne(id)` from `client.ts` (already exists, unused in UI)
2. Refetches the calendar range (same pattern as `syncAllWorkouts`)
3. Returns the `SyncStatusItem` response so the page can patch `selectedWorkout`

### 2. `WorkoutDetailPanel` — new `onSync` prop

Add `onSync?: (id: number) => Promise<void>` to **both**:
- `WorkoutDetailPanelProps` (outer interface, lines ~97–107)
- Passed through the `WorkoutDetailPanel` dispatcher to `WorkoutDetailPlanned`

The prop is consumed only in `WorkoutDetailPlanned` (not `WorkoutDetailCompleted` — completed workouts have their Garmin template deleted on pairing; a sync button would be misleading).

- Local `isSyncing: boolean` state inside `WorkoutDetailPlanned`
- Button placement: next to the existing sync status indicator
- Button label: "Sync to Garmin" (idle) / spinner + "Syncing…" (in-flight)
- Button disabled while `isSyncing` or when `onSync` is undefined
- Button hidden when Garmin is not connected (pass `garminConnected` prop down, or check it in the page before passing `onSync`)
- `isSyncing` resets in a `finally` block — always, on both success and error paths
- On error: status indicator retains its current value; button re-enables; user can retry

### 3. CalendarPage — `handleSync`

```typescript
const handleSync = async (id: number) => {
  const result = await syncOneWorkout(id)
  // SyncStatusItem is a subset of ScheduledWorkoutWithActivity.
  // Patch only the two sync fields — do not replace the whole object.
  setSelectedWorkout(prev =>
    prev ? { ...prev, sync_status: result.sync_status, garmin_workout_id: result.garmin_workout_id } : null
  )
  // workouts[] is already refreshed inside syncOneWorkout (via fetchCalendarRange).
  // selectedWorkout is a separate copy and must be patched independently.
}
```

Pass as `onSync={garminConnected ? handleSync : undefined}` to `WorkoutDetailPanel` — this hides the button when Garmin is not connected without threading an extra prop.

### 4. TodayPage — same pattern

TodayPage uses `useCalendar` and opens the same `WorkoutDetailPanel`. Wire identically to CalendarPage.

**Important**: TodayPage's existing `useCalendar` destructure (`const { workouts, loading, updateNotes } = useCalendar(...)`) is narrower than CalendarPage's. Add `syncOneWorkout` to TodayPage's destructure explicitly.

## Data Flow

```
User clicks "Sync to Garmin"
  → panel sets isSyncing=true
  → onSync(workout.id) fires
  → CalendarPage/TodayPage calls syncOneWorkout(id)
    → POST /api/v1/sync/{id}
    → refetch calendar range → setWorkouts(...)
    → return { id, sync_status, garmin_workout_id }
  → page patches selectedWorkout with new fields
  → panel re-renders: sync status indicator updates, isSyncing=false
```

## Error Handling

- Network / API error → `isSyncing` clears in `finally` block; status indicator unchanged
- `sync_status: "failed"` returned → status indicator shows "failed"; button available to retry
- No toast/modal — the sync status indicator is sufficient feedback

## Mobile

`WorkoutDetailPanel` already handles mobile layout via `useIsMobile()` + CSS class `workout-detail-panel-mobile`. TodayPage opens the same component. No separate mobile work required beyond ensuring the button is responsive within the panel.

## Testing

**Backend**: `POST /api/v1/sync/{id}` already has full integration test coverage (`TestSyncSingle`).

**Frontend**:
- Unit test for `syncOneWorkout` in `useCalendar` — mocks `syncOne` + `fetchCalendarRange`, verifies refetch and return value
- RTL tests for `WorkoutDetailPlanned`:
  - Sync button renders when `onSync` prop provided
  - Button shows "Syncing…" and is disabled while in-flight
  - Button re-enables after completion
  - Status indicator updates when `workout.sync_status` changes

## Out of Scope

- Sync button on completed workouts (Garmin template is deleted on pairing)
- Sync button on unplanned activities (no associated scheduled workout)
- Toast/notification system (the status indicator is sufficient)
