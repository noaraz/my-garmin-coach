# Completed Workout Description Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display the workout template description (e.g. `10m@Z1,25m@Z2`) on completed workouts across all surfaces — desktop calendar card, detail panel, mobile day view, and Today page.

**Architecture:** Four surgical changes to existing components. The template description data is already available in all four locations — no API changes, no new components, no new data fetching. The fix is purely presentational: remove the guard that hides the description on completion in `WorkoutCard`, and add the missing description block to the three components that never rendered it.

**Tech Stack:** React 18 + TypeScript, Vitest + React Testing Library (`frontend/src/tests/`), CSS custom properties, IBM Plex font families.

---

## Shared test fixtures

All four tasks use the same mock data. Define these once at the top of each new test file (or in a shared helper if one already exists in `frontend/src/tests/`):

```tsx
const template = {
  id: 42,
  name: 'Easy Run',
  description: '10m@Z1,25m@Z2,5m@Z1',
  steps: null,
  estimated_duration_sec: 2400,
  estimated_distance_m: null,
  sport_type: 'running',
  user_id: 1,
  created_at: '2026-03-01T00:00:00',
  updated_at: '2026-03-01T00:00:00',
  training_plan_id: null,
}

const activity = {
  id: 99,
  garmin_activity_id: 'abc123',
  name: 'Morning Run',
  sport_type: 'running',
  start_time: '2026-03-23T08:00:00',
  duration_sec: 2700,
  distance_m: 8000,
  avg_hr: 148,
  max_hr: 165,
  avg_pace_sec_per_km: 337,
  compliance: 'on_target' as const,
  user_id: 1,
}

const completedWorkout = {
  id: 1,
  date: '2026-03-23',
  workout_template_id: 42,
  training_plan_id: null,
  resolved_steps: null,
  garmin_workout_id: null,
  sync_status: 'synced' as const,
  completed: true,
  notes: null,
  created_at: '2026-03-23T00:00:00',
  updated_at: '2026-03-23T00:00:00',
  matched_activity_id: 99,
  activity,
}
```

---

## Chunk 1: Docs + WorkoutCard + WorkoutDetailPanel

### Task 0: Update STATUS.md

**Files:**
- Modify: `STATUS.md`

- [ ] **Step 1: Add entry to STATUS.md**

Add a line under the "In Progress" or appropriate section:
```
- Show description on completed workout cards (WorkoutCard, WorkoutDetailPanel, MobileCalendarDayView, TodayPage)
```

- [ ] **Step 2: Commit**

```bash
git add STATUS.md
git commit -m "docs: track completed-workout-description feature"
```

---

### Task 1: WorkoutCard — show description on completed workouts

**Files:**
- Modify: `frontend/src/components/calendar/WorkoutCard.tsx` (line 203)
- Modify: `frontend/src/tests/Calendar.test.tsx` (add tests to existing file)

#### Context

`WorkoutCard` renders the description as comma-split segments in IBM Plex Mono (lines 202–219). The current condition:
```tsx
{template?.description && !workout.activity && !compact && (
```
hides the description the moment a Garmin activity is matched. The fix: remove `!workout.activity`.

The `!compact` guard must stay — month view passes `compact={true}` and should stay description-free.

- [ ] **Step 1: Write two failing tests in `frontend/src/tests/Calendar.test.tsx`**

Open the existing `Calendar.test.tsx` and add these two tests (near other WorkoutCard tests if any, or at the end):

```tsx
describe('WorkoutCard description visibility', () => {
  it('test_description_completedWorkout_isVisible', () => {
    render(
      <MemoryRouter>
        <WorkoutCard
          workout={completedWorkout}
          template={template}
          onRemove={vi.fn()}
          compact={false}
        />
      </MemoryRouter>
    )
    // Description is split by comma — first segment should be present
    expect(screen.getByText('10m@Z1')).toBeInTheDocument()
  })

  it('test_description_compactMode_isHidden', () => {
    render(
      <MemoryRouter>
        <WorkoutCard
          workout={completedWorkout}
          template={template}
          onRemove={vi.fn()}
          compact={true}
        />
      </MemoryRouter>
    )
    expect(screen.queryByText('10m@Z1')).not.toBeInTheDocument()
  })
})
```

Add the mock data from the Shared fixtures section above at the top of the describe block or file scope.

- [ ] **Step 2: Run tests — expect FAIL on first, PASS on second**

```bash
cd frontend && npm test -- --run Calendar
```

Expected output:
```
✗ test_description_completedWorkout_isVisible   ← FAIL (element not found)
✓ test_description_compactMode_isHidden         ← PASS
```

- [ ] **Step 3: Remove the guard**

In `frontend/src/components/calendar/WorkoutCard.tsx` line 203, change:
```tsx
{template?.description && !workout.activity && !compact && (
```
to:
```tsx
{template?.description && !compact && (
```

