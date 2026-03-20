# Workout Detail Panel — Design Spec

**Date:** 2026-03-20
**Status:** Draft

## Problem

Clicking a workout card on the calendar navigates to the Workout Builder page. This breaks the calendar flow — users lose context and can't quickly review workout details, see completion data, or manage scheduling. Unplanned activity cards have no click action at all.

## Goal

Replace the navigate-to-builder behavior with a TrainingPeaks-style slide-out Quick View panel. Clicking any card opens a right-side panel showing workout details, completion status, and contextual actions — without leaving the calendar.

---

## 1. Panel Behavior

- **Trigger**: Click on any `WorkoutCard` or `UnplannedActivityCard` in the calendar (week or month view)
- **Position**: Slide-out panel from the right edge, overlaying the calendar
- **Width**: ~380px fixed
- **Close**: Click X button, click outside the panel, or press Escape
- **Transition**: Slide in from right with subtle animation (~200ms ease-out)
- **Backdrop**: Semi-transparent overlay on the calendar area

### What changes in existing code

- `WorkoutCard.handleCardClick()` currently calls `navigate(/builder?id=...)` — replace with `onCardClick(workout)` callback prop
- `UnplannedActivityCard` currently has no click handler — add `onCardClick(activity)` callback prop
- Both `MonthView` and `WeekView` must thread `onCardClick` callbacks through to card components
- `CalendarPage` manages panel open/close state and renders the panel component
- All data needed for the panel is already loaded in `CalendarPage` state (from `CalendarResponse`) — no async fetching needed when opening the panel

---

## 2. Panel States

### State 1: Planned Workout (No Activity)

A scheduled workout that hasn't been completed yet.

**Header:**
- Workout name (from template) — `IBM Plex Sans Condensed`, 18px, bold, white
- Date — 12px, muted
- Close button (X) top-right

**Zone stripe:** 3px horizontal bar in zone color (same logic as card stripe)

**Planned metrics:**
- Duration (clock format) + Distance (km) — `IBM Plex Mono`, 20px, bold

**Workout steps:**
- Dark card showing the template description/steps in mono font
- Label: "WORKOUT STEPS"

**Sync status:**
- Green checkmark "Synced to Garmin" / pending / failed indicator

**Actions (stacked buttons):**
- Reschedule — opens a date picker inline or as a small popover
- Edit in Builder — navigates to `/builder?id={template_id}` (leaves calendar)
- Remove from Calendar — deletes the scheduled workout (with confirmation)

**Notes:**
- Editable text area, persisted to backend (new `notes` field on ScheduledWorkout)

### State 2: Completed Workout (Activity Matched)

A scheduled workout that has been matched with a Garmin activity.

**Header:** Same as State 1 (workout name + date + close)

**Compliance stripe:** 3px bar colored by compliance result (green/yellow/red)

**Compliance badge:**
- Maps from `ComplianceLevel` (see `compliance.ts`):

| Level | Badge Label | Color |
|-------|-------------|-------|
| `on_target` | ON TARGET | `--color-compliance-green` |
| `close` | CLOSE | `--color-compliance-yellow` |
| `off_target` | OFF TARGET | `--color-compliance-red` |
| `completed_no_plan` | COMPLETED | `--color-compliance-green` |

- Shows deviation when `percentage` is available: `{metric === 'duration' ? 'Duration' : 'Distance'} {direction === 'over' ? '+' : '-'}${Math.abs(percentage - 100)}%`
- `completed_no_plan` shows no deviation (no usable planned values to compare)
- `missed` and `unplanned` levels don't appear in State 2 (activity exists)

**Planned vs Actual comparison:**
- Side-by-side cards: Planned (duration + distance) | Actual (duration + distance)
- Actual values colored by compliance

**Activity details:**
- Grid: Avg Pace, Avg HR, Max HR, Calories
- `IBM Plex Mono`, 13px

**Actions:**
- Unpair Activity — removes the match, activity becomes unplanned grey card on same date

**Notes:** Same editable field

### State 3: Unplanned Activity (No Scheduled Workout)

A Garmin activity that wasn't matched to any planned workout.

**Header:**
- Activity name (from Garmin) + date + close

**Grey stripe:** 3px bar in `--color-compliance-grey`

**Unplanned badge:**
- "UNPLANNED" in grey

**Activity metrics:**
- Duration + Distance — 20px bold
- Grid: Avg Pace, Avg HR, Max HR, Calories

**Notes:** Same editable field

**No special actions** — this is a read-only view of the Garmin data.

---

## 3. Data Requirements

