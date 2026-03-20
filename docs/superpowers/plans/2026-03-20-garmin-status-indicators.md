# Garmin & Zones Status Indicators — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Garmin connection status indicator (sidebar row + calendar toolbar button) and a Zones "Not set" inline warning (Zones NavLink) driven by two React contexts fetched on mount.

**Architecture:** Two new context files (`GarminStatusContext`, `ZonesStatusContext`) wrap `AppShell`. `Sidebar` consumes both. `CalendarPage` consumes `GarminStatusContext` and removes its own `getGarminStatus` call. `SettingsPage` + `ZoneManager` call `refresh()` / `refreshZones()` after mutations to keep the sidebar in sync.

**Tech Stack:** React 18 + TypeScript, Vitest + React Testing Library, existing `getGarminStatus` + `fetchProfile` API functions.

---

## Chunk 1: Docs & Scaffold

### Task 1: Update docs (STATUS.md, CLAUDE.md, feature docs)

**Files:**
- Modify: `STATUS.md`
- Modify: `CLAUDE.md`
- Create: `features/status-indicators/PLAN.md`
- Create: `features/status-indicators/CLAUDE.md`

- [ ] **Step 1: Add new feature section to STATUS.md**

Open `STATUS.md`. Below the `## Current Focus: Plan Coach` block (and above `### Plan Coach — Phase 4`), add a new section:

```markdown
---

## Current Focus: Status Indicators

Design spec: `docs/superpowers/specs/2026-03-20-garmin-status-indicator-design.md`
Implementation plan: `docs/superpowers/plans/2026-03-20-garmin-status-indicators.md`

### Status Indicators — Phase 1: Docs ⬜
| Task | Status |
|------|--------|
| Update STATUS.md + root CLAUDE.md | ⬜ |
| Create features/status-indicators/ docs | ⬜ |

### Status Indicators — Phase 2: Contexts ⬜
| Task | Status |
|------|--------|
| GarminStatusContext.tsx | ⬜ |
| ZonesStatusContext.tsx | ⬜ |

### Status Indicators — Phase 3: UI ⬜
| Task | Status |
|------|--------|
| AppShell: wrap with both providers | ⬜ |
| Sidebar: Garmin row + Zones inline indicator | ⬜ |
| CalendarPage: toolbar button + context + auto-sync migration | ⬜ |
| SettingsPage: call refresh() after connect/disconnect | ⬜ |
| ZoneManager: call refreshZones() after save | ⬜ |

### Status Indicators — Phase 4: Tests ⬜
| Task | Status |
|------|--------|
| Sidebar.test.tsx: new mocks + test cases | ⬜ |
| Calendar.test.tsx: GarminStatusProvider + new test cases | ⬜ |
```

- [ ] **Step 2: Add pattern note to root CLAUDE.md**

In root `CLAUDE.md`, under `## Features`, add a row to the feature table:

```markdown
| Status Indicators | `features/status-indicators/` | Garmin connection dot + Zones "Not set" inline warning in sidebar; Garmin toolbar button on CalendarPage |
```

Also add a new section near the end of the file (before `## Nice to Have`):

```markdown
## Status Indicators (added 2026-03-20)

- **GarminStatusContext** (`frontend/src/contexts/GarminStatusContext.tsx`): fetches `getGarminStatus()` on mount, exposes `garminConnected: boolean | null` + `refresh()`. Provider mounted in `AppShell.tsx`.
- **ZonesStatusContext** (`frontend/src/contexts/ZonesStatusContext.tsx`): fetches `fetchProfile()` on mount, derives `zonesConfigured = profile.threshold_pace !== null`, exposes `zonesConfigured: boolean | null` + `refreshZones()`. Provider mounted in `AppShell.tsx`.
- **Sidebar Garmin row**: `<button>` below Settings NavLink. `aria-label="Garmin: Connected – go to Settings"` / `"Not connected"` variant. Hover via local `hovered` state + `onMouseEnter`/`onMouseLeave`. Constants: `SIDE_GARMIN_CONNECTED = '#22c55e'`, `SIDE_GARMIN_DISCONNECTED = '#ef4444'`, `SIDE_ZONES_WARN = '#f59e0b'`.
- **CalendarPage auto-sync migration**: null guard (`if (garminConnected === null) return`) MUST come before `autoSyncDone` ref check to avoid the ref being consumed on the first null render before context resolves. Effect deps: `[garminConnected]`.
- **SettingsPage**: calls `refresh()` from `useGarminStatus()` after connect and after disconnect.
- **ZoneManager**: calls `refreshZones()` from `useZonesStatus()` after successful save.
- **Sidebar tests**: wrap render in `<GarminStatusProvider><ZonesStatusProvider>`. Both contexts need mocks via `vi.hoisted`.
- **Calendar tests**: wrap `renderPage` in `<GarminStatusProvider>`. Add `mockGetGarminStatus` to `vi.hoisted` + existing `vi.mock('../api/client')` factory.
```

