# Status Indicators — Design Spec

**Date:** 2026-03-20
**Feature:** Garmin connection status + zones configuration status indicators

---

## Overview

Two status indicators added to the sidebar (and Garmin also in the calendar toolbar):

1. **Garmin status** — dedicated row below Settings nav item; also a text button in the calendar toolbar. Shows connected (green) / not connected (red). Clickable → `/settings`.
2. **Zones status** — inline warning on the Zones nav item itself. Shows amber dot + "Not set" when `threshold_pace` is null. Hidden once configured. Clickable → `/zones` (already a NavLink).

---

## Visual Design

### Sidebar row

- Same padding, font size, font weight, letter-spacing, and border-radius as other nav items (`7px 10px`, `12px`, `600`, `0.1em`, `5px`)
- Layout: `[dot] Garmin [status label]`
- Status label right-aligned (`margin-left: auto`)
- Connected: green dot (`SIDE_GARMIN_CONNECTED = '#22c55e'`) + "Connected" label in same color
- Not connected: red dot (`SIDE_GARMIN_DISCONNECTED = '#ef4444'`) + "Not connected" label in same color
- Dot glow: `box-shadow: 0 0 0 2px rgba(34,197,94,0.2)` (connected) / `rgba(239,68,68,0.2)` (disconnected)
- Add both as named constants at the top of `Sidebar.tsx` alongside the existing `SIDE_BG`, `SIDE_BORD`, etc.
- Hover background `rgba(255,255,255,0.05)`: implement with local `const [hovered, setHovered] = useState(false)` and `onMouseEnter`/`onMouseLeave` handlers
- Dot size: `7px × 7px` (matching the dot in `SettingsPage`)
- Gap between dot and label text: `9px` (matching existing nav items)
- Loading (`null` state): row not rendered; also briefly hidden during `refresh()` re-fetch (dot disappears and reappears — accepted UX)
- On error from `getGarminStatus()`: context stays `null`, row stays hidden
- Accessibility: use `<button>` element (not a `<div>`) with `aria-label="Garmin: Connected – go to Settings"` (or "Not connected" variant)

### Calendar toolbar button

- Text-only `<button>`, `border: 'none'`, `background: 'transparent'`
- Positioned **inside the existing `<div style={{ marginLeft: 'auto' }}>` group** that wraps Sync All — Garmin button sits immediately to the left of Sync All within that div
- Layout: `[dot] Garmin` — no status label; `gap: '6px'` between dot and text
- Dot size: `7px × 7px` with glow (same as sidebar)
- Same `27px` height as Sync All; `font-size: 10px`, `font-weight: 700`, `letter-spacing: 0.1em`, uppercase, `font-family: IBM Plex Sans Condensed`
- Color: `var(--text-muted)` for text; dot uses same green/red hex values as sidebar
- Loading (`null` state): button not rendered
- Clicking navigates to `/settings`

### Active state on /settings

The Garmin sidebar row is intentionally **not** a `<NavLink>` — it represents connection status, not a page. It has no active styling when the user is on `/settings`.

---

## Zones Status Indicator

### Visual design

The existing Zones `<NavLink>` in the sidebar gains an inline amber dot + "Not set" label when `threshold_pace === null`:

```
〰 Zones                     ← normal (configured)
〰 Zones  ● Not set          ← warning (threshold_pace is null)
```

- Amber dot: `SIDE_ZONES_WARN = '#f59e0b'`, `7px × 7px`, `box-shadow: 0 0 0 2px rgba(245,158,11,0.2)`
- "Not set" label: same amber color, `9px`, `700` weight, `0.06em` letter-spacing, `margin-left: auto` on the dot group
- The dot + label sit inside the existing NavLink render-prop span, after the "Zones" text
- Loading (`null` state): no indicator rendered
- On error from `fetchProfile()`: state stays `null`, no indicator
- Configured state (`threshold_pace !== null`): indicator not rendered — Zones nav item appears normal
- No separate "Zones" status row — the nav item itself is the indicator

### Condition

`zonesConfigured = profile.threshold_pace !== null`

- `true` → no indicator shown
- `false` → amber dot + "Not set" shown
- `null` → loading or error; no indicator shown

### Architecture

**New: `ZonesStatusContext`**

```
frontend/src/contexts/ZonesStatusContext.tsx
```

Exports `ZonesStatusProvider` and `useZonesStatus`.

```ts
interface ZonesStatusContextValue {
  zonesConfigured: boolean | null  // null = loading or error
  refreshZones: () => void         // re-fetches fetchProfile()
}
```

- Fetches `fetchProfile()` on mount; derives `zonesConfigured = profile.threshold_pace !== null`
- On error: stays `null`
- `refreshZones()` re-fetches and resets to `null` while loading
- Provider mounted in `AppShell.tsx` alongside `GarminStatusProvider`