### Existing data (no backend changes needed for display)

- `ScheduledWorkoutWithActivity` already includes `activity: GarminActivity | null`
- `GarminActivity` has: `duration_sec`, `distance_m`, `avg_hr`, `max_hr`, `avg_speed`, `calories`, `name`, `date`
- `WorkoutTemplate` has: `name`, `description`, `steps`, `estimated_duration_sec`, `estimated_distance_m`
- Compliance calculation: `computeCompliance()` in `frontend/src/utils/compliance.ts`

### New: Notes field

- Add `notes: str | None` column to `ScheduledWorkout` table (alembic migration)
- Backend changes needed:
  - Extend `RescheduleUpdate` schema (or create new `ScheduledWorkoutUpdate`) with `date: date | None` and `notes: str | None`
  - Update service layer to handle partial updates (only update fields that are provided)
  - Update `PATCH /api/v1/calendar/{id}` handler to pass notes to service
- Notes save behavior: debounce 500ms on input change, flush immediately on blur. Show subtle "Saved" indicator after successful persist.
- For unplanned activities: notes are NOT persisted (no backend table change for GarminActivity notes in v1)

### Pace display

- Need `formatPace(paceSecPerKm: number)` utility — format seconds-per-km to `MM:SS /km`
- Data model stores `avg_pace_sec_per_km` (not `avg_speed`) — already in the `GarminActivity` type
- Example: `360` → `6:00 /km`

---

## 4. Component Structure

```
frontend/src/components/calendar/
  WorkoutDetailPanel.tsx       — main panel shell (overlay, slide animation, close logic)
  WorkoutDetailPlanned.tsx     — State 1 content
  WorkoutDetailCompleted.tsx   — State 2 content
  WorkoutDetailUnplanned.tsx   — State 3 content
```

### Props

```typescript
interface WorkoutDetailPanelProps {
  // Either a scheduled workout or an unplanned activity — one must be set
  workout?: ScheduledWorkoutWithActivity
  activity?: GarminActivity
  template?: WorkoutTemplate
  onClose: () => void
  onReschedule: (id: number, newDate: string) => void
  onRemove: (id: number) => void
  onUnpair: (scheduledId: number) => void
  onNavigateToBuilder: (templateId: number) => void
}
```

### State management in CalendarPage

```typescript
const [selectedWorkout, setSelectedWorkout] = useState<ScheduledWorkoutWithActivity | null>(null)
const [selectedActivity, setSelectedActivity] = useState<GarminActivity | null>(null)
const isPanelOpen = selectedWorkout != null || selectedActivity != null
```

---

## 5. Interactions

| Action | Behavior |
|--------|----------|
| Click workout card | Open panel in State 1 or 2 (depending on `activity` presence) |
| Click unplanned card | Open panel in State 3 |
| Click X or outside | Close panel |
| Press Escape | Close panel |
| Reschedule | Date picker → calls `reschedule(id, newDate)` → panel updates |
| Edit in Builder | `navigate(/builder?id=...)` — leaves calendar |
| Remove | Confirmation dialog → `remove(id)` → panel closes |
| Unpair | `unpair(scheduledId)` → workout reverts to State 1, activity becomes grey card |
| Edit notes | Debounced save to backend on blur/change |

---

## 6. Styling

- Panel background: `var(--bg-surface)`
- Uses existing CSS custom properties — no hardcoded hex values
- Font families follow project convention: Condensed for headers, Mono for numbers, Sans for body
- Responsive: panel overlays full-width on mobile (future), fixed 380px on desktop
- Z-index above calendar grid but below modals

---

## 7. Neon Free Tier Considerations

- **Panel open = zero DB queries.** All data is already loaded in CalendarPage state from the initial `CalendarResponse` fetch. Opening the panel is purely frontend.
- **Notes save:** Single-row `UPDATE scheduledworkout SET notes = ? WHERE id = ?` — minimal cost. The 500ms debounce + flush-on-blur ensures at most 1 query per user edit pause, not per keystroke.
- **Reschedule/Remove/Unpair:** These reuse existing endpoints — no new query patterns introduced.
- **No new N+1 risk:** The panel doesn't fetch additional data on open. Template lookup is done in-memory from the already-loaded `templates` array.

---

## 8. Out of Scope (v1)

- Inline step editing (use Builder for that)
- Charts or pace/HR graphs
- Split/lap analysis
- Pairing UI (drag activity onto workout) — pair/unpair is API-only for now
- Notes on unplanned activities (no DB column in v1)
- Mobile responsive panel width
