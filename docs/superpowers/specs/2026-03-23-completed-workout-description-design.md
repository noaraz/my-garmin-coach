# Design: Show Description on Completed Workout Cards

**Date:** 2026-03-23
**Status:** Approved

---

## Problem

After a workout is completed (matched to a Garmin activity), the template description (e.g. `10m@Z1,25m@Z2`) disappears from multiple surfaces:

1. **WorkoutCard** (week/day desktop view) — an explicit `!workout.activity` guard hides it once a Garmin activity is linked.
2. **WorkoutDetailPanel (completed view)** — `WorkoutDetailCompleted` receives `template` with description data but never renders it.
3. **MobileCalendarDayView** — description is never rendered, completed or not.
4. **TodayPage hero card** — description is never rendered.

The description is useful context regardless of completion status — it tells the athlete what kind of workout it was.

---

## Scope

Four surgical changes to existing components. No new components, no API changes, no data model changes, no new fetches. Template data is already available in all locations.

**Not in scope:** The "yesterday" card in `TodayPage` — it's intentionally minimal and links to the detail panel for full info.

---

## Changes

### 1. `frontend/src/components/calendar/WorkoutCard.tsx`

Remove the `!workout.activity` guard from the description render condition:

```tsx
// Before
{template?.description && !workout.activity && !compact && (

// After
{template?.description && !compact && (
```

The description shows on completed cards in the same position and style as planned cards. The `!compact` guard is preserved — description stays hidden on month view.

---

### 2. `frontend/src/components/WorkoutDetailPanel.tsx` — `WorkoutDetailCompleted`

Add description rendering in the completed view, using the same italic style as `WorkoutDetailPlanned`:

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

Placement: near the top of `WorkoutDetailCompleted`, above the notes section — consistent with the planned view layout.

---

### 3. `frontend/src/components/MobileCalendarDayView.tsx`

Add description rendering after the planned stats block and before the actual activity stats block:

```tsx
{template?.description && (
  <div
    style={{
      fontSize: '11px',
      color: 'var(--text-muted)',
      fontStyle: 'italic',
      marginTop: '2px',
    }}
  >
    {template.description}
  </div>
)}
```

Placement: after duration/distance planned stats (around line 185), before the activity metrics block (around line 188). Template is already looked up on line 133 via `templates.find(...)`.

---

### 4. `frontend/src/pages/TodayPage.tsx` — Hero Card

Add description after the duration line, before the "View Details" button:

```tsx
{todayTemplate?.description && (
  <div
    style={{
      fontSize: '12px',
      color: 'var(--text-secondary)',
      fontStyle: 'italic',
      marginBottom: '4px',
    }}
  >
    {todayTemplate.description}
  </div>
)}
```

`todayTemplate` is already available in scope.

---

## What Does Not Change

- Month view cards — `compact` guard preserved, description stays hidden.
- Yesterday card in `TodayPage` — intentionally minimal.
- `UnplannedActivityCard` — no template, no description to show.
- All API calls, data fetching, types, and data models.
- The `template?.description` null-guard — if there's no description, nothing renders.

---

## Testing

- **Desktop week/day view**: Completed workout card shows description.
- **Detail panel**: Clicking a completed workout shows description above notes.
- **Month view**: Cards remain compact with no description.
- **Mobile day view**: Workout card shows description (between planned stats and activity stats).
- **TodayPage**: Hero card shows description below duration, above "View Details".
- **Planned (not completed) workouts**: Unaffected.
- **Unplanned activities**: Unaffected.