**Modified: `Sidebar.tsx`**

Consumes `useZonesStatus()`. Inside the Zones `<NavLink>` render-prop, conditionally renders the amber dot + "Not set" label when `zonesConfigured === false`:

```tsx
<NavLink to="/zones" style={({ isActive }) => navStyle(isActive)}>
  {({ isActive }) => (
    <span style={{ color: isActive ? '#ffffff' : SIDE_ICON_INACTIVE, display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
      <ZonesIcon />
      Zones
      {zonesConfigured === false && (
        <>
          <div style={{ marginLeft: 'auto', marginRight: '4px', width: '7px', height: '7px', borderRadius: '50%', background: SIDE_ZONES_WARN, boxShadow: '0 0 0 2px rgba(245,158,11,0.2)', flexShrink: 0 }} />
          <span style={{ fontSize: '9px', fontWeight: 700, letterSpacing: '0.06em', color: SIDE_ZONES_WARN, marginLeft: 0 }}>Not set</span>
        </>
      )}
    </span>
  )}
</NavLink>
```

**Modified: `ZoneManager.tsx`**

After `handleSave` successfully calls `updateProfile`, call `refreshZones()` from context so the sidebar indicator clears:

```ts
const { refreshZones } = useZonesStatus()

// In handleSave, after successful updateProfile:
refreshZones()
```

### Files added/changed (zones)

| File | Change |
|------|--------|
| `frontend/src/contexts/ZonesStatusContext.tsx` | **New** — context + `useZonesStatus` hook |
| `frontend/src/components/layout/AppShell.tsx` | Add `<ZonesStatusProvider>` alongside `<GarminStatusProvider>` |
| `frontend/src/components/layout/Sidebar.tsx` | Inline amber indicator in Zones NavLink; add `SIDE_ZONES_WARN` constant |
| `frontend/src/components/zones/ZoneManager.tsx` | Call `refreshZones()` after successful save |

### Tests (zones additions to `Sidebar.test.tsx`)

Add `mockFetchProfile` to the `vi.hoisted` block and `vi.mock('../api/client', ...)` factory:

```ts
mockFetchProfile: vi.fn().mockResolvedValue({ threshold_pace: null, lthr: null }),

// In mock factory:
fetchProfile: mockFetchProfile,
```

New test cases:
- `threshold_pace: null` → "Not set" label visible in Zones nav item
- `threshold_pace: 280` → "Not set" label not rendered
- Loading (never-resolving): no label rendered

---

## Architecture

### New: `GarminStatusContext`

```
frontend/src/contexts/GarminStatusContext.tsx
```

Exports both `GarminStatusProvider` (the React provider component) and `useGarminStatus` (the hook) from this file.

Exposes:
```ts
interface GarminStatusContextValue {
  garminConnected: boolean | null  // null = loading or error
  refresh: () => void              // re-fetches getGarminStatus()
}
```

- Fetches `getGarminStatus()` on mount
- On error: `garminConnected` stays `null`
- `refresh()` re-triggers the fetch (sets back to `null` while re-fetching)
- Provider mounted in **`AppShell.tsx`** — guarantees auth (inside `ProtectedRoute`) and router (inside `BrowserRouter`)
- `SettingsPage` keeps its own independent `getGarminStatus()` fetch for its local `connectionState`; after connect/disconnect it calls `refresh()`. Edge case: if context fetch fails but SettingsPage fetch succeeds, sidebar stays hidden while Settings shows "Connected" — accepted degraded state.

```tsx
// AppShell.tsx (updated)
export function AppShell({ children }: AppShellProps) {
  return (
    <GarminStatusProvider>
      <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
        <Sidebar />
        <main ...>{children}</main>
      </div>
    </GarminStatusProvider>
  )
}
```

### Modified: `Sidebar.tsx`

- Consumes `useGarminStatus()`
- Renders Garmin row below the Settings `<NavLink>` when `garminConnected !== null`
- Hover via local `hovered` state + `onMouseEnter`/`onMouseLeave`
- Clicking calls `navigate('/settings')`

### Modified: `CalendarPage.tsx`

- Consumes `useGarminStatus()` — removes its own `getGarminStatus()` import and call
- Renders toolbar button when `garminConnected !== null`
- Clicking calls `navigate('/settings')`

#### Auto-sync effect migration

**Before:**
```ts
useEffect(() => {
  if (autoSyncDone.current) return
  autoSyncDone.current = true
  getGarminStatus().then(status => {
    if (status.connected) handleSyncAll()
  }).catch(() => {})
}, [])
```

**After:**
```ts
useEffect(() => {
  if (garminConnected === null) return   // ← MUST be first: wait for context to resolve
  if (autoSyncDone.current) return       // ← then check the one-shot guard
  autoSyncDone.current = true
  if (garminConnected) handleSyncAll()
}, [garminConnected]) // eslint-disable-line react-hooks/exhaustive-deps
```

