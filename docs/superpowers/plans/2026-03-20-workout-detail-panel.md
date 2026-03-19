# Workout Detail Panel — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace click-to-builder navigation with a slide-out Quick View panel showing workout details, compliance data, and contextual actions.

**Architecture:** New `WorkoutDetailPanel` component rendered by `CalendarPage` with overlay + slide animation. Three sub-components for each panel state (planned, completed, unplanned). Backend PATCH endpoint extended to accept optional `notes` field. All panel data is already loaded — zero new DB queries on panel open.

**Tech Stack:** React 18, TypeScript, CSS custom properties, existing compliance/formatting utils.

**Design Spec:** `docs/superpowers/specs/2026-03-20-workout-detail-panel-design.md`

---

## Chunk 1: Documentation Updates

### Task 0: Update root PLAN.md

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: Add Workout Detail Panel to Feature Build Order table**

Add row after Activity Fetch (row 9):

```markdown
| 10 | Workout Detail Panel | `features/calendar/` | calendar, garmin-activity-fetch | ⬜ |
```

- [ ] **Step 2: Add Key Mechanism entry**

Add under "### 2. Activity Compliance (Feature 9)":

```markdown
### 3. Workout Detail Panel (Feature 10)

```
1. Click any card on calendar → slide-out Quick View panel from right
2. Three states: Planned (actions: reschedule, edit, remove), Completed (compliance comparison, unpair), Unplanned (read-only metrics)
3. Notes field with debounced auto-save
4. Panel uses already-loaded CalendarResponse data — zero additional DB queries
```
```

- [ ] **Step 3: Commit**

```bash
git add PLAN.md
git commit -m "docs: add workout detail panel to root PLAN.md"
```

---

### Task 1: Update root CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add Workout Detail Panel entry to Features table**

In the Features table, add a row:

```markdown
| Workout Detail Panel | `features/calendar/` | Slide-out Quick View panel for workout/activity details |
```

This lives under `features/calendar/` since it's a calendar sub-feature, not a standalone feature.

- [ ] **Step 2: Add CLAUDE.md section for WorkoutDetailPanel patterns**

Add after the "workoutStats Utilities" section:

```markdown
## WorkoutDetailPanel Patterns (added 2026-03-20)

- **Panel trigger**: `WorkoutCard` and `UnplannedActivityCard` fire `onCardClick` callback instead of navigating
- **State management**: `CalendarPage` holds `selectedWorkout` / `selectedActivity` state; panel is purely presentational
- **Data source**: All data already in CalendarPage state from `CalendarResponse` — panel open = zero DB queries
- **Notes save**: Debounced 500ms on input change, flush on blur. Uses extended PATCH `/calendar/{id}` with optional `notes` field
- **Compliance badge mapping**: `on_target` → "ON TARGET", `close` → "CLOSE", `off_target` → "OFF TARGET", `completed_no_plan` → "COMPLETED"
- **formatPace**: Already exists in `frontend/src/utils/formatting.ts` — `formatPace(secPerKm)` → `"6:00/km"`
- **Panel close**: X button, click backdrop, Escape key — all handled in `WorkoutDetailPanel.tsx`
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add workout detail panel to root CLAUDE.md features table"
```

---

### Task 2: Update features/calendar/ PLAN.md and CLAUDE.md

**Files:**
- Modify: `features/calendar/PLAN.md`
- Modify: `features/calendar/CLAUDE.md`

- [ ] **Step 1: Add Workout Detail Panel section to features/calendar/PLAN.md**

Append after the existing "### API Client Tests" section:

```markdown
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
```

Add to Implementation Files section:

```
  components/calendar/ — + WorkoutDetailPanel, WorkoutDetailPlanned, WorkoutDetailCompleted, WorkoutDetailUnplanned
```

- [ ] **Step 2: Add panel patterns to features/calendar/CLAUDE.md**

Append after the "Testing: useNavigate Requires a Router" section:

