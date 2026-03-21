# Plan Coach Prompt Improvements — Design Spec

**Date:** 2026-03-21
**Feature:** Plan Coach — PlanPromptBuilder enhancements
**Files changed:** `frontend/src/components/plan-coach/PlanPromptBuilder.tsx` only

---

## Overview

Three incremental improvements to `PlanPromptBuilder.tsx` to make the generated prompt more useful:

1. **Health & shape field** — free-text input injected into the prompt
2. **On-demand activity fetch** — replace silent auto-fetch with an explicit button
3. **2–3 week planning horizon** — shift the prompt from full race-block to rolling 2–3 week chunks with re-run guidance

---

## Section 1: Form Changes

### 1a. Health & shape textarea

- **Position:** after the Long run day select, before the generated prompt block
- **Label:** `CURRENT HEALTH & SHAPE` (uppercase, `fieldLabel` style)
- **Placeholder:** `E.g. good base fitness, returning from injury, peak week fatigue, feeling strong…`
- **Rows:** 3, full width
- **Optional:** empty value → section omitted from prompt entirely

### 1b. Fetch last 2 weeks button

Replaces the existing `useEffect` auto-fetch. Positioned above the generated prompt, below the health field.

Button states driven by `fetchState: 'idle' | 'fetching' | 'done' | 'empty'`:

| State | Label | Notes |
|-------|-------|-------|
| `idle` | "Fetch last 2 weeks of training" | Default on page load |
| `fetching` | "Fetching…" | Button disabled |
| `done` | "Refresh" + badge "N activities included" | Re-clickable |
| `empty` | "Retry" + note "No recent activities found" | Garmin not connected or no data |

Fetch errors are swallowed silently (same behaviour as the existing catch); `fetchState` → `'empty'`.

### 1c. Remove auto-fetch `useEffect`

The `useEffect` that fires on mount and calls `fetchCalendarRange` is deleted. `activities` state initialises to `[]`.

---

## Section 2: Prompt Changes (`buildPrompt()`)

### Signature change

```typescript
function buildPrompt(
  distance: string,
  raceDate: string,
  days: string[],
  longRunDay: string,
  activities: GarminActivity[],
  healthNotes: string,   // new param
): string
```

### 2a. Planning horizon

Old header:
```
Generate a ${weeksLabel} running training plan as a CSV with these columns:
```

New header:
```
Generate the next 2–3 weeks of my running training plan as a CSV with these columns:
```

- `weeksLabel` and `weeksNote` variables removed from `buildPrompt()`
- Race date still appears as goal context: `My goal: [distance] race on [date]`
- New line after goal: `Plan the next 2–3 weeks only — I'll come back to update it regularly.`

### 2b. Health & shape section

Injected after the training days/long run block, only when `healthNotes.trim()` is non-empty:

```
My current health & shape: [healthNotes]
```

### 2c. Re-run note

Added at the bottom of the prompt, before the output instruction line:

```
Note: plan 2–3 weeks only, not the full race block. I'll re-run this prompt every 2–3 weeks to keep the plan current.
```

### 2d. Activity section label

Changed from `## Recent Training (last 30 days)` → `## Recent Training (last 14 days)` to match the new 2-week fetch window.

---

## Section 3: State & Component Structure

### New / changed state

```typescript
const [healthNotes, setHealthNotes] = useState('')
const [activities, setActivities] = useState<GarminActivity[]>([])   // was recentActivities
const [fetchState, setFetchState] = useState<'idle' | 'fetching' | 'done' | 'empty'>('idle')
```

`copyState` and all other state is unchanged.

### Fetch handler

```typescript
async function handleFetchActivities() {
  setFetchState('fetching')
  try {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 14)   // 14 days, not 30
    const data = await fetchCalendarRange(toDateString(start), toDateString(end))
    const matched = data.workouts.filter(w => w.activity !== null).map(w => w.activity as GarminActivity)
    const all = [...matched, ...data.unplanned_activities].sort((a, b) => b.date.localeCompare(a.date))
    setActivities(all)
    setFetchState(all.length > 0 ? 'done' : 'empty')
  } catch {
    setFetchState('empty')
  }
}
```

### Prompt wiring

```typescript
const prompt = buildPrompt(distance, raceDate, selectedDays, longRunDay, activities, healthNotes)
```

---

## What Does Not Change

- `CsvImportTab.tsx` — no changes
- `PlanCoachPage.tsx` — no changes
- Backend (`plan_coach_service.py`, `plans.py` router) — no changes
- ChatTab — no changes (hidden/disabled; health notes can be added there separately when re-enabled)
- All existing tests — no changes needed; `PlanPromptBuilder` has no RTL tests currently

---

## Testing

`PlanPromptBuilder` currently has no RTL tests. No new tests are required by this change (all logic is pure string building in `buildPrompt()`; the component is a simple form). Manual verification: fill form, click fetch button, confirm activities appear in prompt, confirm health notes appear, confirm prompt says "2–3 weeks".