- [ ] **Step 3: Create features/status-indicators/PLAN.md**

```markdown
# Status Indicators — Feature Plan

## Goal
Garmin connection status and Zones configuration status visible at all times in the sidebar (and Garmin also in the CalendarPage toolbar), driven by React contexts fetched once on AppShell mount.

## Components

| Component | File | Role |
|-----------|------|------|
| GarminStatusContext | `frontend/src/contexts/GarminStatusContext.tsx` | Shared Garmin status state |
| ZonesStatusContext | `frontend/src/contexts/ZonesStatusContext.tsx` | Shared zones configured state |
| AppShell | `frontend/src/components/layout/AppShell.tsx` | Provider mount point |
| Sidebar | `frontend/src/components/layout/Sidebar.tsx` | Garmin row + Zones inline indicator |
| CalendarPage | `frontend/src/pages/CalendarPage.tsx` | Garmin toolbar button + context |
| SettingsPage | `frontend/src/pages/SettingsPage.tsx` | Call refresh() after mutations |
| ZoneManager | `frontend/src/components/zones/ZoneManager.tsx` | Call refreshZones() after save |

## Tests

| Test File | New Cases |
|-----------|-----------|
| `frontend/src/tests/Sidebar.test.tsx` | Connected/not-connected labels, click→navigate, Zones "Not set", Zones configured (no label), loading (no label) |
| `frontend/src/tests/Calendar.test.tsx` | Toolbar button when connected, red dot when not connected, absent when loading, click→navigate |
```

- [ ] **Step 4: Create features/status-indicators/CLAUDE.md**

```markdown
# Status Indicators — CLAUDE.md

## Contexts

Both contexts follow the same pattern:
- Fetch on mount
- `null` while loading or on error (never throw to UI)
- `refresh()` / `refreshZones()` sets back to `null` then re-fetches

## Color Constants (Sidebar.tsx)

```ts
const SIDE_GARMIN_CONNECTED    = '#22c55e'   // green
const SIDE_GARMIN_DISCONNECTED = '#ef4444'   // red
const SIDE_ZONES_WARN          = '#f59e0b'   // amber
```

These are hardcoded hex (not CSS vars) because the sidebar is intentionally always dark and has its own palette.

## Auto-sync Guard Order (CalendarPage.tsx)

```ts
useEffect(() => {
  if (garminConnected === null) return   // MUST be first — waits for context
  if (autoSyncDone.current) return       // one-shot guard
  autoSyncDone.current = true
  if (garminConnected) handleSyncAll()
}, [garminConnected]) // eslint-disable-line react-hooks/exhaustive-deps
```

**Never swap these two guards.** If `autoSyncDone.current` is checked first, the ref gets set on the first null render and auto-sync never fires after context resolves.

## Dot Spec

- Size: `7px × 7px`, `borderRadius: '50%'`, `flexShrink: 0`
- Green glow: `boxShadow: '0 0 0 2px rgba(34,197,94,0.2)'`
- Red glow: `boxShadow: '0 0 0 2px rgba(239,68,68,0.2)'`
- Amber glow: `boxShadow: '0 0 0 2px rgba(245,158,11,0.2)'`

## Test Setup

Both test files need `vi.hoisted` blocks that create stable mock function references **before** `vi.mock` runs. Pattern from `WorkoutLibrary.test.tsx`.

Sidebar renders must wrap: `<MemoryRouter><GarminStatusProvider><ZonesStatusProvider><Sidebar /></ZonesStatusProvider></GarminStatusProvider></MemoryRouter>`.

Calendar `renderPage` must wrap: `<MemoryRouter><GarminStatusProvider><CalendarPage /></GarminStatusProvider></MemoryRouter>`.
```