```markdown
## Workout Detail Panel (2026-03-20)

Design spec: `docs/superpowers/specs/2026-03-20-workout-detail-panel-design.md`

- **Panel replaces card navigation**: `WorkoutCard` no longer calls `navigate()`. Instead fires `onCardClick(workout)` prop. `UnplannedActivityCard` similarly fires `onCardClick(activity)`.
- **Callback threading**: `CalendarPage` → `CalendarView` → `WeekView`/`MonthView` → `DayCell` → cards. All pass `onWorkoutClick` and `onActivityClick` callbacks.
- **Panel state in CalendarPage**: `selectedWorkout: ScheduledWorkoutWithActivity | null` + `selectedActivity: GarminActivity | null`. Panel open when either is non-null.
- **Notes**: `ScheduledWorkout.notes` column already exists in DB model + schema. PATCH endpoint extended to accept `{ date?, notes? }`.
- **Escape/backdrop close**: `useEffect` with `keydown` listener for Escape. Backdrop `onClick` for outside clicks.
```

- [ ] **Step 3: Commit**

```bash
git add features/calendar/PLAN.md features/calendar/CLAUDE.md
git commit -m "docs: add workout detail panel to calendar feature docs"
```

---

### Task 3: Update features/garmin-activity-fetch/ CLAUDE.md

**Files:**
- Modify: `features/garmin-activity-fetch/CLAUDE.md`

- [ ] **Step 1: Add cross-reference to detail panel**

Append to the end of `features/garmin-activity-fetch/CLAUDE.md`:

```markdown
## Workout Detail Panel (cross-reference)

The detail panel displays activity data fetched by this feature:
- **Completed state**: Shows compliance badge + planned vs actual comparison using `computeCompliance()`
- **Unplanned state**: Shows activity metrics (duration, distance, pace, HR, calories)
- **Unpair action**: Calls existing `POST /calendar/{id}/unpair` endpoint
- **Panel design spec**: `docs/superpowers/specs/2026-03-20-workout-detail-panel-design.md`
- **Implementation lives in**: `features/calendar/` (panel is a calendar sub-feature)
```

- [ ] **Step 2: Commit**

```bash
git add features/garmin-activity-fetch/CLAUDE.md
git commit -m "docs: cross-reference workout detail panel in activity fetch CLAUDE.md"
```

---

### Task 4: Update STATUS.md

**Files:**
- Modify: `STATUS.md`

- [ ] **Step 1: Update current focus and add panel tasks**

Update the header to mention the panel:

```markdown
Last updated: 2026-03-20 (Workout Detail Panel — slide-out Quick View)

## Current Focus: Workout Detail Panel
```

Add a new section after the Activity Fetch table:

```markdown
### Workout Detail Panel
| Task | Status |
|------|--------|
| Docs: root PLAN.md, CLAUDE.md, feature docs, STATUS.md | ⬜ |
| Backend: extend PATCH /calendar/{id} for notes | ⬜ |
| Frontend: WorkoutDetailPanel shell (overlay, slide, close) | ⬜ |
| Frontend: WorkoutDetailPlanned content | ⬜ |
| Frontend: WorkoutDetailCompleted content | ⬜ |
| Frontend: WorkoutDetailUnplanned content | ⬜ |
| Frontend: Card click → panel (replace builder navigation) | ⬜ |
| Frontend: CalendarPage panel state + render | ⬜ |
| Frontend: Notes save (debounced, useCalendar hook) | ⬜ |
| Frontend: Tests | ⬜ |
```

- [ ] **Step 2: Mark auto-sync row as done in Activity Fetch table**

Change the auto-sync row from ⬜ to ✅:

```markdown
| Frontend: auto-sync on mount, reschedule action | ✅ |
```

- [ ] **Step 3: Commit**

```bash
git add STATUS.md
git commit -m "docs: update STATUS.md — add workout detail panel tasks"
```

---

## Chunk 2: Backend — Extend PATCH endpoint for notes

