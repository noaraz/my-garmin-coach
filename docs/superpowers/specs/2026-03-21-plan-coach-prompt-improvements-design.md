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

- **Position:** after the Long run day select, before the fetch button and generated prompt block
- **Label:** `CURRENT HEALTH & SHAPE` (uppercase, `fieldLabel` style)
- **Placeholder:** `E.g. good base fitness, returning from injury, peak week fatigue, feeling strong…`
- **Rows:** 3, full width
- **Style:** `inputStyle` with `fontFamily` overridden to `'IBM Plex Sans', system-ui, sans-serif` (not Mono — this is free prose, not structured data), plus `width: '100%'` and `resize: 'vertical'`. All other tokens from `inputStyle` apply.
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

**Style:** use the same inline style pattern as the existing day-toggle buttons — `IBM Plex Sans Condensed`, uppercase, `var(--border)` border, `var(--bg-surface-2)` background, `var(--text-secondary)` color. Disabled (`fetching`) state: `opacity: 0.5, cursor: 'not-allowed'`. No hardcoded hex values. The fetch button has no success/error color states — do not use `--color-success` or `--color-error` here; those are only on the copy button.

**`done` and `empty` feedback placement:** the count badge / "No recent activities found" note is rendered as a `<span>` inline sibling immediately to the right of the button (same flex row), using `var(--text-muted)` and `fontSize: '12px'`. Not a separate block element. Badge copy: `"1 activity included"` (singular) / `"N activities included"` (plural) — same pluralisation logic as the existing summary block.

**Re-fetch state machine:** clicking "Refresh" (`done`) or "Retry" (`empty`) always transitions to `'fetching'` first (button disabled), then to `'done'` or `'empty'` on completion. `activities` is **not** cleared on re-fetch or on error — old activities remain in the prompt until the new fetch completes. On catch, only `fetchState` changes to `'empty'`; `activities` is left as-is.

### 1c. Remove auto-fetch `useEffect` and old summary block

Three deletions:
1. The `useEffect` that fires on mount and calls `fetchCalendarRange` — deleted entirely.
2. Remove `useEffect` from the React import (`import { useState, useRef, useEffect }` → `import { useState, useRef }`). Without this, `tsc -b` fails with an unused-import error.
3. The existing "Recent training included in prompt" summary JSX block (currently rendered below the Long run day select when `recentActivities.length > 0`) — deleted entirely. Its role is replaced by the fetch button's `done`/`empty` state feedback.

`recentActivities` state is renamed to `activities`; all JSX references to `recentActivities` are updated accordingly.

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

- `weeksLabel`, `weeksNote`, and their local `const weeks = weeksUntil(raceDate)` line removed from `buildPrompt()`. The `weeksUntil()` helper function at module level is no longer called — **delete it** to keep the file clean.
- Race date still appears as goal context: `My goal: [distance] race on [date]` — the old `${weeksNote}` interpolation at the end of this line is removed.
- New line after goal: `Plan the next 2–3 weeks only — I'll come back to update it regularly.`

### 2b. Health & shape section

Injected **after the training days/long run lines and before the `activitySection`**, only when `healthNotes.trim()` is non-empty. Full prompt order:

```
Generate the next 2–3 weeks of my running training plan as a CSV with these columns:
date,name,steps_spec,sport_type,description

My goal: [distance] race on [date]
Plan the next 2–3 weeks only — I'll come back to update it regularly.
Training: Nx/week on [days]
Long run day: [day]
My current health & shape: [healthNotes]   ← new, only when non-empty

## Recent Training (last 14 days)           ← only when activities fetched
- 2026-03-20 running 45min 8.2km avg 5:29/km
...

Rules: ...
Step notation: ...
Example rows: ...

Note: plan 2–3 weeks only, not the full race block. I'll re-run this prompt every 2–3 weeks to keep the plan current.   ← new

Output as a downloadable file named training_plan.csv — no explanation, no markdown fences.
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
