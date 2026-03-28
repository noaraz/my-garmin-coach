# Sync from Workout Detail Panel — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Sync to Garmin" button to the WorkoutDetailPanel so users can sync a single planned workout without triggering a full Sync All.

**Architecture:** `syncOne(id)` already exists in `api/client.ts` (unused). Add `syncOneWorkout(id)` to `useCalendar` (same pattern as `syncAllWorkouts`), add `onSync` prop to `WorkoutDetailPanel` + `WorkoutDetailPlanned`, wire in both CalendarPage and TodayPage. Panel manages its own `isSyncing` state.

**Tech Stack:** React 18, TypeScript strict, Vitest + React Testing Library, existing `syncOne` API client function.

**Spec:** `docs/superpowers/specs/2026-03-27-sync-from-detail-panel-design.md`

---

## Chunk 1: Hook + API wiring

### Task 1: Add `syncOneWorkout` to `useCalendar`

**Files:**
- Modify: `frontend/src/hooks/useCalendar.ts`
- Modify: `frontend/src/api/client.ts` (import `syncOne`)
- Test: `frontend/src/hooks/__tests__/useCalendar.syncOne.test.ts` (new file)

**Context:**
`useCalendar.ts` already has `syncAllWorkouts` (lines 46–54) which calls `syncAll()` then refetches. Mirror that pattern exactly. `syncOne` is already in `client.ts` at line ~113 but not imported by the hook.

`SyncStatusItem` is in `api/types.ts`:
```typescript
export interface SyncStatusItem {
  id: number
  date: string
  sync_status: SyncStatus
  garmin_workout_id: string | null
}
```

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/__tests__/useCalendar.syncOne.test.ts`:

```typescript
import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'

const { mockSyncOne, mockFetchCalendarRange } = vi.hoisted(() => ({
  mockSyncOne: vi.fn(),
  mockFetchCalendarRange: vi.fn(),
}))

vi.mock('../../api/client', () => ({
  fetchCalendarRange: mockFetchCalendarRange,
  scheduleWorkout: vi.fn(),
  rescheduleWorkout: vi.fn(),
  unscheduleWorkout: vi.fn(),
  syncAll: vi.fn(),
  syncOne: mockSyncOne,
  pairActivity: vi.fn(),
  unpairActivity: vi.fn(),
  updateWorkoutNotes: vi.fn(),
}))

import { useCalendar } from '../useCalendar'

const emptyCalendar = { workouts: [], unplanned_activities: [] }