> **Note:** The `notes` column already exists on `ScheduledWorkout` model (`backend/src/db/models.py:99`) and in the initial alembic migration (`7cd1f83b9815_initial_schema.py:116`). No new migration needed. The `ScheduledWorkoutRead` schema already includes `notes: Optional[str] = None` (`schemas.py:126`). The only backend change is making the PATCH endpoint accept notes.

### Task 5: Backend test — PATCH accepts notes

**Files:**
- Modify: `backend/tests/integration/test_api_calendar.py`

- [ ] **Step 1: Write failing test for notes update**

Add test to the calendar integration tests:

```python
async def test_patch_scheduled_workout_notes(
    async_client: AsyncClient,
    auth_headers: dict,
    scheduled_workout_id: int,
):
    """PATCH /calendar/{id} with notes only (no date change)."""
    response = await async_client.patch(
        f"/api/v1/calendar/{scheduled_workout_id}",
        json={"notes": "Felt strong today"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "Felt strong today"


async def test_patch_scheduled_workout_date_and_notes(
    async_client: AsyncClient,
    auth_headers: dict,
    scheduled_workout_id: int,
):
    """PATCH /calendar/{id} with both date and notes."""
    response = await async_client.patch(
        f"/api/v1/calendar/{scheduled_workout_id}",
        json={"date": "2026-04-01", "notes": "Moved to next week"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-04-01"
    assert data["notes"] == "Moved to next week"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_api_calendar.py -k "notes" -v`
Expected: FAIL (schema validation rejects notes field / requires date)

- [ ] **Step 3: Update RescheduleUpdate schema to accept optional notes**

Modify `backend/src/api/schemas.py` line 114-115:

```python
class RescheduleUpdate(BaseModel):
    date: Optional[date] = None
    notes: Optional[str] = None
```

Add import at top if needed: `from typing import Optional`

- [ ] **Step 4: Update calendar_service.reschedule to handle notes**

Modify `backend/src/services/calendar_service.py` — the `reschedule` method (line 169-182):

```python
async def reschedule(
    self, session: AsyncSession, scheduled_id: int, new_date: date | None, user_id: int, notes: str | None = None
) -> ScheduledWorkout:
    """Update a ScheduledWorkout date and/or notes. Raises ValueError if not found or not owned."""
    scheduled = await scheduled_workout_repository.get(session, scheduled_id)
    if scheduled is None or scheduled.user_id != user_id:
        raise ValueError(f"ScheduledWorkout {scheduled_id} not found")

    if new_date is not None:
        scheduled.date = new_date
    if notes is not None:
        scheduled.notes = notes
    scheduled.updated_at = datetime.utcnow()
    session.add(scheduled)
    await session.commit()
    await session.refresh(scheduled)
    return scheduled
```

Also update the module-level shim:

```python
async def reschedule(
    session: AsyncSession, scheduled_id: int, new_date: date | None, user_id: int, notes: str | None = None
) -> ScheduledWorkout:
    return await calendar_service.reschedule(session, scheduled_id, new_date, user_id, notes=notes)
```

- [ ] **Step 5: Update router to pass notes**

Modify `backend/src/api/routers/calendar.py` line 186-187:

```python
sw = await reschedule(session, scheduled_id, body.date, current_user.id, notes=body.notes)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/integration/test_api_calendar.py -k "notes" -v`
Expected: PASS

- [ ] **Step 7: Run full backend test suite (verify existing reschedule tests still pass)**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass. Especially verify existing reschedule tests (that send only `date`) still work with the now-optional `date` field. The `reschedule` service method handles `None` date by skipping the date update.

- [ ] **Step 8: Commit**

```bash
git add backend/src/api/schemas.py backend/src/services/calendar_service.py backend/src/api/routers/calendar.py backend/tests/integration/test_api_calendar.py
git commit -m "feat: extend PATCH /calendar/{id} to accept optional notes field"
```

---

## Chunk 3: Frontend — API client + hook + card click callbacks

### Task 6: Frontend API client — updateWorkoutNotes function

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add updateWorkoutNotes function**

