# Calendar UX Improvements — Design Spec

**Date**: 2026-04-02
**Status**: Approved

---

## Overview

Two small, independent UX improvements to the Calendar page:

1. **Persist view preference** — remember the user's month/week toggle selection in `localStorage` so it survives page reloads.
2. **Search bar in WorkoutPicker** — add a name search input to the workout picker modal that opens when adding a workout from a calendar day card.

---

## Feature 1 — Persist Calendar View Preference

### Problem

`CalendarPage` initialises `view` as `useState<'week' | 'month'>('week')` every mount. Switching to month view and refreshing the page resets back to week view, which is friction for users who prefer month view.

### Scope

Desktop only. Mobile always uses the week/day view (`MobileCalendarDayView`) and has no toggle — this feature does not affect mobile behaviour.

### Design

**Storage key**: `'calendar_view_preference'`
**Values**: `'week'` | `'month'`
**Default**: `'week'` (if key absent or value unrecognised)

**State initialisation** (lazy initialiser so it reads storage only once on mount):
```ts
const [view, setView] = useState<'week' | 'month'>(
  () => (localStorage.getItem('calendar_view_preference') as 'week' | 'month') ?? 'week'
)
```

**On toggle** (inside the existing button `onClick`):
```ts
setView(v)
localStorage.setItem('calendar_view_preference', v)
```

### Files Changed

| File | Change |
|------|--------|
| `frontend/src/pages/CalendarPage.tsx` | Replace `useState` initialiser; add `localStorage.setItem` call in toggle handler |

### Edge Cases

- Unknown/corrupted value in storage → `?? 'week'` fallback
- Mobile renders `MobileCalendarDayView` regardless of `view` state → no impact

---

## Feature 2 — Search Bar in WorkoutPicker Modal

### Problem

`WorkoutPicker.tsx` (the modal shown when clicking "+ Add" on a calendar day card) renders all workout templates as a flat list with no way to filter. Users with many templates must scroll to find the one they want.

### Scope

`WorkoutPicker.tsx` only. The full `WorkoutLibrary` page already has search — this brings the same experience to the picker modal. Search is by name only (case-insensitive substring match), consistent with `WorkoutLibrary`.

### Design

**New state**: `const [search, setSearch] = useState('')`

**Input placement**: Top of the modal, above the template list. Full-width, auto-focused on open so keyboard users can type immediately.

**Filter logic** (same pattern as `WorkoutLibrary.tsx`):
```ts
const filtered = templates.filter(t =>
  t.name.toLowerCase().includes(search.toLowerCase())
)
```

**Empty state** (when `filtered.length === 0` and `search` is non-empty):
```
No workouts match your search
```
Displayed as a small centred message inside the list area.

**Implementation**: Use the standard HTML `autoFocus` attribute — React calls `.focus()` on mount.

**Styling**:
- Input uses CSS vars: `var(--input-bg)` background, `var(--text-primary)` text, `var(--input-border)` border — matches the existing `WorkoutLibrary` search input pattern
- Mobile: full-width, `min-height: 44px` for touch target (consciously larger than `WorkoutLibrary`'s desktop-only input, since the picker is modal-centric and a primary mobile interaction point)
- No debounce — list is short, filtering is synchronous

### Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/calendar/WorkoutPicker.tsx` | Add `search` state, search input element, filtered list, empty state message |

---

## Testing

1. **View preference**:
   - Toggle to month view → refresh page → should open in month view
   - Toggle back to week → refresh → should open in week view
   - Clear localStorage → refresh → should default to week view

2. **Search bar**:
   - Open picker on any calendar day → search input appears and is focused
   - Type part of a template name → list filters in real time
   - Type something with no match → empty state message shown
   - Clear input → full list restored
   - On mobile: picker opens, search input is full-width and tappable