- [ ] **Step 4: Run tests — expect both PASS**

```bash
cd frontend && npm test -- --run Calendar
```

Expected output:
```
✓ test_description_completedWorkout_isVisible
✓ test_description_compactMode_isHidden
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/calendar/WorkoutCard.tsx \
        frontend/src/tests/Calendar.test.tsx
git commit -m "feat: show description on completed workout cards"
```

---

### Task 2: WorkoutDetailPanel — add description to completed view

**Files:**
- Modify: `frontend/src/components/calendar/WorkoutDetailPanel.tsx` (~line 795)
- Modify: `frontend/src/tests/WorkoutDetailPanel.test.tsx` (add test to existing file)

#### Context

`WorkoutDetailPanel` has two internal components: `WorkoutDetailPlanned` and `WorkoutDetailCompleted`. The planned view already renders the description above the notes textarea (lines 370–382):

```tsx
{template?.description && (
  <div
    style={{
      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      fontSize: '12px',
      color: 'var(--text-secondary)',
      marginBottom: '6px',
      fontStyle: 'italic',
    }}
  >
    {template.description}
  </div>
)}
```

Add the identical block to `WorkoutDetailCompleted`'s Notes section, before the `<textarea>`. Find the Notes section in `WorkoutDetailCompleted` by searching for `placeholder="Add notes..."` — the `{template?.description && ...}` block goes immediately above the `<textarea>`.

- [ ] **Step 1: Write failing test in `frontend/src/tests/WorkoutDetailPanel.test.tsx`**

Open the existing file and add this test. Check the existing tests in this file to understand which context providers are needed (e.g. `GarminStatusProvider`, `ZonesStatusProvider`) — wrap accordingly:

```tsx
it('test_description_completedDetailPanel_isVisible', async () => {
  render(
    <MemoryRouter>
      <WorkoutDetailPanel
        workout={completedWorkout}
        activity={activity}
        template={template}
        onClose={vi.fn()}
        onRemove={vi.fn()}
        onNotesChange={vi.fn()}
      />
    </MemoryRouter>
  )
  // The full description string (not split by comma in the panel)
  expect(await screen.findByText('10m@Z1,25m@Z2,5m@Z1')).toBeInTheDocument()
})
```

Add mock data from Shared fixtures at the top of the describe block.

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd frontend && npm test -- --run WorkoutDetailPanel
```

Expected output:
```
✗ test_description_completedDetailPanel_isVisible   ← FAIL
```

- [ ] **Step 3: Add description block to WorkoutDetailCompleted**

In `WorkoutDetailPanel.tsx`, find the `WorkoutDetailCompleted` component. Search for `placeholder="Add notes..."` inside it. Add this block immediately before the `<textarea>`:

```tsx
{template?.description && (
  <div
    style={{
      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      fontSize: '12px',
      color: 'var(--text-secondary)',
      marginBottom: '6px',
      fontStyle: 'italic',
    }}
  >
    {template.description}
  </div>
)}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd frontend && npm test -- --run WorkoutDetailPanel
```

Expected output:
```
✓ test_description_completedDetailPanel_isVisible
```

- [ ] **Step 5: Run all tests — confirm no regressions**

```bash
cd frontend && npm test -- --run
```

Expected: all existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/calendar/WorkoutDetailPanel.tsx \
        frontend/src/tests/WorkoutDetailPanel.test.tsx
git commit -m "feat: show description in completed workout detail panel"
```

---

## Chunk 2: Mobile surfaces

### Task 3: MobileCalendarDayView — add description to mobile workout cards

**Files:**
- Modify: `frontend/src/components/calendar/MobileCalendarDayView.tsx` (~line 185)
- Create: `frontend/src/tests/MobileCalendarDayView.test.tsx`

#### Context

`MobileCalendarDayView` renders inline cards. Template is looked up early in the render:
```tsx
const template = templates.find(t => t.id === workout.workout_template_id)
```

The card shows planned stats (duration/distance), then actual activity stats if a Garmin activity exists. The description goes **between** these two blocks — after the planned stats closing `)}` and before the `{act && ...}` activity block.

Description block to insert:
```tsx
{template?.description && (
  <div style={{
    fontFamily: 'var(--font-family-mono)',
    fontSize: 11,
    color: 'var(--text-muted)',
    fontStyle: 'italic',
    marginBottom: 4,
  }}>
    {template.description}
  </div>
)}
```

- [ ] **Step 1: Check if MobileCalendarDayView test file exists**

```bash
ls frontend/src/tests/MobileCalendarDayView.test.tsx 2>/dev/null || echo "not found"
```

If not found, create it. If it exists, add to it.

- [ ] **Step 2: Write failing test**