Add after `rescheduleWorkout` (line ~93):

```typescript
export const updateWorkoutNotes = (id: number, notes: string) =>
  request<ScheduledWorkout>(`/calendar/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ notes }),
  })
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add updateWorkoutNotes API client function"
```

---

### Task 7: useCalendar hook — add updateNotes method

**Files:**
- Modify: `frontend/src/hooks/useCalendar.ts`

- [ ] **Step 1: Add updateNotes method**

Import `updateWorkoutNotes` from client. Add method before the return statement:

```typescript
const updateNotes = async (id: number, notes: string) => {
  const updated = await updateWorkoutNotes(id, notes)
  setWorkouts(prev => prev.map(w => w.id === id ? { ...w, notes: updated.notes } : w))
}
```

Update the return to include `updateNotes`:

```typescript
return { workouts, unplannedActivities, loading, error, schedule, reschedule, remove, syncAllWorkouts, pair, unpair, loadRange, updateNotes }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useCalendar.ts
git commit -m "feat: add updateNotes to useCalendar hook"
```

---

### Task 8: Update WorkoutCard — replace navigate with onCardClick

**Files:**
- Modify: `frontend/src/components/calendar/WorkoutCard.tsx`

- [ ] **Step 1: Add onCardClick prop, remove navigate**

Update `WorkoutCardProps` interface:

```typescript
interface WorkoutCardProps {
  workout: ScheduledWorkoutWithActivity
  template: WorkoutTemplate | undefined
  onRemove: (id: number) => void
  onCardClick?: (workout: ScheduledWorkoutWithActivity) => void
  displayName?: string
  compact?: boolean
}
```

Remove `useNavigate` import and usage. Replace `handleCardClick`:

```typescript
const handleCardClick = () => {
  if (onCardClick) {
    onCardClick(workout)
  }
}
```

Update cursor logic:

```typescript
cursor: onCardClick ? 'pointer' : 'default',
```

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm test -- --run`
Expected: Some tests may need updating (those that check for navigate behavior)

- [ ] **Step 3: Fix any broken tests**

Update Calendar.test.tsx tests that relied on `useNavigate` mock — they should now check that `onCardClick` is called instead. The `MemoryRouter` wrapper may still be needed for other components.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/calendar/WorkoutCard.tsx frontend/src/tests/Calendar.test.tsx
git commit -m "refactor: WorkoutCard fires onCardClick instead of navigating to builder"
```

---

### Task 9: Update UnplannedActivityCard — add onCardClick

**Files:**
- Modify: `frontend/src/components/calendar/UnplannedActivityCard.tsx`

- [ ] **Step 1: Add onCardClick prop**

Update interface:

```typescript
interface UnplannedActivityCardProps {
  activity: GarminActivity
  onCardClick?: (activity: GarminActivity) => void
  compact?: boolean
}
```

Add click handler to the card container:

```typescript
onClick={() => onCardClick?.(activity)}
style={{
  ...existing styles,
  cursor: onCardClick ? 'pointer' : 'default',
}}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/calendar/UnplannedActivityCard.tsx
git commit -m "feat: UnplannedActivityCard fires onCardClick callback"
```

---

### Task 10: Thread onCardClick through view hierarchy

**Files:**
- Modify: `frontend/src/components/calendar/CalendarView.tsx`
- Modify: `frontend/src/components/calendar/WeekView.tsx`
- Modify: `frontend/src/components/calendar/MonthView.tsx`
- Modify: `frontend/src/components/calendar/DayCell.tsx`

- [ ] **Step 1: Add callbacks to CalendarViewProps**

```typescript
interface CalendarViewProps {
  // ... existing props
  onWorkoutClick?: (workout: ScheduledWorkoutWithActivity) => void
  onActivityClick?: (activity: GarminActivity) => void
}
```

Pass them through to `WeekView` and `MonthView`.

- [ ] **Step 2: Add callbacks to WeekViewProps, pass to DayCell**

```typescript
interface WeekViewProps {
  // ... existing props
  onWorkoutClick?: (workout: ScheduledWorkoutWithActivity) => void
  onActivityClick?: (activity: GarminActivity) => void
}
```

Pass to each `DayCell`.

- [ ] **Step 3: Add callbacks to DayCellProps, pass to cards**

```typescript
interface DayCellProps {
  // ... existing props
  onWorkoutClick?: (workout: ScheduledWorkoutWithActivity) => void
  onActivityClick?: (activity: GarminActivity) => void
}
```

Pass `onCardClick={onWorkoutClick}` to `WorkoutCard` and `onCardClick={onActivityClick}` to `UnplannedActivityCard`.

- [ ] **Step 4: Add callbacks to MonthViewProps, pass to cards**

`MonthView` renders `WorkoutCard` and `UnplannedActivityCard` directly in its grid cells (it does NOT use `DayCell`). Add both callbacks and pass to cards:

```typescript
interface MonthViewProps {
  // ... existing props
  onWorkoutClick?: (workout: ScheduledWorkoutWithActivity) => void
  onActivityClick?: (activity: GarminActivity) => void
}
```

- [ ] **Step 5: Run tests**

Run: `cd frontend && npm test -- --run`
Expected: All pass (callbacks are optional props)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/calendar/CalendarView.tsx frontend/src/components/calendar/WeekView.tsx frontend/src/components/calendar/MonthView.tsx frontend/src/components/calendar/DayCell.tsx
git commit -m "feat: thread onWorkoutClick/onActivityClick through calendar view hierarchy"
```

