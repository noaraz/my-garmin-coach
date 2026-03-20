# Status Indicators — Feature Plan

Design spec: `docs/superpowers/specs/2026-03-20-garmin-status-indicator-design.md`
Implementation plan: `docs/superpowers/plans/2026-03-20-garmin-status-indicators.md`

---

## Overview

Two always-visible status indicators driven by React contexts fetched on AppShell mount:

1. **Garmin connection status** — dedicated row in sidebar below Settings nav item; text button in calendar toolbar left of Sync All. Green = connected, red = not connected. Clickable → `/settings`.
2. **Zones "Not set" warning** — inline amber dot + label on the Zones NavLink when `threshold_pace === null`. Hidden once configured. Clickable → `/zones`.

---

## Phase 1 — Docs ⬜

- [ ] Update STATUS.md + root CLAUDE.md
- [ ] Create this PLAN.md + CLAUDE.md

---

## Phase 2 — Contexts ⬜

### New files

| File | Exports |
|------|---------|
| `frontend/src/contexts/GarminStatusContext.tsx` | `GarminStatusProvider`, `useGarminStatus` |
| `frontend/src/contexts/ZonesStatusContext.tsx` | `ZonesStatusProvider`, `useZonesStatus` |

Both contexts: fetch on mount, `null` while loading/error, `refresh()` / `refreshZones()` re-fetches.

---

## Phase 3 — UI ⬜

### Modified files

| File | Change |
|------|--------|
| `frontend/src/components/layout/AppShell.tsx` | Wrap with `<GarminStatusProvider><ZonesStatusProvider>` |
| `frontend/src/components/layout/Sidebar.tsx` | Garmin status `<button>` row + Zones inline amber indicator |
| `frontend/src/pages/CalendarPage.tsx` | Toolbar Garmin button; consume context; migrate auto-sync effect |
| `frontend/src/pages/SettingsPage.tsx` | Call `refresh()` after connect + disconnect |
| `frontend/src/components/zones/ZoneManager.tsx` | Call `refreshZones()` after successful save |

---

## Phase 4 — Tests ⬜

| Test file | New cases |
|-----------|-----------|
| `frontend/src/tests/Sidebar.test.tsx` | Garmin connected/not-connected labels; click→navigate; Zones "Not set"; Zones configured (no label); loading (no label) |
| `frontend/src/tests/Calendar.test.tsx` | Toolbar button present/absent; click→navigate |