**Critical:** the `null` guard must come before the `autoSyncDone` check. If reversed, the ref would be set on the first (null) run and auto-sync would never fire when the context resolves.

`handleSyncAll` is intentionally excluded from deps — it is recreated each render; adding it would re-fire the effect. The `// eslint-disable-line` comment goes on the closing `}, [garminConnected])` line, matching the existing pattern at line 65 of `CalendarPage.tsx`.

### Modified: `SettingsPage.tsx`

`SettingsPage` already fetches `getGarminStatus()` independently on mount and does not need to change. After connect/disconnect it must call `refresh()` from context to keep the sidebar indicator in sync:

```ts
const { refresh } = useGarminStatus()

// After successful connectGarmin():
setConnectionState('connected')
refresh()

// After successful disconnectGarmin():
setConnectionState('disconnected')
refresh()
```

---

## Data Flow

```
AppShell mount (authenticated)
  → GarminStatusContext fetches getGarminStatus()
  → garminConnected: boolean | null

Sidebar (every page) ← reads context → renders row
CalendarPage ← reads context → renders toolbar button + drives auto-sync

SettingsPage (connect/disconnect)
  → calls refresh() → context re-fetches → sidebar updates
```

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/contexts/GarminStatusContext.tsx` | **New** — context + `useGarminStatus` hook |
| `frontend/src/components/layout/AppShell.tsx` | Wrap in `<GarminStatusProvider>` |
| `frontend/src/components/layout/Sidebar.tsx` | Add Garmin status row; add `SIDE_GARMIN_CONNECTED/DISCONNECTED` constants |
| `frontend/src/pages/CalendarPage.tsx` | Add toolbar button; consume context; migrate auto-sync |
| `frontend/src/pages/SettingsPage.tsx` | Call `refresh()` after connect/disconnect |

---

## Tests

Additions to the **existing** test files.

### `frontend/src/tests/Sidebar.test.tsx`

`Sidebar.test.tsx` currently has no `api/client` or `react-router-dom` mocks. Both must be added. Use `vi.hoisted` (same pattern as `WorkoutLibrary.test.tsx`):

```ts
const { mockGetGarminStatus, mockNavigate } = vi.hoisted(() => ({
  mockGetGarminStatus: vi.fn().mockResolvedValue({ connected: true }),
  mockNavigate: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, getGarminStatus: mockGetGarminStatus }
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})
```

Wrap renders in `<GarminStatusProvider>`:
```tsx
render(<MemoryRouter><GarminStatusProvider><Sidebar /></GarminStatusProvider></MemoryRouter>)
```

New test cases:
- Connected (`mockResolvedValue({ connected: true })`): Garmin row visible, "Connected" label present
- Not connected (`mockResolvedValue({ connected: false })`): "Not connected" label visible
- Click row: `mockNavigate` called with `'/settings'`

### `frontend/src/tests/Calendar.test.tsx`

Add `mockGetGarminStatus` and `mockNavigate` to the **existing** `vi.hoisted` block, add `getGarminStatus` to the existing `vi.mock('../api/client', ...)` factory, and add a new `react-router-dom` mock:

```ts
// Add to existing vi.hoisted block:
mockGetGarminStatus: vi.fn().mockResolvedValue({ connected: false }),
mockNavigate: vi.fn(),

// Add to existing vi.mock('../api/client', ...) return:
getGarminStatus: mockGetGarminStatus,

// New mock (alongside existing mocks):
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})
```

Add to `beforeEach`:
```ts
mockGetGarminStatus.mockReset()
mockGetGarminStatus.mockResolvedValue({ connected: false })
mockNavigate.mockReset()
```

Update `renderPage` to wrap in `GarminStatusProvider`:
```tsx
const renderPage = (props: { initialDate?: Date } = {}) =>
  render(
    <MemoryRouter>
      <GarminStatusProvider>
        <CalendarPage {...props} />
      </GarminStatusProvider>
    </MemoryRouter>
  )
```

**Fake timers note:** the existing `test_sync_all_button` group uses `vi.useFakeTimers()`. Ensure `mockGetGarminStatus` is set in the top-level `beforeEach` (before fake timers activate) and flush the provider's async mount with `await act(async () => {})` at the start of each test in that group before asserting.

New test cases:
- Connected (`mockResolvedValue({ connected: true })`): toolbar Garmin button visible
- Not connected: red dot visible in toolbar button
- Loading (never-resolving promise): button not rendered
- Click: `mockNavigate` called with `'/settings'`

---

## Out of Scope

- Polling / live refresh of either status (single fetch on mount + explicit refresh is sufficient)
- Toast or notification when Garmin disconnects mid-session
- Zones indicator on pages other than sidebar
- Warning when `lthr` is null but `threshold_pace` is set (threshold_pace is the primary condition)
