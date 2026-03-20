# Status Indicators — Feature Reference

Design spec: `docs/superpowers/specs/2026-03-20-garmin-status-indicator-design.md`
Implementation plan: `docs/superpowers/plans/2026-03-20-garmin-status-indicators.md`
Feature plan: `features/status-indicators/PLAN.md`

---

## Contexts

Both follow the same pattern — fetch on mount, `null` while loading or on error (never throw), re-fetch on `refresh()` / `refreshZones()`:

```ts
// GarminStatusContext
interface GarminStatusContextValue {
  garminConnected: boolean | null   // null = loading or error
  refresh: () => void
}

// ZonesStatusContext
interface ZonesStatusContextValue {
  zonesConfigured: boolean | null   // null = loading or error
  refreshZones: () => void
}
```

Providers are mounted in `AppShell.tsx` — inside both `ProtectedRoute` and `BrowserRouter`.

---

## Color Constants (Sidebar.tsx)

The sidebar has its own hardcoded palette (never CSS vars):

```ts
const SIDE_GARMIN_CONNECTED    = '#22c55e'   // green
const SIDE_GARMIN_DISCONNECTED = '#ef4444'   // red
const SIDE_ZONES_WARN          = '#f59e0b'   // amber
```

Dot spec: `7px × 7px`, `borderRadius: '50%'`, `flexShrink: 0`.
Glows: `boxShadow: '0 0 0 2px rgba(<rgb>,0.2)'` matching each color.

---

## Auto-sync Guard Order (CalendarPage.tsx)

```ts
useEffect(() => {
  if (garminConnected === null) return   // MUST be first — waits for context
  if (autoSyncDone.current) return       // one-shot guard
  autoSyncDone.current = true
  if (garminConnected) handleSyncAll()
}, [garminConnected]) // eslint-disable-line react-hooks/exhaustive-deps
```

**Never swap these two guards.** If `autoSyncDone.current` is checked first, the ref is consumed on the first null render and auto-sync never fires after context resolves.

---

## Mutation → Refresh Pattern

After any mutation that changes garmin or zones state, call the context refresh to sync the sidebar:

| Mutation | Where | Call |
|----------|-------|------|
| Garmin connect | `SettingsPage.tsx` `handleConnect` | `refresh()` |
| Garmin disconnect | `SettingsPage.tsx` `handleDisconnect` | `refresh()` |
| Zones save | `ZoneManager.tsx` `handleSave` | `refreshZones()` |

---

## Test Setup

Both test files use `vi.hoisted` to create stable mock references before `vi.mock` runs.

**Sidebar tests** — wrap render:
```tsx
<MemoryRouter>
  <GarminStatusProvider>
    <ZonesStatusProvider>
      <Sidebar />
    </ZonesStatusProvider>
  </GarminStatusProvider>
</MemoryRouter>
```

**Calendar tests** — wrap `renderPage`:
```tsx
<MemoryRouter>
  <GarminStatusProvider>
    <CalendarPage {...props} />
  </GarminStatusProvider>
</MemoryRouter>
```

Mock both `getGarminStatus` and `fetchProfile` in the `vi.mock('../api/client', ...)` factory. Use `mockResolvedValue` (not `Once`) and reset in `beforeEach` — React 18 StrictMode double-fires effects.

---

## Zones Indicator Condition

```ts
zonesConfigured = profile.threshold_pace !== null
```

- `true` → no indicator (clean Zones nav item)
- `false` → amber dot + "Not set" label inline in Zones NavLink
- `null` → no indicator (loading or error)

`lthr` is intentionally ignored — `threshold_pace` is the primary condition.