Check the Props interface at the top of `MobileCalendarDayView.tsx` to match prop names exactly, then write:

```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import MobileCalendarDayView from '../components/calendar/MobileCalendarDayView'

// Add mock data from Shared fixtures here

describe('MobileCalendarDayView description visibility', () => {
  it('test_description_mobileCard_isVisible', () => {
    render(
      <MemoryRouter>
        <MobileCalendarDayView
          date="2026-03-23"
          workouts={[completedWorkout]}
          templates={[template]}
          unplannedActivities={[]}
          onWorkoutClick={vi.fn()}
          onActivityClick={vi.fn()}
          onRemove={vi.fn()}
        />
      </MemoryRouter>
    )
    expect(screen.getByText('10m@Z1,25m@Z2,5m@Z1')).toBeInTheDocument()
  })
})
```

Adjust prop names to match the actual component interface.

- [ ] **Step 3: Run test — expect FAIL**

```bash
cd frontend && npm test -- --run MobileCalendarDayView
```

Expected:
```
✗ test_description_mobileCard_isVisible   ← FAIL
```

- [ ] **Step 4: Add description block**

In `MobileCalendarDayView.tsx`, locate the planned stats block (look for `hasDuration`, `hasDistance`, `formatClock`). After its closing `)}`, before the activity stats block (look for `act &&`), insert the description block from the Context section above.

- [ ] **Step 5: Run test — expect PASS**

```bash
cd frontend && npm test -- --run MobileCalendarDayView
```

Expected:
```
✓ test_description_mobileCard_isVisible
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/calendar/MobileCalendarDayView.tsx \
        frontend/src/tests/MobileCalendarDayView.test.tsx
git commit -m "feat: show description on mobile workout cards"
```

---

### Task 4: TodayPage — add description to hero card

**Files:**
- Modify: `frontend/src/pages/TodayPage.tsx` (~line 141)
- Modify: `frontend/src/tests/TodayPage.test.tsx` (add test to existing file)

#### Context

The hero card (lines 128–158) shows:
1. "Today's Workout" label (mono, uppercase)
2. Workout name (display font, bold)
3. Duration (mono, muted) — div has `marginBottom: 10`
4. "View Details" button

Insert the description **between duration and button**. Because both duration and description have bottom margin, reduce duration's `marginBottom` from `10` to `4` when adding description:

```tsx
{/* Duration — change marginBottom: 10 → 4 */}
{todayDurationSec != null && (
  <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
    {formatClock(todayDurationSec)}
  </div>
)}
{/* Description — NEW */}
{todayTemplate?.description && (
  <div style={{
    fontFamily: 'var(--font-family-mono)',
    fontSize: 10,
    color: 'var(--text-muted)',
    fontStyle: 'italic',
    marginBottom: 10,
  }}>
    {todayTemplate.description}
  </div>
)}
```

If duration is null but description is present, the description div's `marginBottom: 10` provides the spacing before the button.

- [ ] **Step 1: Write failing test in `frontend/src/tests/TodayPage.test.tsx`**

Open the existing `TodayPage.test.tsx`. Check what API functions it mocks (look for `vi.mock('../api/client')`). Add a test that mocks the calendar fetch to return a workout for today and checks the description appears:

```tsx
it('test_description_todayHeroCard_isVisible', async () => {
  const today = new Date().toISOString().split('T')[0]
  // Override the mock for this test to return a workout scheduled today
  mockFetchCalendarRange.mockResolvedValue({
    workouts: [{ ...completedWorkout, date: today }],
    unplanned_activities: [],
  })
  mockFetchWorkoutTemplates.mockResolvedValue([template])

  render(<MemoryRouter><TodayPage /></MemoryRouter>)
  expect(await screen.findByText('10m@Z1,25m@Z2,5m@Z1')).toBeInTheDocument()
})
```

Check the existing mock setup pattern in the file (it likely uses `vi.hoisted` — follow the same pattern).

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd frontend && npm test -- --run TodayPage
```

Expected:
```
✗ test_description_todayHeroCard_isVisible   ← FAIL
```

- [ ] **Step 3: Add description block and adjust duration margin**

In `TodayPage.tsx`, find the duration div (`marginBottom: 10`) inside the hero card. Change its `marginBottom` to `4`, then add the description block immediately after it (before the button).

- [ ] **Step 4: Run test — expect PASS**

```bash
cd frontend && npm test -- --run TodayPage
```

Expected:
```
✓ test_description_todayHeroCard_isVisible
```

- [ ] **Step 5: Run full test suite — confirm no regressions**

```bash
cd frontend && npm test -- --run
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/TodayPage.tsx \
        frontend/src/tests/TodayPage.test.tsx
git commit -m "feat: show description in Today page hero card"
```