---

## Chunk 4: Frontend — Panel components

### Task 11: WorkoutDetailPanel shell

**Files:**
- Create: `frontend/src/components/calendar/WorkoutDetailPanel.tsx`

- [ ] **Step 1: Write test for panel shell**

Create test in `frontend/src/tests/WorkoutDetailPanel.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { WorkoutDetailPanel } from '../components/calendar/WorkoutDetailPanel'

// Test: renders panel when workout is provided
// Test: calls onClose when X button clicked
// Test: calls onClose when Escape pressed
// Test: calls onClose when backdrop clicked
// Test: renders planned state when no activity
// Test: renders completed state when activity matched
// Test: renders unplanned state for standalone activity
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run -t "WorkoutDetailPanel"`
Expected: FAIL (component doesn't exist)

- [ ] **Step 3: Implement WorkoutDetailPanel.tsx**

```typescript
import { useEffect } from 'react'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate, GarminActivity } from '../../api/types'
import { WorkoutDetailPlanned } from './WorkoutDetailPlanned'
import { WorkoutDetailCompleted } from './WorkoutDetailCompleted'
import { WorkoutDetailUnplanned } from './WorkoutDetailUnplanned'

interface WorkoutDetailPanelProps {
  workout?: ScheduledWorkoutWithActivity | null
  activity?: GarminActivity | null
  template?: WorkoutTemplate
  onClose: () => void
  onReschedule: (id: number, newDate: string) => void
  onRemove: (id: number) => void
  onUnpair: (scheduledId: number) => void
  onUpdateNotes: (id: number, notes: string) => void
  onNavigateToBuilder: (templateId: number) => void
}

export function WorkoutDetailPanel({
  workout, activity, template, onClose,
  onReschedule, onRemove, onUnpair, onUpdateNotes, onNavigateToBuilder,
}: WorkoutDetailPanelProps) {
  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Determine which state to show
  const isUnplannedOnly = !workout && activity
  const isCompleted = workout?.activity != null
  const isPlanned = workout != null && !isCompleted

  return (
    <>
      {/* Backdrop */}
      <div
        data-testid="panel-backdrop"
        onClick={onClose}
        style={{
          position: 'absolute', inset: 0,
          background: 'rgba(0,0,0,0.3)',
          zIndex: 20,
        }}
      />
      {/* Panel */}
      <div
        data-testid="workout-detail-panel"
        style={{
          position: 'absolute', right: 0, top: 0, bottom: 0,
          width: '380px', background: 'var(--bg-surface)',
          borderLeft: '1px solid var(--border)',
          zIndex: 21, overflowY: 'auto',
          animation: 'slideInRight 0.2s ease-out',
        }}
      >
        {isPlanned && (
          <WorkoutDetailPlanned
            workout={workout!}
            template={template}
            onClose={onClose}
            onReschedule={onReschedule}
            onRemove={onRemove}
            onUpdateNotes={onUpdateNotes}
            onNavigateToBuilder={onNavigateToBuilder}
          />
        )}
        {isCompleted && (
          <WorkoutDetailCompleted
            workout={workout!}
            template={template}
            onClose={onClose}
            onUnpair={onUnpair}
            onUpdateNotes={onUpdateNotes}
          />
        )}
        {isUnplannedOnly && (
          <WorkoutDetailUnplanned
            activity={activity!}
            onClose={onClose}
          />
        )}
      </div>
    </>
  )
}
```

- [ ] **Step 4: Add slide animation CSS**

Add to `frontend/src/index.css`:

```css
@keyframes slideInRight {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
```

- [ ] **Step 5: Run tests**

Run: `cd frontend && npm test -- --run -t "WorkoutDetailPanel"`
Expected: PASS (or partial — sub-components next)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/calendar/WorkoutDetailPanel.tsx frontend/src/tests/WorkoutDetailPanel.test.tsx frontend/src/index.css
git commit -m "feat: WorkoutDetailPanel shell — overlay, slide animation, close logic"
```

---

### Task 12: WorkoutDetailPlanned content

**Files:**
- Create: `frontend/src/components/calendar/WorkoutDetailPlanned.tsx`
- Modify: `frontend/src/tests/WorkoutDetailPanel.test.tsx`

- [ ] **Step 1: Write failing tests for planned state**

Add to `WorkoutDetailPanel.test.tsx`:

```typescript
// Test: planned state shows workout name and date
// Test: planned state shows planned duration and distance
// Test: planned state shows workout steps from template description
// Test: planned state shows sync status indicator
// Test: Reschedule button opens native date input (v1 simplification)
// Test: Edit in Builder button calls onNavigateToBuilder with template id
// Test: Remove button shows window.confirm() then calls onRemove (v1: window.confirm for simplicity)
// Test: Notes textarea shows existing notes value
// Test: Notes textarea calls onUpdateNotes on blur (flush)
```

- [ ] **Step 2: Run tests — verify RED**

Run: `cd frontend && npm test -- --run -t "planned"`
Expected: FAIL

- [ ] **Step 3: Implement WorkoutDetailPlanned.tsx**

Key implementation details:
- Use `computeDurationFromSteps` / `computeDistanceFromSteps` for fallback metrics
- Use `formatClock` / `formatKm` for display
- Zone stripe color from `zoneStripeColor(template?.sport_type)` (same logic as WorkoutCard)
- Sync status badge: same `syncStatusLabel` / `syncStatusClass` as WorkoutCard
- Reschedule: native `<input type="date">` (v1 simplification — matches spec "inline or popover")
- Remove: `window.confirm()` for v1 confirmation dialog (spec says "with confirmation")
- Notes: `<textarea>` with debounced onChange (500ms) + flush on blur + "Saved" indicator (brief CSS transition)
- `formatDateHeader` already exists in `frontend/src/utils/formatting.ts` (line 16-19)

```typescript
import { useState, useRef, useEffect, useCallback } from 'react'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate } from '../../api/types'
import { computeDurationFromSteps, computeDistanceFromSteps, formatClock, formatKm } from '../../utils/workoutStats'
import { formatDateHeader } from '../../utils/formatting'