describe('useCalendar syncOneWorkout', () => {
  beforeEach(() => {
    mockFetchCalendarRange.mockResolvedValue(emptyCalendar)
    mockSyncOne.mockReset()
  })

  it('calls syncOne with the given id and refetches calendar', async () => {
    const syncResult = { id: 5, date: '2026-04-01', sync_status: 'synced', garmin_workout_id: 'gw-123' }
    mockSyncOne.mockResolvedValue(syncResult)
    const refreshed = { workouts: [{ id: 5, sync_status: 'synced' }], unplanned_activities: [] }
    // First call: initial load. Second call: after syncOne.
    mockFetchCalendarRange.mockResolvedValueOnce(emptyCalendar).mockResolvedValueOnce(refreshed)

    const start = new Date('2026-03-31')
    const end = new Date('2026-04-06')
    const { result } = renderHook(() => useCalendar(start, end))

    // Wait for initial load
    await act(async () => {})

    let returned: unknown
    await act(async () => {
      returned = await result.current.syncOneWorkout(5)
    })

    expect(mockSyncOne).toHaveBeenCalledWith(5)
    expect(mockFetchCalendarRange).toHaveBeenCalledTimes(2)
    expect(result.current.workouts).toHaveLength(1)
    expect(returned).toEqual(syncResult)
  })
})
```

- [ ] **Step 2: Run to confirm it fails**

```bash
cd frontend && npx vitest run src/hooks/__tests__/useCalendar.syncOne.test.ts
```
Expected: FAIL — `result.current.syncOneWorkout is not a function`

- [ ] **Step 3: Add `syncOneWorkout` to `useCalendar`**

In `frontend/src/hooks/useCalendar.ts`:

1. Add `syncOne` to the import from `../api/client`:
```typescript
import { fetchCalendarRange, scheduleWorkout, rescheduleWorkout, unscheduleWorkout, syncAll, syncOne, pairActivity, unpairActivity, updateWorkoutNotes } from '../api/client'
```

2. Add `SyncStatusItem` to the import from `../api/types`:
```typescript
import type { ScheduledWorkoutWithActivity, GarminActivity, SyncStatusItem } from '../api/types'
```

3. Add `syncOneWorkout` alongside `syncAllWorkouts` (after line 54):
```typescript
const syncOneWorkout = async (id: number): Promise<SyncStatusItem> => {
  const result = await syncOne(id)
  const current = rangeRef.current
  const response = await fetchCalendarRange(toDateString(current.start), toDateString(current.end))
  setWorkouts(response.workouts)
  setUnplannedActivities(response.unplanned_activities)
  return result
}
```

4. Add `syncOneWorkout` to the return object:
```typescript
return { workouts, unplannedActivities, loading, error, schedule, reschedule, remove, syncAllWorkouts, syncOneWorkout, pair, unpair, loadRange, updateNotes }
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
cd frontend && npx vitest run src/hooks/__tests__/useCalendar.syncOne.test.ts
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useCalendar.ts frontend/src/hooks/__tests__/useCalendar.syncOne.test.ts
git commit -m "feat: add syncOneWorkout to useCalendar hook"
```

---

## Chunk 2: WorkoutDetailPanel — prop + button

### Task 2: Add `onSync` prop and sync button to WorkoutDetailPanel

**Files:**
- Modify: `frontend/src/components/calendar/WorkoutDetailPanel.tsx`
- Test: `frontend/src/components/calendar/__tests__/WorkoutDetailPanel.sync.test.tsx` (new file)

**Context:**
`WorkoutDetailPanelProps` is at lines 97–107. `WorkoutDetailPlanned` inline props are at lines 141–150. The dispatcher (`WorkoutDetailPanel` export) is at lines ~1108–1148. The sync status indicator block is at lines 257–272 inside `WorkoutDetailPlanned`.

The pattern for an existing action button (e.g. "Edit in Builder") is the `onNavigateToBuilder` prop — use the same style.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/calendar/__tests__/WorkoutDetailPanel.sync.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect } from 'vitest'
import { WorkoutDetailPanel } from '../WorkoutDetailPanel'
import type { ScheduledWorkoutWithActivity } from '../../../api/types'

const baseWorkout: ScheduledWorkoutWithActivity = {
  id: 1,
  date: '2026-04-01',
  sync_status: 'pending',
  garmin_workout_id: null,
  workout_template_id: null,
  completed: false,
  notes: null,
  matched_activity_id: null,
  activity: null,
  resolved_steps: null,
  training_plan_id: null,
  garmin_schedule_id: null,
}

const baseProps = {
  workout: baseWorkout,
  activity: null,
  template: undefined,
  onClose: vi.fn(),
  onReschedule: vi.fn(),
  onRemove: vi.fn(),
  onUnpair: vi.fn(),
  onUpdateNotes: vi.fn(),
  onNavigateToBuilder: vi.fn(),
}

describe('WorkoutDetailPanel sync button', () => {
  it('shows sync button when onSync provided', () => {
    render(<WorkoutDetailPanel {...baseProps} onSync={vi.fn()} />)
    expect(screen.getByRole('button', { name: /sync to garmin/i })).toBeInTheDocument()
  })

  it('does not show sync button when onSync is undefined', () => {
    render(<WorkoutDetailPanel {...baseProps} />)
    expect(screen.queryByRole('button', { name: /sync to garmin/i })).not.toBeInTheDocument()
  })

  it('shows syncing state while in-flight and re-enables after', async () => {
    let resolve!: () => void
    const onSync = vi.fn(() => new Promise<void>(r => { resolve = r }))
    render(<WorkoutDetailPanel {...baseProps} onSync={onSync} />)

    fireEvent.click(screen.getByRole('button', { name: /sync to garmin/i }))

    expect(screen.getByText(/syncing/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /syncing/i })).toBeDisabled()

    resolve()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /sync to garmin/i })).not.toBeDisabled()
    )
  })

  it('re-enables button even when onSync throws', async () => {
    const onSync = vi.fn().mockRejectedValue(new Error('network error'))
    render(<WorkoutDetailPanel {...baseProps} onSync={onSync} />)

    fireEvent.click(screen.getByRole('button', { name: /sync to garmin/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /sync to garmin/i })).not.toBeDisabled()
    )
  })
})
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
cd frontend && npx vitest run src/components/calendar/__tests__/WorkoutDetailPanel.sync.test.tsx
```
Expected: FAIL — button not found