- [ ] **Step 5: Commit docs**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/.claude/worktrees/vigilant-ellis
git add STATUS.md CLAUDE.md features/status-indicators/
git commit -m "docs: scaffold status-indicators feature — STATUS, CLAUDE, feature docs"
```

---

## Chunk 2: Context Layer

### Task 2: GarminStatusContext

**Files:**
- Create: `frontend/src/contexts/GarminStatusContext.tsx`

- [ ] **Step 1: Write the context file**

```tsx
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { getGarminStatus } from '../api/client'

interface GarminStatusContextValue {
  garminConnected: boolean | null
  refresh: () => void
}

const GarminStatusContext = createContext<GarminStatusContextValue | null>(null)

export function GarminStatusProvider({ children }: { children: ReactNode }) {
  const [garminConnected, setGarminConnected] = useState<boolean | null>(null)

  const fetchStatus = useCallback(() => {
    setGarminConnected(null)
    getGarminStatus()
      .then(res => setGarminConnected(res.connected))
      .catch(() => setGarminConnected(null))
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  return (
    <GarminStatusContext.Provider value={{ garminConnected, refresh: fetchStatus }}>
      {children}
    </GarminStatusContext.Provider>
  )
}

export function useGarminStatus(): GarminStatusContextValue {
  const ctx = useContext(GarminStatusContext)
  if (!ctx) throw new Error('useGarminStatus must be used inside GarminStatusProvider')
  return ctx
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/contexts/GarminStatusContext.tsx
git commit -m "feat: GarminStatusContext — shared garmin connected state"
```

---

### Task 3: ZonesStatusContext

**Files:**
- Create: `frontend/src/contexts/ZonesStatusContext.tsx`

- [ ] **Step 1: Write the context file**

```tsx
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { fetchProfile } from '../api/client'

interface ZonesStatusContextValue {
  zonesConfigured: boolean | null
  refreshZones: () => void
}

const ZonesStatusContext = createContext<ZonesStatusContextValue | null>(null)

export function ZonesStatusProvider({ children }: { children: ReactNode }) {
  const [zonesConfigured, setZonesConfigured] = useState<boolean | null>(null)

  const fetchStatus = useCallback(() => {
    setZonesConfigured(null)
    fetchProfile()
      .then(profile => setZonesConfigured(profile.threshold_pace !== null))
      .catch(() => setZonesConfigured(null))
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  return (
    <ZonesStatusContext.Provider value={{ zonesConfigured, refreshZones: fetchStatus }}>
      {children}
    </ZonesStatusContext.Provider>
  )
}

export function useZonesStatus(): ZonesStatusContextValue {
  const ctx = useContext(ZonesStatusContext)
  if (!ctx) throw new Error('useZonesStatus must be used inside ZonesStatusProvider')
  return ctx
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/contexts/ZonesStatusContext.tsx
git commit -m "feat: ZonesStatusContext — shared zones configured state"
```

---

## Chunk 3: AppShell + Sidebar

### Task 4: Wrap AppShell with providers

**Files:**
- Modify: `frontend/src/components/layout/AppShell.tsx`

Current content (full file, 23 lines):
```tsx
import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <Sidebar />
      <main style={{
        flex: 1,
        overflow: 'auto',
        background: 'var(--bg-main)',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {children}
      </main>
    </div>
  )
}
```

- [ ] **Step 1: Add imports and wrap**

Replace the entire file:

```tsx
import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { GarminStatusProvider } from '../../contexts/GarminStatusContext'
import { ZonesStatusProvider } from '../../contexts/ZonesStatusContext'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <GarminStatusProvider>
      <ZonesStatusProvider>
        <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
          <Sidebar />
          <main style={{
            flex: 1,
            overflow: 'auto',
            background: 'var(--bg-main)',
            display: 'flex',
            flexDirection: 'column',
          }}>
            {children}
          </main>
        </div>
      </ZonesStatusProvider>
    </GarminStatusProvider>
  )
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/.claude/worktrees/vigilant-ellis/frontend
npm run build 2>&1 | head -30
```

Expected: build completes (or errors only about files not yet modified).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/AppShell.tsx
git commit -m "feat: AppShell wraps GarminStatusProvider + ZonesStatusProvider"
```

---

### Task 5: Update Sidebar — Garmin row + Zones inline indicator

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Add color constants and context imports**

At the top of `Sidebar.tsx`, add imports after the existing import block:

```tsx
import { useGarminStatus } from '../../contexts/GarminStatusContext'
import { useZonesStatus } from '../../contexts/ZonesStatusContext'
```

In the constants section (after line `const SIDE_ICON_INACTIVE = '#6a6a78'`), add:

```tsx
const SIDE_GARMIN_CONNECTED    = '#22c55e'
const SIDE_GARMIN_DISCONNECTED = '#ef4444'
const SIDE_ZONES_WARN          = '#f59e0b'
```

- [ ] **Step 2: Consume contexts in the Sidebar function**

Inside `export function Sidebar()`, after the existing `const navigate = useNavigate()` line, add:

```tsx
const { garminConnected } = useGarminStatus()
const { zonesConfigured } = useZonesStatus()
const [garminHovered, setGarminHovered] = useState(false)
```

Add `useState` to the React import if not already there — check the existing import at line 1 (`import { NavLink, useNavigate } from 'react-router-dom'`). `useState` comes from React; add to Sidebar.tsx import:

```tsx
import { useState } from 'react'
```

- [ ] **Step 3: Add Zones inline indicator to the Zones NavLink**

Find the Zones `<NavLink>` block (currently lines 146–153). Replace the inner `<span>` so it renders the amber indicator when `zonesConfigured === false`:

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

- [ ] **Step 4: Add Garmin status row after the Settings NavLink**

Find the Settings `<NavLink>` block (currently ends around line 185). After the closing `</NavLink>` for Settings, add the Garmin row (still inside `<nav>`):

```tsx
{garminConnected !== null && (
  <button
    aria-label={garminConnected ? 'Garmin: Connected – go to Settings' : 'Garmin: Not connected – go to Settings'}
    onClick={() => navigate('/settings')}
    onMouseEnter={() => setGarminHovered(true)}
    onMouseLeave={() => setGarminHovered(false)}
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: '9px',
      padding: '7px 10px',
      borderRadius: '5px',
      marginBottom: '1px',
      fontSize: '12px',
      fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
      fontWeight: 600,
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
      color: SIDE_ICON_INACTIVE,
      background: garminHovered ? 'rgba(255,255,255,0.05)' : 'transparent',
      border: 'none',
      cursor: 'pointer',
      width: '100%',
      textAlign: 'left',
      transition: 'background 0.12s',
    }}
  >
    <div style={{
      width: '7px',
      height: '7px',
      borderRadius: '50%',
      background: garminConnected ? SIDE_GARMIN_CONNECTED : SIDE_GARMIN_DISCONNECTED,
      boxShadow: garminConnected
        ? '0 0 0 2px rgba(34,197,94,0.2)'
        : '0 0 0 2px rgba(239,68,68,0.2)',
      flexShrink: 0,
    }} />
    Garmin
    <span style={{
      marginLeft: 'auto',
      fontSize: '9px',
      fontWeight: 700,
      letterSpacing: '0.06em',
      color: garminConnected ? SIDE_GARMIN_CONNECTED : SIDE_GARMIN_DISCONNECTED,
    }}>
      {garminConnected ? 'Connected' : 'Not connected'}
    </span>
  </button>
)}
```

- [ ] **Step 5: Run frontend tests to confirm no existing tests broken**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/.claude/worktrees/vigilant-ellis/frontend
npm test -- --run 2>&1 | tail -30
```

Expected: Sidebar tests fail (contexts not mocked yet) — that's fine. Other test suites should still pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: Sidebar — Garmin status row + Zones inline Not-set indicator"
```

---

## Chunk 4: CalendarPage Migration

### Task 6: CalendarPage — context consumption + toolbar button + auto-sync migration

**Files:**
- Modify: `frontend/src/pages/CalendarPage.tsx`

- [ ] **Step 1: Replace getGarminStatus import + add context**

In the imports at the top of `CalendarPage.tsx`:

Remove `getGarminStatus` from the `../api/client` import (line 5). If `getGarminStatus` was the only function imported from client alongside others, keep the rest. Current line:
```ts
import { fetchWorkoutTemplates, getGarminStatus, getActivePlan } from '../api/client'
```
Replace with:
```ts
import { fetchWorkoutTemplates, getActivePlan } from '../api/client'
```

Add the context import after the existing import block:
```tsx
import { useGarminStatus } from '../contexts/GarminStatusContext'
```

- [ ] **Step 2: Consume context and remove old auto-sync effect**

Inside `CalendarPage`, after `const navigate = useNavigate()`, add:
```tsx
const { garminConnected } = useGarminStatus()
```

Delete the old auto-sync effect (lines 56–65 currently):
```ts
// DELETE this block:
const autoSyncDone = useRef(false)
useEffect(() => {
  if (autoSyncDone.current) return
  autoSyncDone.current = true
  getGarminStatus()
    .then(status => {
      if (status.connected) handleSyncAll()
    })
    .catch(() => {})
}, []) // eslint-disable-line react-hooks/exhaustive-deps
```

Replace with the migrated version — place it after the `activePlanName` effect:
```tsx
// Auto-sync on mount if Garmin is connected (context-driven)
const autoSyncDone = useRef(false)
useEffect(() => {
  if (garminConnected === null) return   // wait for context to resolve
  if (autoSyncDone.current) return       // one-shot guard
  autoSyncDone.current = true
  if (garminConnected) handleSyncAll()
}, [garminConnected]) // eslint-disable-line react-hooks/exhaustive-deps
```

- [ ] **Step 3: Add Garmin toolbar button**

Find the `{/* Sync All */}` section (currently a `<div style={{ marginLeft: 'auto' }}>` wrapping only the Sync All button). Add the Garmin button **inside that same div**, immediately before the Sync All `<button>`:

```tsx
{/* Sync All + Garmin status */}
<div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
  {garminConnected !== null && (
    <button
      onClick={() => navigate('/settings')}
      aria-label={garminConnected ? 'Garmin Connected – go to Settings' : 'Garmin Not Connected – go to Settings'}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        height: '27px',
        padding: '0 10px',
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        color: 'var(--text-muted)',
        fontSize: '10px',
        fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
        fontWeight: 700,
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
      }}
    >
      <div style={{
        width: '7px',
        height: '7px',
        borderRadius: '50%',
        background: garminConnected ? '#22c55e' : '#ef4444',
        boxShadow: garminConnected
          ? '0 0 0 2px rgba(34,197,94,0.2)'
          : '0 0 0 2px rgba(239,68,68,0.2)',
        flexShrink: 0,
      }} />
      Garmin
    </button>
  )}
  <button
    onClick={handleSyncAll}
    disabled={syncing}
    aria-label={syncing ? 'Syncing…' : 'Sync All'}
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: '5px',
      padding: '5px 13px',
      background: 'var(--accent)',
      color: 'var(--text-on-accent)',
      border: 'none',
      borderRadius: '4px',
      fontSize: '10px',
      fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
      fontWeight: 700,
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
      cursor: syncing ? 'not-allowed' : 'pointer',
      opacity: syncing ? 0.75 : 1,
      transition: 'opacity 0.15s',
    }}
  >
    <svg
      className={syncing ? 'sync-spinning' : undefined}
      width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
    >
      <polyline points="1 4 1 10 7 10"/>
      <path d="M3.51 15a9 9 0 1 0 .49-3.63"/>
    </svg>
    {syncing ? 'Syncing…' : 'Sync All'}
  </button>
</div>
```

- [ ] **Step 4: Run TypeScript check**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/.claude/worktrees/vigilant-ellis/frontend
npx tsc -b --noEmit 2>&1 | head -30
```

Expected: No errors from CalendarPage.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CalendarPage.tsx
git commit -m "feat: CalendarPage — Garmin toolbar button + context + auto-sync migration"
```

---

## Chunk 5: SettingsPage + ZoneManager Mutations

### Task 7: SettingsPage — call refresh() after connect/disconnect

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Add context import and consume hook**

Add import at top:
```tsx
import { useGarminStatus } from '../contexts/GarminStatusContext'
```

Inside `export function SettingsPage()`, after existing `const { isAdmin } = useAuth()`, add:
```tsx
const { refresh } = useGarminStatus()
```

- [ ] **Step 2: Call refresh() after connect**

In `handleConnect`, after `setConnectionState('connected')` (line ~46), add:
```ts
refresh()
```

So the block becomes:
```ts
if (res.connected) {
  setConnectionState('connected')
  refresh()
  setGarminEmail('')
  setGarminPassword('')
  setSuccessMsg('Garmin account connected successfully.')
}
```

- [ ] **Step 3: Call refresh() after disconnect**

In `handleDisconnect`, after `setConnectionState('disconnected')` (line ~87), add:
```ts
refresh()
```

So the block becomes:
```ts
await disconnectGarmin()
setConnectionState('disconnected')
refresh()
setSuccessMsg('Garmin account disconnected.')
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx
git commit -m "feat: SettingsPage — refresh GarminStatusContext after connect/disconnect"
```

---

### Task 8: ZoneManager — call refreshZones() after save

**Files:**
- Modify: `frontend/src/components/zones/ZoneManager.tsx`

- [ ] **Step 1: Add context import and consume hook**

Add import at top of ZoneManager.tsx:
```tsx
import { useZonesStatus } from '../../contexts/ZonesStatusContext'
```

Inside `export function ZoneManager()`, after the existing hook calls, add:
```tsx
const { refreshZones } = useZonesStatus()
```

- [ ] **Step 2: Call refreshZones() in handleSave after successful save**

In `handleSave`, after `showToast('success', 'Saved successfully')`, add:
```ts
refreshZones()
```

So the try block becomes:
```ts
try {
  await save({
    lthr: resolvedLthr ?? undefined,
    threshold_pace: resolvedThresholdPace ?? undefined,
  })
  if (localZones.length > 0) {
    await saveHRZones(localZones)
    setLocalZones([])
  }
  showToast('success', 'Saved successfully')
  refreshZones()
} catch (e) {
  showToast('error', e instanceof Error ? e.message : 'Save failed')
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/zones/ZoneManager.tsx
git commit -m "feat: ZoneManager — refreshZones() after successful save"
```

---

## Chunk 6: Tests

### Task 9: Sidebar.test.tsx — add context mocks + new test cases

**Files:**
- Modify: `frontend/src/tests/Sidebar.test.tsx`

Current file (44 lines) has no `api/client` or `react-router-dom` mocks. The whole file needs to be rewritten with additions.

- [ ] **Step 1: Write the full updated Sidebar.test.tsx**

Replace the entire file:

```tsx
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { Sidebar } from '../components/layout/Sidebar'
import { GarminStatusProvider } from '../contexts/GarminStatusContext'
import { ZonesStatusProvider } from '../contexts/ZonesStatusContext'

declare const __APP_VERSION__: string

const { mockGetGarminStatus, mockFetchProfile, mockNavigate } = vi.hoisted(() => ({
  mockGetGarminStatus: vi.fn().mockResolvedValue({ connected: true }),
  mockFetchProfile: vi.fn().mockResolvedValue({ threshold_pace: null, lthr: null }),
  mockNavigate: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, getGarminStatus: mockGetGarminStatus, fetchProfile: mockFetchProfile }
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/AuthContext')>()
  return {
    ...actual,
    useAuth: () => ({
      user: { id: 1, email: 'test@example.com' },
      accessToken: null,
      isAdmin: false,
      googleLogin: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    }),
  }
})

vi.mock('../contexts/ThemeContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/ThemeContext')>()
  return {
    ...actual,
    useTheme: () => ({ theme: 'dark' as const, toggleTheme: vi.fn() }),
  }
})

beforeEach(() => {
  mockGetGarminStatus.mockReset()
  mockGetGarminStatus.mockResolvedValue({ connected: true })
  mockFetchProfile.mockReset()
  mockFetchProfile.mockResolvedValue({ threshold_pace: null, lthr: null })
  mockNavigate.mockReset()
})

const renderSidebar = () =>
  render(
    <MemoryRouter>
      <GarminStatusProvider>
        <ZonesStatusProvider>
          <Sidebar />
        </ZonesStatusProvider>
      </GarminStatusProvider>
    </MemoryRouter>
  )

describe('Sidebar version display', () => {
  it('shows version with -dev suffix in test/dev mode', () => {
    renderSidebar()
    expect(screen.getByText(/^v\d+\.\d+\.\d+-dev$/)).toBeInTheDocument()
  })

  it('version number reflects package.json via __APP_VERSION__', () => {
    renderSidebar()
    expect(screen.getByText(new RegExp(`^v${__APP_VERSION__}`))).toBeInTheDocument()
  })
})

describe('Garmin status row', () => {
  it('shows Connected label when garminConnected is true', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    renderSidebar()
    expect(await screen.findByText('Connected')).toBeInTheDocument()
  })

  it('shows Not connected label when garminConnected is false', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: false })
    renderSidebar()
    expect(await screen.findByText('Not connected')).toBeInTheDocument()
  })

  it('clicking Garmin row navigates to /settings', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    const user = userEvent.setup()
    renderSidebar()
    const btn = await screen.findByRole('button', { name: /Garmin: Connected/i })
    await user.click(btn)
    expect(mockNavigate).toHaveBeenCalledWith('/settings')
  })

  it('does not render Garmin row while loading (null)', async () => {
    mockGetGarminStatus.mockReturnValue(new Promise(() => {}))
    renderSidebar()
    await act(async () => {})
    expect(screen.queryByText('Connected')).not.toBeInTheDocument()
    expect(screen.queryByText('Not connected')).not.toBeInTheDocument()
  })
})

describe('Zones status indicator', () => {
  it('shows Not set label when threshold_pace is null', async () => {
    mockFetchProfile.mockResolvedValue({ threshold_pace: null, lthr: null })
    renderSidebar()
    expect(await screen.findByText('Not set')).toBeInTheDocument()
  })

  it('does not show Not set when threshold_pace is set', async () => {
    mockFetchProfile.mockResolvedValue({ threshold_pace: 280, lthr: 155 })
    renderSidebar()
    await act(async () => {})
    expect(screen.queryByText('Not set')).not.toBeInTheDocument()
  })

  it('does not show Not set while loading (null)', async () => {
    mockFetchProfile.mockReturnValue(new Promise(() => {}))
    renderSidebar()
    await act(async () => {})
    expect(screen.queryByText('Not set')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run Sidebar tests — expect GREEN**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/.claude/worktrees/vigilant-ellis/frontend
npm test -- --run src/tests/Sidebar.test.tsx 2>&1
```

Expected: All tests pass (9 tests).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/Sidebar.test.tsx
git commit -m "test: Sidebar — Garmin status row + Zones indicator tests"
```

---

### Task 10: Calendar.test.tsx — add GarminStatusProvider + new test cases

**Files:**
- Modify: `frontend/src/tests/Calendar.test.tsx`

- [ ] **Step 1: Add mockGetGarminStatus + mockGetActivePlan + mockNavigate to vi.hoisted block**

Current `vi.hoisted` block starts at line 10. Add to it:

```tsx
const { mockSchedule, mockSyncAll, mockLoadRange, mockFetchTemplates, mockGetGarminStatus, mockGetActivePlan, mockNavigate } = vi.hoisted(() => {
  const defaultTemplates = [
    { id: 1, name: 'Easy Run',  estimated_duration_sec: 2700, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
    { id: 2, name: 'Tempo Run', estimated_duration_sec: 3600, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
  ]
  return {
    mockSchedule: vi.fn(),
    mockSyncAll: vi.fn(),
    mockLoadRange: vi.fn(),
    mockFetchTemplates: vi.fn().mockResolvedValue(defaultTemplates),
    mockGetGarminStatus: vi.fn().mockResolvedValue({ connected: false }),
    mockGetActivePlan: vi.fn().mockResolvedValue(null),
    mockNavigate: vi.fn(),
  }
})
```

- [ ] **Step 2: Add getGarminStatus + getActivePlan to the api/client mock factory**

Current mock (line 42):
```tsx
vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, fetchWorkoutTemplates: mockFetchTemplates }
})
```

Replace with:
```tsx
vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchWorkoutTemplates: mockFetchTemplates,
    getGarminStatus: mockGetGarminStatus,
    getActivePlan: mockGetActivePlan,
  }
})
```

- [ ] **Step 3: Add react-router-dom mock (new, alongside existing mocks)**

After the `vi.mock('../api/client', ...)` block, add:

```tsx
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})
```

- [ ] **Step 4: Add resets to beforeEach**

In the existing `beforeEach`, add:

```tsx
mockGetGarminStatus.mockReset()
mockGetGarminStatus.mockResolvedValue({ connected: false })
mockGetActivePlan.mockReset()
mockGetActivePlan.mockResolvedValue(null)
mockNavigate.mockReset()
```

- [ ] **Step 5: Add GarminStatusProvider import + update renderPage**

Add import at top of the test file:
```tsx
import { GarminStatusProvider } from '../contexts/GarminStatusContext'
```

Update `renderPage` (currently line 7):
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

- [ ] **Step 6: Add new Garmin toolbar test cases**

After the existing describe blocks, add:

```tsx
describe('test_garmin_toolbar_button', () => {
  it('shows Garmin toolbar button when connected', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    renderPage({ initialDate: new Date('2026-03-09') })
    expect(await screen.findByRole('button', { name: /Garmin Connected/i })).toBeInTheDocument()
  })

  it('shows Garmin toolbar button when not connected', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: false })
    renderPage({ initialDate: new Date('2026-03-09') })
    expect(await screen.findByRole('button', { name: /Garmin Not Connected/i })).toBeInTheDocument()
  })

  it('does not show Garmin toolbar button while loading', async () => {
    mockGetGarminStatus.mockReturnValue(new Promise(() => {}))
    renderPage({ initialDate: new Date('2026-03-09') })
    await act(async () => {})
    expect(screen.queryByRole('button', { name: /Garmin/i })).not.toBeInTheDocument()
  })

  it('clicking Garmin toolbar button navigates to /settings', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    const user = userEvent.setup()
    renderPage({ initialDate: new Date('2026-03-09') })
    const btn = await screen.findByRole('button', { name: /Garmin Connected/i })
    await user.click(btn)
    expect(mockNavigate).toHaveBeenCalledWith('/settings')
  })
})
```

- [ ] **Step 7: Run Calendar tests — expect GREEN**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/.claude/worktrees/vigilant-ellis/frontend
npm test -- --run src/tests/Calendar.test.tsx 2>&1
```