interface WorkoutDetailPlannedProps {
  workout: ScheduledWorkoutWithActivity
  template: WorkoutTemplate | undefined
  onClose: () => void
  onReschedule: (id: number, newDate: string) => void
  onRemove: (id: number) => void
  onUpdateNotes: (id: number, notes: string) => void
  onNavigateToBuilder: (templateId: number) => void
}
```

- [ ] **Step 4: Run tests — verify GREEN**

Run: `cd frontend && npm test -- --run -t "planned"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/calendar/WorkoutDetailPlanned.tsx frontend/src/tests/WorkoutDetailPanel.test.tsx
git commit -m "feat: WorkoutDetailPlanned — planned workout panel content"
```

---

### Task 13: WorkoutDetailCompleted content

**Files:**
- Create: `frontend/src/components/calendar/WorkoutDetailCompleted.tsx`
- Modify: `frontend/src/tests/WorkoutDetailPanel.test.tsx`

- [ ] **Step 1: Write failing tests for completed state**

Add to `WorkoutDetailPanel.test.tsx`:

```typescript
// Test: completed state shows compliance badge with correct label (ON TARGET / CLOSE / OFF TARGET / COMPLETED)
// Test: completed state shows deviation percentage when available
// Test: completed state shows planned vs actual side-by-side
// Test: actual values colored by compliance color
// Test: activity details grid shows Avg Pace (formatPace), Avg HR, Max HR, Calories
// Test: Unpair button calls onUnpair with workout id
// Test: notes textarea works same as planned state
```

- [ ] **Step 2: Run tests — verify RED**

Run: `cd frontend && npm test -- --run -t "completed"`
Expected: FAIL

- [ ] **Step 3: Implement completed state component**

Key implementation details:
- Use `computeCompliance()` for stripe color + badge
- Badge label mapping: `on_target` → "ON TARGET", `close` → "CLOSE", `off_target` → "OFF TARGET", `completed_no_plan` → "COMPLETED"
- Deviation display: `${metric === 'duration' ? 'Duration' : 'Distance'} ${direction === 'over' ? '+' : '-'}${Math.abs(percentage! - 100)}%`
- Activity grid: Avg Pace (`formatPace` from `formatting.ts`), Avg HR, Max HR, Calories
- Planned vs Actual side-by-side cards

```typescript
import { useState, useRef, useEffect, useCallback } from 'react'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate } from '../../api/types'
import { computeCompliance } from '../../utils/compliance'
import { computeDurationFromSteps, computeDistanceFromSteps, formatClock, formatKm } from '../../utils/workoutStats'
import { formatPace, formatDateHeader } from '../../utils/formatting'