- [ ] **Step 3: Add `onSync` to interfaces and pass through dispatcher**

In `WorkoutDetailPanel.tsx`:

1. Add to `WorkoutDetailPanelProps` (after `onNavigateToBuilder`):
```typescript
onSync?: (id: number) => Promise<void>
```

2. Add to `WorkoutDetailPlanned` inline props type (after `onNavigateToBuilder`):
```typescript
onSync?: (id: number) => Promise<void>
```

3. In the `WorkoutDetailPanel` dispatcher, add `onSync` to destructure and pass-through:
```typescript
export function WorkoutDetailPanel({
  workout, activity, template, onClose, onReschedule, onRemove,
  onUnpair, onUpdateNotes, onNavigateToBuilder, onSync,  // ← add onSync
}: WorkoutDetailPanelProps) {
```
And in the `<WorkoutDetailPlanned .../>` render:
```typescript
<WorkoutDetailPlanned
  workout={workout}
  template={template}
  onClose={onClose}
  onReschedule={onReschedule}
  onRemove={onRemove}
  onUpdateNotes={onUpdateNotes}
  onNavigateToBuilder={onNavigateToBuilder}
  onSync={onSync}    // ← add this
/>
```

- [ ] **Step 4: Add `isSyncing` state and sync button in `WorkoutDetailPlanned`**

In `WorkoutDetailPlanned`, add state and button next to the sync status indicator (lines ~257–272).

Add `useState` to imports if not already present (it is — the component uses `useRef`, `useState`, `useEffect`).

Add after existing imports inside `WorkoutDetailPlanned`:
```typescript
const [isSyncing, setIsSyncing] = useState(false)

const handleSync = async () => {
  if (!onSync || !workout.id) return
  setIsSyncing(true)
  try {
    await onSync(workout.id)
  } finally {
    setIsSyncing(false)
  }
}
```

Replace the sync status block (lines ~257–272) with:
```tsx
{/* Sync status + sync button */}
<div
  style={{
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '20px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
  }}
>
  <span style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{syncStatusLabel(workout.sync_status)}</span>
  <span style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif" }}>
    {syncStatusText(workout.sync_status)}
  </span>
  {onSync && (
    <button
      onClick={handleSync}
      disabled={isSyncing}
      style={{
        marginLeft: 'auto',
        fontSize: '11px',
        padding: '3px 8px',
        borderRadius: '4px',
        border: '1px solid var(--border)',
        background: 'var(--bg-surface-2)',
        color: 'var(--text-secondary)',
        cursor: isSyncing ? 'not-allowed' : 'pointer',
        opacity: isSyncing ? 0.6 : 1,
      }}
    >
      {isSyncing ? 'Syncing…' : 'Sync to Garmin'}
    </button>
  )}
</div>
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd frontend && npx vitest run src/components/calendar/__tests__/WorkoutDetailPanel.sync.test.tsx
```
Expected: all 4 PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/calendar/WorkoutDetailPanel.tsx \
        frontend/src/components/calendar/__tests__/WorkoutDetailPanel.sync.test.tsx
