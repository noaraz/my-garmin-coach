# Garmin Status Indicator — Design Spec

**Date:** 2026-03-20
**Feature:** Garmin connection status indicator in sidebar and calendar toolbar

---

## Overview

Show a live Garmin connection status indicator in two places:

1. **Sidebar** — a dedicated "Garmin" row below the Settings nav item, visible on every page
2. **Calendar toolbar** — a minimal text button to the left of Sync All, visible on the calendar page

Both are clickable and navigate to `/settings` so the user can connect or disconnect.

---

## Visual Design

### Sidebar row

- Same padding, font size, font weight, letter-spacing, and border-radius as other nav items (`7px 10px`, `12px`, `600`, `0.1em`, `5px`)
- Layout: `[dot] Garmin [status label]`
- Status label right-aligned (`margin-left: auto`)
- Connected: green dot (`var(--color-success)` / `#22c55e`) + "Connected" label in green
- Not connected: red dot (`var(--color-error)` / `#ef4444`) + "Not connected" label in red
- Hover: `rgba(255,255,255,0.05)` background (same as inactive nav hover)
- Loading (null state): row hidden — no dot rendered until status resolves

### Calendar toolbar button

- Text-only button, no border, no background
- Layout: `[dot] Garmin` — no status label (space is tight)
- Same `27px` height as Sync All; `font-size: 10px`, `font-weight: 700`, `letter-spacing: 0.1em`, uppercase
- Connected: green dot, text color `var(--text-muted)` / `#6a6a78`
- Not connected: red dot, text color `var(--text-muted)` / `#6a6a78`
- Loading (null state): button hidden

---

## Architecture

### New: `GarminStatusContext`

```
frontend/src/contexts/GarminStatusContext.tsx
```

- Fetches `getGarminStatus()` once on mount
- Exposes `{ garminConnected: boolean | null }` — `null` = loading
- Wraps `<App>` in `App.tsx` (inside `AuthProvider`, outside route rendering)

### Modified: `Sidebar.tsx`

- Consumes `useGarminStatus()`
- Renders the Garmin nav row below the Settings `<NavLink>` when `garminConnected !== null`
- Clicking calls `navigate('/settings')`

### Modified: `CalendarPage.tsx`

- Consumes `useGarminStatus()` — drops its own `getGarminStatus()` call (currently in the auto-sync `useEffect`)
- The auto-sync effect checks `garminConnected` from context instead of fetching
- Renders the toolbar text button when `garminConnected !== null`
- Clicking calls `navigate('/settings')`

---

## Data Flow

```
App mount
  → GarminStatusContext fetches getGarminStatus()
  → sets garminConnected: boolean

Sidebar (any page)
  ← reads garminConnected from context
  → renders dot + label row

CalendarPage
  ← reads garminConnected from context
  → renders toolbar dot button
  → auto-sync useEffect reads garminConnected (no extra fetch)
```

---

## Loading State

- While `garminConnected === null`: both the sidebar row and toolbar button are hidden
- No spinner or skeleton — the absence is invisible and resolves quickly (single fast API call)

---

## CSS Tokens Used

| Token | Usage |
|-------|-------|
| `--color-success` | Connected dot + label color |
| `--color-error` | Disconnected dot + label color |
| `var(--text-muted)` | Toolbar button text |

Sidebar uses its own hardcoded dark palette (existing pattern — sidebar never uses theme tokens).

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/contexts/GarminStatusContext.tsx` | **New** — context + hook |
| `frontend/src/App.tsx` | Wrap app in `<GarminStatusProvider>` |
| `frontend/src/components/layout/Sidebar.tsx` | Add Garmin status row |
| `frontend/src/pages/CalendarPage.tsx` | Add toolbar button; consume context |

---

## Tests

| File | Tests |
|------|-------|
| `frontend/src/tests/Sidebar.test.tsx` | Connected state shows green row; disconnected shows red row; loading hides row; clicking navigates to /settings |
| `frontend/src/tests/Calendar.test.tsx` | Connected shows toolbar button; disconnected shows red dot; loading hides button; clicking navigates to /settings |

---

## Out of Scope

- Polling / live refresh of Garmin status (single fetch on mount is sufficient)
- Toast or notification when Garmin disconnects mid-session
- Status indicator on pages other than the sidebar (sidebar covers all pages)