interface WorkoutDetailCompletedProps {
  workout: ScheduledWorkoutWithActivity
  template: WorkoutTemplate | undefined
  onClose: () => void
  onUnpair: (scheduledId: number) => void
  onUpdateNotes: (id: number, notes: string) => void
}
```

- [ ] **Step 4: Run tests — verify GREEN**

Run: `cd frontend && npm test -- --run -t "completed"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/calendar/WorkoutDetailCompleted.tsx frontend/src/tests/WorkoutDetailPanel.test.tsx
git commit -m "feat: WorkoutDetailCompleted — compliance comparison panel content"
```

---

### Task 14: WorkoutDetailUnplanned content

**Files:**
- Create: `frontend/src/components/calendar/WorkoutDetailUnplanned.tsx`
- Modify: `frontend/src/tests/WorkoutDetailPanel.test.tsx`

- [ ] **Step 1: Write failing tests for unplanned state**

Add to `WorkoutDetailPanel.test.tsx`:

```typescript
// Test: unplanned state shows "UNPLANNED" badge in grey
// Test: unplanned state shows activity name and date
// Test: unplanned state shows duration and distance
// Test: unplanned state shows activity details grid (pace, HR, calories)
// Test: unplanned state has no action buttons (no Reschedule, Remove, or Unpair)
// Test: unplanned state has no notes field
```

- [ ] **Step 2: Run tests — verify RED**

Run: `cd frontend && npm test -- --run -t "unplanned"`
Expected: FAIL

- [ ] **Step 3: Implement unplanned state component**

Shows: header, grey stripe, "UNPLANNED" badge, activity metrics (duration/distance), details grid (pace, HR, calories). Read-only — no actions, no notes.

```typescript
import type { GarminActivity } from '../../api/types'
import { formatClock, formatKm } from '../../utils/workoutStats'
import { formatPace, formatDateHeader } from '../../utils/formatting'