git commit -m "feat: add sync button to WorkoutDetailPlanned panel"
```

---

## Chunk 3: Wire CalendarPage + TodayPage

### Task 3: Wire `onSync` in CalendarPage

**Files:**
- Modify: `frontend/src/pages/CalendarPage.tsx`

**Context:**
CalendarPage already uses `useCalendar` and destructures `syncAllWorkouts` (plus many others). It uses `useGarminStatus()` for `garminConnected`. The panel is rendered around line 403–427. The pattern to follow is the existing `onReschedule` handler.

- [ ] **Step 1: Add `syncOneWorkout` to the destructure and wire handler**

In `CalendarPage.tsx`:

1. Add `syncOneWorkout` to `useCalendar` destructure (find the existing destructure — it includes `syncAllWorkouts`):
```typescript
const { workouts, ..., syncAllWorkouts, syncOneWorkout, ... } = useCalendar(...)
```

2. Add `handleSync` alongside the other handlers (e.g. near `handleRequestRemove`):
```typescript
const handleSync = async (id: number) => {
  const result = await syncOneWorkout(id)
  setSelectedWorkout(prev =>
    prev ? { ...prev, sync_status: result.sync_status, garmin_workout_id: result.garmin_workout_id } : null
  )
}
```

3. Pass to `WorkoutDetailPanel`:
```tsx
<WorkoutDetailPanel
  ...
  onSync={garminConnected ? handleSync : undefined}
/>
```

- [ ] **Step 2: Run the full frontend test suite**

```bash
cd frontend && npm test -- --run
```
Expected: all pass (no regressions)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/CalendarPage.tsx
git commit -m "feat: wire onSync handler in CalendarPage"
```

### Task 4: Wire `onSync` in TodayPage

**Files:**
- Modify: `frontend/src/pages/TodayPage.tsx`

**Context:**
TodayPage has a narrower `useCalendar` destructure than CalendarPage — currently only `{ workouts, loading, updateNotes }`. It also uses `useGarminStatus()`. Add `syncOneWorkout` explicitly and wire the same handler.

- [ ] **Step 1: Add `syncOneWorkout` to destructure and wire handler**

In `TodayPage.tsx`:

1. Expand `useCalendar` destructure:
```typescript
const { workouts, loading, updateNotes, syncOneWorkout } = useCalendar(weekStart, weekEnd)
```

2. Add handler (same as CalendarPage):
```typescript
const handleSync = async (id: number) => {
  const result = await syncOneWorkout(id)
  setSelectedWorkout(prev =>
    prev ? { ...prev, sync_status: result.sync_status, garmin_workout_id: result.garmin_workout_id } : null
  )
}
```

3. Pass to `WorkoutDetailPanel`:
```tsx
<WorkoutDetailPanel
  ...
  onSync={garminConnected ? handleSync : undefined}
/>
```

- [ ] **Step 2: Run the full frontend test suite**

```bash
cd frontend && npm test -- --run
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TodayPage.tsx
git commit -m "feat: wire onSync handler in TodayPage"
```

---

## Chunk 4: Final verification

- [ ] **Step 1: Run all frontend tests**

```bash
cd frontend && npm test -- --run
```
Expected: all pass, no regressions

- [ ] **Step 2: Run backend tests**

```bash
cd backend && .venv/bin/pytest tests/integration/test_api_sync.py -v --no-cov
```
Expected: 33 pass (no backend changes needed — `POST /api/v1/sync/{id}` already covered)

- [ ] **Step 3: TypeScript build check**

```bash
cd frontend && npx tsc -b --noEmit
```
Expected: 0 errors. Common pitfalls: `onSync` prop type mismatch, `SyncStatusItem` import missing in a page.

- [ ] **Step 4: Manual smoke test (Render Preview)**

1. Open a planned workout's detail panel
2. Confirm "Sync to Garmin" button appears (Garmin connected) or is absent (Garmin not connected)
3. Click it — button shows "Syncing…" briefly, then sync status indicator updates to "Synced to Garmin"
4. Open TodayPage on mobile → "View Details" → confirm same button appears and works