Expected: All existing tests still pass + 4 new Garmin toolbar tests pass.

- [ ] **Step 8: Run full test suite**

```bash
npm test -- --run 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/tests/Calendar.test.tsx
git commit -m "test: Calendar — GarminStatusProvider wrap + toolbar button tests"
```

---

## Chunk 7: Final Checks + Status Update

### Task 11: TypeScript build + final verification

- [ ] **Step 1: Full TypeScript build**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/.claude/worktrees/vigilant-ellis/frontend
npm run build 2>&1 | tail -20
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 2: Run full test suite one more time**

```bash
npm test -- --run 2>&1
```

Expected: All tests pass.

- [ ] **Step 3: Update STATUS.md — mark all tasks done**

In `STATUS.md`, update the Status Indicators section to mark all tasks ✅:

```markdown
### Status Indicators — Phase 1: Docs ✅
| Task | Status |
|------|--------|
| Update STATUS.md + root CLAUDE.md | ✅ |
| Create features/status-indicators/ docs | ✅ |

### Status Indicators — Phase 2: Contexts ✅
| Task | Status |
|------|--------|
| GarminStatusContext.tsx | ✅ |
| ZonesStatusContext.tsx | ✅ |

### Status Indicators — Phase 3: UI ✅
| Task | Status |
|------|--------|
| AppShell: wrap with both providers | ✅ |
| Sidebar: Garmin row + Zones inline indicator | ✅ |
| CalendarPage: toolbar button + context + auto-sync migration | ✅ |
| SettingsPage: call refresh() after connect/disconnect | ✅ |
| ZoneManager: call refreshZones() after save | ✅ |

### Status Indicators — Phase 4: Tests ✅
| Task | Status |
|------|--------|
| Sidebar.test.tsx: new mocks + test cases | ✅ |
| Calendar.test.tsx: GarminStatusProvider + new test cases | ✅ |
```

- [ ] **Step 4: Final commit**

```bash
git add STATUS.md
git commit -m "docs: STATUS — status-indicators feature complete"
```