interface WorkoutDetailUnplannedProps {
  activity: GarminActivity
  onClose: () => void
}
```

- [ ] **Step 4: Run tests — verify GREEN**

Run: `cd frontend && npm test -- --run -t "unplanned"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/calendar/WorkoutDetailUnplanned.tsx frontend/src/tests/WorkoutDetailPanel.test.tsx
git commit -m "feat: WorkoutDetailUnplanned — unplanned activity panel content"
```

---

## Chunk 5: Frontend — CalendarPage integration + tests

### Task 15: CalendarPage — panel state management

**Files:**
- Modify: `frontend/src/pages/CalendarPage.tsx`

- [ ] **Step 1: Add panel state and render WorkoutDetailPanel**

Add state:

```typescript
const [selectedWorkout, setSelectedWorkout] = useState<ScheduledWorkoutWithActivity | null>(null)
const [selectedActivity, setSelectedActivity] = useState<GarminActivity | null>(null)
const isPanelOpen = selectedWorkout != null || selectedActivity != null
```

Add handlers:

```typescript
const handleWorkoutClick = (workout: ScheduledWorkoutWithActivity) => {
  setSelectedWorkout(workout)
  setSelectedActivity(null)
}

const handleActivityClick = (activity: GarminActivity) => {
  setSelectedActivity(activity)
  setSelectedWorkout(null)
}

const handlePanelClose = () => {
  setSelectedWorkout(null)
  setSelectedActivity(null)
}
```

Pass `onWorkoutClick` and `onActivityClick` to `CalendarView`.

Render `WorkoutDetailPanel` conditionally when `isPanelOpen`:

```tsx
{isPanelOpen && (
  <WorkoutDetailPanel
    workout={selectedWorkout}
    activity={selectedActivity}
    template={selectedWorkout ? templates.find(t => t.id === selectedWorkout.workout_template_id) : undefined}
    onClose={handlePanelClose}
    onReschedule={async (id, date) => { await reschedule(id, date); handlePanelClose(); }}
    onRemove={async (id) => { await remove(id); handlePanelClose(); }}
    onUnpair={async (id) => { await unpair(id); handlePanelClose(); }}
    onUpdateNotes={updateNotes}
    onNavigateToBuilder={(tid) => navigate(`/builder?id=${tid}`)}
  />
)}
```

Add `useNavigate` import (moved from WorkoutCard to CalendarPage). Add `reschedule`, `unpair`, `updateNotes` to the destructured `useCalendar` return.

- [ ] **Step 2: Run tests**

Run: `cd frontend && npm test -- --run`

- [ ] **Step 3: Fix any broken tests**

Update Calendar.test.tsx as needed for the new panel behavior.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/CalendarPage.tsx
git commit -m "feat: CalendarPage renders WorkoutDetailPanel on card click"
```

---

### Task 16: Final verification — all tests + TypeScript build

**Files:** (none new — verification only)

> Tests for each sub-component were written in Tasks 11-14 (TDD). This task is the final verification pass.

- [ ] **Step 1: Run full frontend test suite**

Run: `cd frontend && npm test -- --run`
Expected: All pass (including all WorkoutDetailPanel tests from Tasks 11-14)

- [ ] **Step 2: Run TypeScript build**

Run: `cd frontend && npm run build`
Expected: Clean build, no type errors

- [ ] **Step 3: Run backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All pass

---

### Task 17: Update STATUS.md — mark tasks complete

**Files:**
- Modify: `STATUS.md`

- [ ] **Step 1: Mark all panel tasks as ✅**

- [ ] **Step 2: Commit**

```bash
git add STATUS.md
git commit -m "docs: update STATUS.md — workout detail panel complete"
```
