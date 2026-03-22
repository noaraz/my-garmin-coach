# Mobile Responsive Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make GarminCoach fully usable on mobile phones via a bottom tab bar + a Today home screen, while keeping the desktop layout completely unchanged.

**Architecture:** Add a `useIsMobile` hook (768px breakpoint via `matchMedia`) that gates two separate rendering paths in `AppShell`: desktop gets the existing Sidebar, mobile gets a new `BottomTabBar`. A new `TodayPage` serves as the mobile home screen. `WorkoutDetailPanel` grows a bottom-sheet mode. All other pages get responsive padding/overflow fixes. **Zero backend changes.**

**Tech Stack:** React 18 + TypeScript + Tailwind v4 CSS custom properties · Vitest + React Testing Library · `useNavigate` / `MemoryRouter` for routing

**Constraints:**
- Desktop appearance must not change at all — run `npm test -- --run` + `npx tsc -b --noEmit` after EVERY task
- Pure frontend — no API changes, no new endpoints
- All color tokens from CSS custom properties (`var(--*)`) — no hardcoded hex in new component files
- Sidebar is the one component exempt from zero-hex (already was); new components are not exempt

**Desktop regression check (run after every task):**
```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npm test -- --run && npx tsc -b --noEmit && echo "✅ Desktop OK"
```
If this fails at any point, fix before moving on.

---

## Phase 0: Documentation — Update MD files before touching any code

### Task 0: Update STATUS.md, CLAUDE.md, PLAN.md, and create feature folder

**Files:**
- Modify: `STATUS.md`
- Modify: `CLAUDE.md` (root)
- Modify: `PLAN.md` (root)
- Create: `features/mobile-responsive/PLAN.md`
- Create: `features/mobile-responsive/CLAUDE.md`

No code changes in this task. Documentation and branch creation only.

- [ ] **Step 0: Pull main and create feature branch**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git checkout main && git pull origin main
git checkout -b feature/mobile-responsive
```

Expected: clean branch based on latest main, all existing tests green.

Verify immediately:
```bash
cd frontend && npm test -- --run && echo "✅ baseline green"
```

- [ ] **Step 1: Update STATUS.md**

In `STATUS.md`, find the line `| Mobile responsive | ⬜ |` and replace with `| Mobile responsive | 🔄 |`.

Then add a new section at the TOP of `STATUS.md` (after the header line and before "Current Focus"):

```markdown
## Current Focus: Mobile Responsive 🔄

Visual design: `frontend/public/mobile-mockup.html` (open in browser to see all screens)
Implementation plan: `docs/superpowers/plans/2026-03-21-mobile-responsive.md`
Feature docs: `features/mobile-responsive/`

### Mobile Responsive
| Task | Status |
|------|--------|
| Phase 0: MD files (STATUS.md, CLAUDE.md, PLAN.md, feature folder) | 🔄 |
| Chunk 1: useIsMobile hook + CSS mobile vars + AppShell mobile layout | ⬜ |
| Chunk 2: BottomTabBar + More sheet + /today route | ⬜ |
| Chunk 3: TodayPage (week strip, hero card, chips) | ⬜ |
| Chunk 4: WorkoutDetailPanel bottom sheet + OnboardingWizard + HelpPage mobile | ⬜ |
| Chunk 5: All pages responsive padding/overflow audit | ⬜ |

---
```

- [ ] **Step 2: Create `features/mobile-responsive/PLAN.md`**

```markdown
# Mobile Responsive

## References
- **Visual design**: `frontend/public/mobile-mockup.html` — open in browser, shows all screens and flows
- **Implementation plan**: `docs/superpowers/plans/2026-03-21-mobile-responsive.md` — step-by-step TDD tasks

## Goal
Make every page of GarminCoach fully usable on mobile phones (< 768px) without changing the desktop layout.

## Approach
- `useIsMobile` hook (768px via `matchMedia`) gates rendering in `AppShell`
- Desktop: Sidebar + main (unchanged)
- Mobile: `BottomTabBar` (Today · Calendar · Library · Zones · ···) + main with bottom padding
- More sheet (slides up from bottom): Builder · Plan Coach · Settings · Help
- New `/today` route as mobile home screen — week strip, hero workout card, quick status chips
- `WorkoutDetailPanel` → bottom sheet (75vh slide-up) on mobile
- `OnboardingWizard` → full-screen on mobile
- `HelpPage` → stacked card grid on mobile
- All existing pages → responsive padding/overflow fixes

## Breakpoint
`< 768px` — `@media (max-width: 767px)` in CSS, `matchMedia('(max-width: 767px)')` in JS

## New Files
- `frontend/src/hooks/useIsMobile.ts`
- `frontend/src/components/layout/BottomTabBar.tsx`
- `frontend/src/pages/TodayPage.tsx`

## Modified Files
- `frontend/src/index.css` — mobile CSS vars + @media rules
- `frontend/src/App.tsx` — /today route + SmartRedirect
- `frontend/src/components/layout/AppShell.tsx` — mobile layout switch
- `frontend/src/components/layout/Sidebar.tsx` — aria-label on aside
- `frontend/src/components/calendar/WorkoutDetailPanel.tsx` — bottom sheet on mobile
- `frontend/src/components/onboarding/OnboardingWizard.tsx` — full-screen on mobile
- `frontend/src/pages/HelpPage.tsx` — stacked cards on mobile
- `frontend/src/pages/CalendarPage.tsx` — toolbar wraps on mobile
- `frontend/src/pages/LibraryPage.tsx` — responsive padding
- `frontend/src/components/zones/ZoneManager.tsx` — full-width inputs on mobile
- `frontend/src/pages/BuilderPage.tsx` — overflow-x auto on mobile
- `frontend/src/pages/PlanCoachPage.tsx` — table overflow-x auto on mobile
- `frontend/src/pages/SettingsPage.tsx` — full-width form on mobile

## Test Files
- `frontend/src/tests/useIsMobile.test.ts` (new)
- `frontend/src/tests/AppShell.test.tsx` (new)
- `frontend/src/tests/BottomTabBar.test.tsx` (new)
- `frontend/src/tests/SmartRedirect.test.tsx` (new)
- `frontend/src/tests/TodayPage.test.tsx` (new)
- `frontend/src/tests/WorkoutDetailPanel.test.tsx` (existing — add mobile test)
- `frontend/src/tests/OnboardingWizard.test.tsx` (existing — add mobile test)
- `frontend/src/tests/HelpPage.test.tsx` (existing — add mobile test)

## Constraints
- Zero backend changes
- Desktop layout unchanged — all existing tests continue to pass
- No hardcoded hex in new files — use CSS vars
```

- [ ] **Step 3: Create `features/mobile-responsive/CLAUDE.md`**

```markdown
# Mobile Responsive — Patterns & Gotchas

## References
- Visual design: `frontend/public/mobile-mockup.html` (open in browser)
- Implementation plan: `docs/superpowers/plans/2026-03-21-mobile-responsive.md`

## useIsMobile Hook
- Uses `window.matchMedia('(max-width: 767px)')` — same query as CSS @media
- Listens to `change` events — updates state on resize
- In Vitest: `setup.ts` mocks `matchMedia` returning `{ matches: false }` (desktop default)
- Override per-test BEFORE rendering: `window.matchMedia = vi.fn().mockReturnValue({ matches: true, ... })`
- Always reset in `beforeEach(() => { window.matchMedia = vi.fn().mockReturnValue({ matches: false, ... }) })`

## AppShell Mobile Layout
- Desktop: `<Sidebar />` + `<OnboardingWizard />` + `<main>`
- Mobile: `<OnboardingWizard />` + `<main style={{ paddingBottom: 'var(--bottom-tab-height)' }}>` + `<BottomTabBar />`
- Sidebar.tsx root element is `<aside>` (ARIA role `complementary`, NOT `navigation`)
  — aria-label must be added: `<aside aria-label="Sidebar navigation">`

## BottomTabBar
- Tabs: Today · Calendar · Library · Zones · ···
- More sheet items (slide-up): Builder · Plan Coach · Settings · Help
- More sheet uses `.mobile-bottom-sheet` CSS class (in `@media` block in `index.css`)
- Backdrop: `data-testid="more-sheet-backdrop"` for test selection

## CSS mobile vars
- `--bottom-tab-height: 56px` — added to existing `:root` block in `index.css` (NOT a second block)
- `--bottom-sheet-radius: 16px` — same
- `.mobile-page-content` — class for scrollable containers needing bottom padding above tab bar
- `.workout-detail-panel-mobile` — 75vh bottom sheet for WorkoutDetailPanel

## WorkoutDetailPanel field names (CRITICAL)
- `ScheduledWorkout.date` (NOT `scheduled_date`)
- `ScheduledWorkoutWithActivity.activity: GarminActivity | null` (NOT `garmin_activity`)
- `GarminActivity` has NO `compliance_level` field
- `WorkoutDetailPanel` requires: `onReschedule`, `onRemove`, `onUnpair`, `onUpdateNotes`, `onNavigateToBuilder`
  — pass no-ops in TodayPage since it's view-only

## OnboardingWizard Mobile
- On mobile: `position: fixed; inset: 0` — full-screen, no border-radius, no max-width cap
- On desktop: existing centered modal (max-width ~540px, border-radius, shadow) — unchanged
- Wizard navigates between routes — all existing routes work with BottomTabBar

## HelpPage Mobile
- Feature cards: `grid-template-columns: 1fr` on mobile (stacked), multi-column on desktop
- Replay Tour button: `openWizard()` from `OnboardingContext` — works identically on mobile
- The onboarding wizard full-screen mode activates because `useIsMobile` returns true

## Desktop Regression Policy
After every task: `npm test -- --run && npx tsc -b --noEmit`
If any existing test fails, fix before proceeding. Never skip.
```

- [ ] **Step 4: Update root CLAUDE.md Features table**

In root `CLAUDE.md`, find the Features table under `## Features` and add a row (or update if it already exists):

```
| Mobile Responsive | `features/mobile-responsive/` | Bottom tab bar, TodayPage, responsive layout for all pages |
```

- [ ] **Step 5: Update root PLAN.md**

In root `PLAN.md`, find the section that lists features (look for a table or bullet list) and add or update the Mobile Responsive entry to show it's in progress.

- [ ] **Step 6: Commit Phase 0**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add STATUS.md CLAUDE.md PLAN.md \
        features/mobile-responsive/PLAN.md \
        features/mobile-responsive/CLAUDE.md
git commit -m "docs: phase 0 — mobile-responsive MD files and status tracking"
```

---

## Chunk 1: Foundation — useIsMobile hook + CSS mobile vars + AppShell mobile layout

### Task 1: `useIsMobile` hook

**Files:**
- Create: `frontend/src/hooks/useIsMobile.ts`
- Create: `frontend/src/tests/useIsMobile.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/tests/useIsMobile.test.ts
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useIsMobile } from '../hooks/useIsMobile'

describe('useIsMobile', () => {
  let listeners: Array<(e: { matches: boolean }) => void>

  function mockMatchMedia(matches: boolean) {
    listeners = []
    window.matchMedia = vi.fn().mockReturnValue({
      matches,
      media: '(max-width: 767px)',
      onchange: null,
      addEventListener: vi.fn((_, cb) => { listeners.push(cb) }),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })
  }

  beforeEach(() => {
    mockMatchMedia(false) // desktop by default
  })

  it('useIsMobile_whenWidthAbove768_returnsFalse', () => {
    mockMatchMedia(false)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })

  it('useIsMobile_whenWidthBelow768_returnsTrue', () => {
    mockMatchMedia(true)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(true)
  })

  it('useIsMobile_whenResizedFromDesktopToMobile_updatesValue', () => {
    mockMatchMedia(false)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
    act(() => { listeners.forEach(cb => cb({ matches: true })) })
    expect(result.current).toBe(true)
  })
})
```

- [ ] **Step 2: Run to confirm RED**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npm test -- --run src/tests/useIsMobile.test.ts
```

Expected: FAIL with `Cannot find module '../hooks/useIsMobile'`

- [ ] **Step 3: Implement the hook**

```typescript
// frontend/src/hooks/useIsMobile.ts
import { useState, useEffect } from 'react'

const MOBILE_QUERY = '(max-width: 767px)'

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(
    () => window.matchMedia(MOBILE_QUERY).matches
  )

  useEffect(() => {
    const mql = window.matchMedia(MOBILE_QUERY)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])

  return isMobile
}
```

- [ ] **Step 4: Run to confirm GREEN**

```bash
npm test -- --run src/tests/useIsMobile.test.ts
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/hooks/useIsMobile.ts frontend/src/tests/useIsMobile.test.ts
git commit -m "feat: add useIsMobile hook with matchMedia listener"
```

---

### Task 2: Mobile CSS variables in `index.css`

**Files:**
- Modify: `frontend/src/index.css`

No new test (pure CSS — not testable via Vitest).

- [ ] **Step 1: Add mobile CSS to index.css**

**Important:** Add the two new CSS variables into the **existing** `:root` block (around line 18) — do NOT append a second `:root` block. Open `frontend/src/index.css`, find `:root, [data-theme="light"] {` and add before the closing `}`:

```css
  --bottom-tab-height: 56px;
  --bottom-sheet-radius: 16px;
```

Then append the following `@media` block at the **end** of `frontend/src/index.css`:

```css

/* ── Mobile global resets ────────────────────────── */
/* NOTE: @keyframes inside @media is valid CSS — keeps animation scoped to mobile */
@media (max-width: 767px) {
  /* Prevent horizontal scroll from absolute positioned children */
  body {
    overflow-x: hidden;
  }

  /* Give scrollable page content space above the fixed tab bar */
  .mobile-page-content {
    padding-bottom: calc(var(--bottom-tab-height) + env(safe-area-inset-bottom, 0px));
  }

  /* Bottom sheet overlay backdrop */
  .mobile-bottom-sheet-backdrop {
    position: fixed;
    inset: 0;
    background: var(--overlay-bg);
    z-index: 200;
  }

  /* Bottom sheet panel */
  .mobile-bottom-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--bg-surface);
    border-radius: var(--bottom-sheet-radius) var(--bottom-sheet-radius) 0 0;
    border-top: 1px solid var(--border);
    z-index: 201;
    animation: slideUpSheet 200ms ease-out;
    max-height: 85vh;
    overflow-y: auto;
  }

  @keyframes slideUpSheet {
    from { transform: translateY(100%); }
    to   { transform: translateY(0); }
  }

  /* Workout detail panel: bottom sheet instead of right panel */
  .workout-detail-panel-mobile {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 75vh;
    background: var(--bg-surface);
    border-radius: var(--bottom-sheet-radius) var(--bottom-sheet-radius) 0 0;
    border-top: 1px solid var(--border);
    z-index: 300;
    animation: slideUpSheet 200ms ease-out;
    overflow-y: auto;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
}
```

- [ ] **Step 2: Verify build still compiles**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npx tsc -b --noEmit && echo "TypeScript OK"
```

Expected: `TypeScript OK` (CSS files are not type-checked)

- [ ] **Step 3: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/index.css
git commit -m "feat: add mobile CSS vars and @media layout rules"
```

---

### Task 3: AppShell mobile layout

**Files:**
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/tests/AppShell.test.tsx`

The AppShell must:
- On **desktop** (≥768px): render `<Sidebar />` + `<main>` (unchanged)
- On **mobile** (<768px): skip `<Sidebar />`, add `paddingBottom: var(--bottom-tab-height)` to `<main>`, render `<BottomTabBar />` fixed at bottom

`BottomTabBar` doesn't exist yet — import it but write a stub first; Task 4 replaces it.

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/tests/AppShell.test.tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'

import type { ReactNode } from 'react'

// Mock contexts that AppShell's providers depend on
vi.mock('../api/client', () => ({
  getGarminStatus: vi.fn().mockResolvedValue({ connected: false }),
  fetchProfile: vi.fn().mockResolvedValue(null),
}))

vi.mock('../contexts/OnboardingContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/OnboardingContext')>()
  return {
    ...actual,
    OnboardingProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  }
})

vi.mock('../components/onboarding/OnboardingWizard', () => ({
  OnboardingWizard: () => null,
}))

function mockMatchMedia(isMobile: boolean) {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: isMobile,
    media: '(max-width: 767px)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })
}

const renderShell = () =>
  render(
    <MemoryRouter>
      <AppShell>
        <div data-testid="child">content</div>
      </AppShell>
    </MemoryRouter>
  )

describe('AppShell', () => {
  beforeEach(() => {
    // Reset to desktop by default so tests don't bleed into each other
    mockMatchMedia(false)
  })

  it('AppShell_onDesktop_rendersSidebar', () => {
    mockMatchMedia(false)
    renderShell()
    // Sidebar.tsx root element is <aside> (ARIA role = complementary)
    expect(screen.getByRole('complementary', { name: /sidebar/i })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: /bottom tab/i })).not.toBeInTheDocument()
  })

  it('AppShell_onMobile_rendersBottomTabBar', () => {
    mockMatchMedia(true)
    renderShell()
    expect(screen.queryByRole('complementary', { name: /sidebar/i })).not.toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: /bottom tab/i })).toBeInTheDocument()
  })

  it('AppShell_alwaysRendersChildren', () => {
    mockMatchMedia(false)
    renderShell()
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to confirm RED**

```bash
npm test -- --run src/tests/AppShell.test.tsx
```

Expected: FAIL — `BottomTabBar` doesn't exist yet + aria assertions fail

- [ ] **Step 3: Create a minimal BottomTabBar stub**

```typescript
// frontend/src/components/layout/BottomTabBar.tsx
// Stub — replaced fully in Task 4
export function BottomTabBar() {
  return (
    <nav aria-label="Bottom tab bar" style={{ position: 'fixed', bottom: 0, left: 0, right: 0, height: 'var(--bottom-tab-height)', background: 'var(--bg-surface)', borderTop: '1px solid var(--border)', zIndex: 100 }}>
      {/* tabs rendered in Task 4 */}
    </nav>
  )
}
```

- [ ] **Step 4: Modify AppShell.tsx**

```typescript
// frontend/src/components/layout/AppShell.tsx
import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { BottomTabBar } from './BottomTabBar'
import { GarminStatusProvider } from '../../contexts/GarminStatusContext'
import { ZonesStatusProvider } from '../../contexts/ZonesStatusContext'
import { OnboardingProvider } from '../../contexts/OnboardingContext'
import { OnboardingWizard } from '../onboarding/OnboardingWizard'
import { useIsMobile } from '../../hooks/useIsMobile'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const isMobile = useIsMobile()

  return (
    <OnboardingProvider>
      <GarminStatusProvider>
        <ZonesStatusProvider>
          <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
            {!isMobile && <Sidebar />}
            <OnboardingWizard />
            <main
              style={{
                flex: 1,
                overflow: 'auto',
                background: 'var(--bg-main)',
                display: 'flex',
                flexDirection: 'column',
                paddingBottom: isMobile ? 'var(--bottom-tab-height)' : undefined,
              }}
            >
              {children}
            </main>
            {isMobile && <BottomTabBar />}
          </div>
        </ZonesStatusProvider>
      </GarminStatusProvider>
    </OnboardingProvider>
  )
}
```

- [ ] **Step 5: Add `aria-label` to Sidebar's root `<aside>` element**

In `frontend/src/components/layout/Sidebar.tsx`, find the outermost `<aside>` element (ARIA role = `complementary`) and add `aria-label="Sidebar navigation"`. Do NOT change the element type — keep it as `<aside>`.

Read the file first to find the exact line, then add the attribute:

```typescript
// Find: <aside style={{...}}>
// Change to: <aside aria-label="Sidebar navigation" style={{...}}>
```

This matches the test query `getByRole('complementary', { name: /sidebar/i })`.

- [ ] **Step 6: Run AppShell tests to confirm GREEN**

```bash
npm test -- --run src/tests/AppShell.test.tsx
```

Expected: 3 tests PASS

- [ ] **Step 7: Run full test suite to confirm no regressions**

```bash
npm test -- --run
```

Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/components/layout/AppShell.tsx \
        frontend/src/components/layout/BottomTabBar.tsx \
        frontend/src/components/layout/Sidebar.tsx \
        frontend/src/tests/AppShell.test.tsx
git commit -m "feat: AppShell mobile layout — hide sidebar, show BottomTabBar on mobile"
```

---

## Chunk 2: BottomTabBar + More Sheet + App routing

### Task 4: Full BottomTabBar with More sheet

**Files:**
- Modify: `frontend/src/components/layout/BottomTabBar.tsx` (replace stub)
- Modify: `frontend/src/tests/AppShell.test.tsx` (add tab interaction tests)
- Create: `frontend/src/tests/BottomTabBar.test.tsx`

Tab bar layout: **Today · Calendar · Library · Zones · ···**
More sheet (slides up): **Builder · Plan Coach · Settings · Help**

- [ ] **Step 1: Write tests for BottomTabBar**

```typescript
// frontend/src/tests/BottomTabBar.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { BottomTabBar } from '../components/layout/BottomTabBar'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate, useLocation: () => ({ pathname: '/today' }) }
})

const renderBar = () =>
  render(<MemoryRouter><BottomTabBar /></MemoryRouter>)

describe('BottomTabBar', () => {
  it('BottomTabBar_renders_fiveTabs', () => {
    renderBar()
    expect(screen.getByLabelText('Today')).toBeInTheDocument()
    expect(screen.getByLabelText('Calendar')).toBeInTheDocument()
    expect(screen.getByLabelText('Library')).toBeInTheDocument()
    expect(screen.getByLabelText('Zones')).toBeInTheDocument()
    expect(screen.getByLabelText('More')).toBeInTheDocument()
  })

  it('BottomTabBar_clickCalendar_navigatesToCalendar', () => {
    renderBar()
    fireEvent.click(screen.getByLabelText('Calendar'))
    expect(mockNavigate).toHaveBeenCalledWith('/calendar')
  })

  it('BottomTabBar_clickMore_opensMoreSheet', () => {
    renderBar()
    fireEvent.click(screen.getByLabelText('More'))
    expect(screen.getByText('Builder')).toBeInTheDocument()
    expect(screen.getByText('Plan Coach')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Help')).toBeInTheDocument()
  })

  it('BottomTabBar_clickBackdrop_closesMoreSheet', () => {
    renderBar()
    fireEvent.click(screen.getByLabelText('More'))
    expect(screen.getByText('Builder')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('more-sheet-backdrop'))
    expect(screen.queryByText('Builder')).not.toBeInTheDocument()
  })

  it('BottomTabBar_clickMoreItem_navigatesAndClosesSheet', () => {
    renderBar()
    fireEvent.click(screen.getByLabelText('More'))
    fireEvent.click(screen.getByText('Settings'))
    expect(mockNavigate).toHaveBeenCalledWith('/settings')
    expect(screen.queryByText('Builder')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to confirm RED**

```bash
npm test -- --run src/tests/BottomTabBar.test.tsx
```

Expected: FAIL — stub has no tabs yet

- [ ] **Step 3: Implement BottomTabBar**

```typescript
// frontend/src/components/layout/BottomTabBar.tsx
import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

// SVG icons — inline to avoid extra files
const TodayIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>
)
const CalendarIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
)
const LibraryIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="8" y1="6" x2="21" y2="6"/>
    <line x1="8" y1="12" x2="21" y2="12"/>
    <line x1="8" y1="18" x2="21" y2="18"/>
    <line x1="3" y1="6" x2="3.01" y2="6"/>
    <line x1="3" y1="12" x2="3.01" y2="12"/>
    <line x1="3" y1="18" x2="3.01" y2="18"/>
  </svg>
)
const ZonesIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
)
const MoreIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="5" cy="12" r="1" fill="currentColor"/>
    <circle cx="12" cy="12" r="1" fill="currentColor"/>
    <circle cx="19" cy="12" r="1" fill="currentColor"/>
  </svg>
)

// More sheet items
const MORE_ITEMS: Array<{ label: string; route: string }> = [
  { label: 'Builder',    route: '/builder' },
  { label: 'Plan Coach', route: '/plan-coach' },
  { label: 'Settings',   route: '/settings' },
  { label: 'Help',       route: '/help' },
]

// Primary tabs
const TABS = [
  { label: 'Today',    route: '/today',    Icon: TodayIcon },
  { label: 'Calendar', route: '/calendar', Icon: CalendarIcon },
  { label: 'Library',  route: '/library',  Icon: LibraryIcon },
  { label: 'Zones',    route: '/zones',    Icon: ZonesIcon },
]

export function BottomTabBar() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)

  const tabStyle = (active: boolean): CSSProperties => ({
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    padding: '6px 0 4px',
    color: active ? 'var(--accent)' : 'var(--text-muted)',
    fontSize: 9,
    fontFamily: 'var(--font-family-display)',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    transition: 'color 120ms',
  })

  const moreItemStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    width: '100%',
    padding: '14px 20px',
    border: 'none',
    borderBottom: '1px solid var(--border)',
    background: 'none',
    cursor: 'pointer',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-family-body)',
    fontSize: 16,
    textAlign: 'left',
  }

  return (
    <>
      {moreOpen && (
        <>
          <div
            data-testid="more-sheet-backdrop"
            className="mobile-bottom-sheet-backdrop"
            onClick={() => setMoreOpen(false)}
          />
          <div className="mobile-bottom-sheet">
            <div style={{ padding: '12px 20px 8px', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontFamily: 'var(--font-family-display)', fontWeight: 700, fontSize: 13, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                More
              </span>
            </div>
            {MORE_ITEMS.map(({ label, route }) => (
              <button
                key={route}
                style={moreItemStyle}
                onClick={() => { setMoreOpen(false); navigate(route) }}
              >
                {label}
              </button>
            ))}
          </div>
        </>
      )}

      <nav
        aria-label="Bottom tab bar"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          height: 'var(--bottom-tab-height)',
          background: 'var(--bg-surface)',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          zIndex: 100,
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
      >
        {TABS.map(({ label, route, Icon }) => {
          const active = pathname === route || (route === '/today' && pathname === '/')
          return (
            <button
              key={route}
              aria-label={label}
              style={tabStyle(active)}
              onClick={() => navigate(route)}
            >
              <Icon />
              {label}
            </button>
          )
        })}
        <button
          aria-label="More"
          style={tabStyle(moreOpen)}
          onClick={() => setMoreOpen(v => !v)}
        >
          <MoreIcon />
          More
        </button>
      </nav>
    </>
  )
}
```

- [ ] **Step 4: Run tests to confirm GREEN**

```bash
npm test -- --run src/tests/BottomTabBar.test.tsx
```

Expected: 5 tests PASS

- [ ] **Step 5: Run full test suite**

```bash
npm test -- --run
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/components/layout/BottomTabBar.tsx \
        frontend/src/tests/BottomTabBar.test.tsx
git commit -m "feat: implement BottomTabBar with 5 tabs and More bottom sheet"
```

---

### Task 5: Add `/today` route + SmartRedirect in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/TodayPage.tsx` (stub — full impl in Task 6)

The root `/` redirect becomes a `SmartRedirect`: mobile → `/today`, desktop → `/calendar`.

- [ ] **Step 1: Create TodayPage stub**

```typescript
// frontend/src/pages/TodayPage.tsx
// Stub — replaced in Task 6
export function TodayPage() {
  return (
    <div style={{ padding: '16px' }}>
      <p>Today — coming soon</p>
    </div>
  )
}
```

- [ ] **Step 2: Add SmartRedirect + `/today` route to App.tsx**

In `frontend/src/App.tsx`:

1. Import `useIsMobile` and `TodayPage`
2. Replace the `<Route path="/" element={<Navigate to="/calendar" replace />} />` with:

```typescript
import { useIsMobile } from './hooks/useIsMobile'
import { TodayPage } from './pages/TodayPage'

// SmartRedirect component (add inside App.tsx above App function)
function SmartRedirect() {
  const isMobile = useIsMobile()
  return <Navigate to={isMobile ? '/today' : '/calendar'} replace />
}
```

3. Replace the root route:

```typescript
<Route path="/" element={<SmartRedirect />} />
```

4. Add the `/today` route after the root route:

```typescript
<Route
  path="/today"
  element={
    <ProtectedRoute>
      <ErrorBoundary>
        <AppShell>
          <TodayPage />
        </AppShell>
      </ErrorBoundary>
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 3: Write and run SmartRedirect test**

Create `frontend/src/tests/SmartRedirect.test.tsx`:

```typescript
// frontend/src/tests/SmartRedirect.test.tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

function mockMatchMedia(isMobile: boolean) {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: isMobile,
    media: '(max-width: 767px)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })
}

// Mock auth so ProtectedRoute doesn't redirect to login
vi.mock('../contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/AuthContext')>()
  return {
    ...actual,
    useAuth: () => ({ user: { id: 1, email: 'test@test.com' }, logout: vi.fn() }),
    AuthProvider: ({ children }: { children: import('react').ReactNode }) => <>{children}</>,
  }
})

// Suppress heavy component rendering
vi.mock('../components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: import('react').ReactNode }) => <div>{children}</div>,
}))
vi.mock('../pages/CalendarPage', () => ({ CalendarPage: () => <div>Calendar</div> }))
vi.mock('../pages/TodayPage', () => ({ TodayPage: () => <div>Today</div> }))

describe('SmartRedirect', () => {
  beforeEach(() => { mockMatchMedia(false) })

  it('SmartRedirect_onDesktop_redirectsToCalendar', async () => {
    mockMatchMedia(false)
    render(<App />)
    expect(await screen.findByText('Calendar')).toBeInTheDocument()
  })

  it('SmartRedirect_onMobile_redirectsToToday', async () => {
    mockMatchMedia(true)
    render(<App />)
    expect(await screen.findByText('Today')).toBeInTheDocument()
  })
})
```

Run:
```bash
npm test -- --run src/tests/SmartRedirect.test.tsx
```

Expected: 2 tests PASS

- [ ] **Step 4: TypeScript check**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npx tsc -b --noEmit && echo "TypeScript OK"
```

Expected: `TypeScript OK`

- [ ] **Step 5: Run full test suite**

```bash
npm test -- --run
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/App.tsx \
        frontend/src/pages/TodayPage.tsx \
        frontend/src/tests/SmartRedirect.test.tsx
git commit -m "feat: add /today route and SmartRedirect (mobile→today, desktop→calendar)"
```

---

## Chunk 3: TodayPage — mobile home screen

### Task 6: TodayPage full implementation

**Files:**
- Modify: `frontend/src/pages/TodayPage.tsx` (replace stub)
- Create: `frontend/src/tests/TodayPage.test.tsx`

**What TodayPage shows:**
1. Page header: "Today" + date subtitle
2. Week strip: Mon–Sun with dot per day (blue = planned, green = done), today circle highlighted
3. Hero card: today's upcoming workout (title, duration, "View Details" button)
4. Quick chips: Garmin status dot + value, Zones configured status
5. Yesterday card: yesterday's workout compliance badge

**Data source:** `useCalendar(weekStart, weekEnd)` for workouts + `fetchWorkoutTemplates()` for template names and durations. Both are already used by CalendarPage — no new API endpoints.

**Important field names from `api/types.ts`:**
- `ScheduledWorkout.date` (NOT `scheduled_date`)
- `ScheduledWorkoutWithActivity.activity: GarminActivity | null` (NOT `garmin_activity`)
- `GarminActivity` has no `compliance_level` field

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/src/tests/TodayPage.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { GarminStatusProvider } from '../contexts/GarminStatusContext'
import { ZonesStatusProvider } from '../contexts/ZonesStatusContext'
import { TodayPage } from '../pages/TodayPage'
import type { WorkoutTemplate } from '../api/types'

const TODAY = new Date().toISOString().split('T')[0]

const mockEasyRunTemplate: WorkoutTemplate = {
  id: 10,
  name: 'Easy Run',
  description: '45min easy',
  sport_type: 'running',
  estimated_duration_sec: 2700,
  estimated_distance_m: null,
  tags: null,
  steps: null,
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
}

// Mock API
const { mockFetchCalendar, mockGetGarminStatus, mockFetchProfile, mockFetchTemplates } = vi.hoisted(() => ({
  mockFetchCalendar: vi.fn().mockResolvedValue({ workouts: [], unplanned_activities: [] }),
  mockGetGarminStatus: vi.fn().mockResolvedValue({ connected: true }),
  mockFetchProfile: vi.fn().mockResolvedValue({ threshold_pace: 300 }),
  mockFetchTemplates: vi.fn().mockResolvedValue([]),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchCalendarRange: mockFetchCalendar,
    getGarminStatus: mockGetGarminStatus,
    fetchProfile: mockFetchProfile,
    fetchWorkoutTemplates: mockFetchTemplates,
  }
})

const renderPage = () =>
  render(
    <MemoryRouter>
      <GarminStatusProvider>
        <ZonesStatusProvider>
          <TodayPage />
        </ZonesStatusProvider>
      </GarminStatusProvider>
    </MemoryRouter>
  )

describe('TodayPage', () => {
  beforeEach(() => {
    mockFetchCalendar.mockResolvedValue({ workouts: [], unplanned_activities: [] })
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    mockFetchProfile.mockResolvedValue({ threshold_pace: 300 })
    mockFetchTemplates.mockResolvedValue([])
  })

  it('TodayPage_renders_pageHeader', async () => {
    renderPage()
    expect(await screen.findByText('Today')).toBeInTheDocument()
  })

  it('TodayPage_renders_weekStrip', async () => {
    renderPage()
    // Week strip has 7 day labels (M T W T F S S)
    await waitFor(() => {
      expect(screen.getAllByText(/^[MTWFS]$/).length).toBeGreaterThanOrEqual(5)
    })
  })

  it('TodayPage_withNoWorkout_showsRestDay', async () => {
    renderPage()
    expect(await screen.findByText(/rest day/i)).toBeInTheDocument()
  })

  it('TodayPage_withWorkout_showsHeroCard', async () => {
    // Workout uses .date (not .scheduled_date), no embedded template
    mockFetchCalendar.mockResolvedValue({
      workouts: [{
        id: 1,
        date: TODAY,                     // ← correct field name
        workout_template_id: 10,
        training_plan_id: null,
        resolved_steps: null,
        garmin_workout_id: null,
        sync_status: 'pending',
        completed: false,
        notes: null,
        created_at: TODAY,
        updated_at: TODAY,
        matched_activity_id: null,
        activity: null,
      }],
      unplanned_activities: [],
    })
    mockFetchTemplates.mockResolvedValue([mockEasyRunTemplate])
    renderPage()
    expect(await screen.findByText('Easy Run')).toBeInTheDocument()
    expect(await screen.findByText(/45:00/)).toBeInTheDocument()
  })

  it('TodayPage_garminConnected_showsGreenDot', async () => {
    renderPage()
    expect(await screen.findByLabelText(/garmin connected/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to confirm RED**

```bash
npm test -- --run src/tests/TodayPage.test.tsx
```

Expected: FAIL (stub doesn't render week strip or hero card)

- [ ] **Step 3: Implement TodayPage**

```typescript
// frontend/src/pages/TodayPage.tsx
import { useState, useMemo, useEffect } from 'react'
import type { CSSProperties } from 'react'
import { startOfWeek, addDays, format, isToday, isYesterday, isSameDay } from 'date-fns'
import { useCalendar } from '../hooks/useCalendar'
import { useGarminStatus } from '../contexts/GarminStatusContext'
import { useZonesStatus } from '../contexts/ZonesStatusContext'
import { computeDurationFromSteps, formatClock } from '../utils/workoutStats'
import { fetchWorkoutTemplates } from '../api/client'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate } from '../api/types'
import { WorkoutDetailPanel } from '../components/calendar/WorkoutDetailPanel'

function getWeekStart(date: Date): Date {
  return startOfWeek(date, { weekStartsOn: 1 }) // Monday
}

const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

export function TodayPage() {
  const today = useMemo(() => new Date(), [])
  const weekStart = getWeekStart(today)
  const weekEnd = addDays(weekStart, 6)
  const [selectedWorkout, setSelectedWorkout] = useState<ScheduledWorkoutWithActivity | null>(null)
  const [templates, setTemplates] = useState<WorkoutTemplate[]>([])

  const { workouts, loading, updateNotes } = useCalendar(weekStart, weekEnd)
  const { garminConnected } = useGarminStatus()
  const { zonesConfigured } = useZonesStatus()

  useEffect(() => {
    fetchWorkoutTemplates().then(setTemplates).catch(() => {})
  }, [])

  // Partition workouts — use .date (field name on ScheduledWorkout)
  const todayWorkout = workouts.find(w => isToday(new Date(w.date)) && !w.completed) ?? null
  const yesterdayWorkout = workouts.find(w => isYesterday(new Date(w.date))) ?? null

  // Template lookup helpers
  const findTemplate = (w: ScheduledWorkoutWithActivity) =>
    templates.find(t => t.id === w.workout_template_id)

  const todayTemplate = todayWorkout ? findTemplate(todayWorkout) : undefined
  const todayDurationSec = todayTemplate?.estimated_duration_sec
    ?? computeDurationFromSteps(todayTemplate?.steps)

  const selectedTemplate = selectedWorkout ? findTemplate(selectedWorkout) : undefined

  // Week strip dots — use .date
  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const date = addDays(weekStart, i)
    const dayWorkout = workouts.find(w => isSameDay(new Date(w.date), date))
    return { date, label: DAY_LABELS[i], dayWorkout }
  })

  const headerStyle: CSSProperties = {
    padding: '12px 16px 8px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-main)',
    flexShrink: 0,
  }

  const weekStripStyle: CSSProperties = {
    display: 'flex',
    padding: '8px 12px 6px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-surface)',
    gap: 2,
    flexShrink: 0,
  }

  const bodyStyle: CSSProperties = {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={headerStyle}>
        <div style={{ fontFamily: 'var(--font-family-display)', fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.03em' }}>
          Today
        </div>
        <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
          {format(today, 'EEEE, MMM d')}
        </div>
      </div>

      {/* Week strip */}
      <div style={weekStripStyle}>
        {weekDays.map(({ date, label, dayWorkout }, i) => {
          const isTodayDay = isToday(date)
          return (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
              <span style={{ fontFamily: 'var(--font-family-mono)', fontSize: 8, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                {label}
              </span>
              <div style={{
                width: 22, height: 22, borderRadius: '50%',
                background: isTodayDay ? 'var(--accent)' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-family-display)', fontSize: 10, fontWeight: 600,
                color: isTodayDay ? 'var(--text-on-accent)' : 'var(--text-secondary)',
              }}>
                {format(date, 'd')}
              </div>
              <div style={{
                width: 4, height: 4, borderRadius: '50%',
                background: dayWorkout?.completed
                  ? 'var(--color-success)'
                  : dayWorkout
                    ? 'var(--accent)'
                    : 'var(--border)',
              }} />
            </div>
          )
        })}
      </div>

      {/* Body */}
      <div style={bodyStyle}>
        {loading ? (
          <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-family-mono)', fontSize: 12, textAlign: 'center', paddingTop: 24 }}>
            Loading...
          </div>
        ) : (
          <>
            {/* Hero card */}
            {todayWorkout ? (
              <div style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent)', borderRadius: 10, padding: '12px 14px' }}>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 9, color: 'var(--accent)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 4 }}>
                  Today's Workout
                </div>
                <div style={{ fontFamily: 'var(--font-family-display)', fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 3 }}>
                  {todayTemplate?.name ?? 'Workout'}
                </div>
                {todayDurationSec != null && (
                  <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
                    {formatClock(todayDurationSec)}
                  </div>
                )}
                <button
                  onClick={() => setSelectedWorkout(todayWorkout)}
                  style={{ width: '100%', background: 'var(--accent)', color: 'var(--text-on-accent)', border: 'none', borderRadius: 6, padding: '8px 0', fontFamily: 'var(--font-family-display)', fontWeight: 700, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', cursor: 'pointer' }}
                >
                  View Details
                </button>
              </div>
            ) : (
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px', textAlign: 'center' }}>
                <div style={{ fontFamily: 'var(--font-family-display)', fontSize: 14, fontWeight: 700, color: 'var(--text-secondary)' }}>
                  Rest Day
                </div>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                  No workout scheduled today
                </div>
              </div>
            )}

            {/* Quick chips */}
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 10px' }}>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 8, color: 'var(--text-muted)', marginBottom: 3 }}>Garmin</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <div
                    aria-label={garminConnected ? 'Garmin connected' : 'Garmin disconnected'}
                    style={{ width: 6, height: 6, borderRadius: '50%', background: garminConnected ? 'var(--color-success)' : 'var(--color-error)', flexShrink: 0 }}
                  />
                  <span style={{ fontFamily: 'var(--font-family-display)', fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>
                    {garminConnected === null ? '—' : garminConnected ? 'Connected' : 'Not set'}
                  </span>
                </div>
              </div>
              <div style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 10px' }}>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 8, color: 'var(--text-muted)', marginBottom: 3 }}>Zones</div>
                <span style={{ fontFamily: 'var(--font-family-display)', fontSize: 11, fontWeight: 600, color: zonesConfigured ? 'var(--text-primary)' : 'var(--color-warning)' }}>
                  {zonesConfigured === null ? '—' : zonesConfigured ? 'Configured' : 'Not set'}
                </span>
              </div>
            </div>

            {/* Yesterday card */}
            {yesterdayWorkout && (
              <div>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 5 }}>
                  Yesterday
                </div>
                <div
                  style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => setSelectedWorkout(yesterdayWorkout)}
                >
                  <div style={{ fontFamily: 'var(--font-family-display)', fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>
                    {findTemplate(yesterdayWorkout)?.name ?? 'Workout'}
                  </div>
                  {/* Show "DONE" badge if matched to a Garmin activity */}
                  {yesterdayWorkout.activity && (
                    <span style={{
                      fontFamily: 'var(--font-family-mono)', fontSize: 8, fontWeight: 500,
                      padding: '2px 5px', borderRadius: 4,
                      background: 'var(--color-success-bg)',
                      color: 'var(--color-success)',
                      border: '1px solid var(--color-success-border)',
                    }}>
                      DONE
                    </span>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Detail panel — reuses existing WorkoutDetailPanel with all required props */}
      {selectedWorkout && (
        <WorkoutDetailPanel
          workout={selectedWorkout}
          activity={selectedWorkout.activity}       // ← correct field: .activity (not .garmin_activity)
          template={selectedTemplate}
          onClose={() => setSelectedWorkout(null)}
          onReschedule={() => {}}                   // TodayPage is view-only
          onRemove={() => {}}
          onUnpair={() => {}}
          onUpdateNotes={(id, notes) => updateNotes(id, notes)}
          onNavigateToBuilder={() => {}}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run TodayPage tests to confirm GREEN**

```bash
npm test -- --run src/tests/TodayPage.test.tsx
```

Expected: 5 tests PASS

- [ ] **Step 5: Run full test suite**

```bash
npm test -- --run
```

Expected: all tests pass

- [ ] **Step 6: TypeScript check**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npx tsc -b --noEmit && echo "TypeScript OK"
```

- [ ] **Step 7: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/pages/TodayPage.tsx \
        frontend/src/tests/TodayPage.test.tsx
git commit -m "feat: implement TodayPage with week strip, hero card, and compliance chips"
```

---

## Chunk 4: WorkoutDetailPanel + OnboardingWizard + HelpPage mobile

### Task 7: WorkoutDetailPanel — bottom sheet on mobile

**Files:**
- Modify: `frontend/src/components/calendar/WorkoutDetailPanel.tsx`
- Modify: `frontend/src/tests/WorkoutDetailPanel.test.tsx` (add mobile test)

On desktop: existing right-side panel (no change).
On mobile: the panel fills 75vh from the bottom using the `.workout-detail-panel-mobile` CSS class added in Task 2.

- [ ] **Step 1: Read current WorkoutDetailPanel to find its container style**

```bash
grep -n "position.*fixed\|slideInRight\|panelStyle\|container" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/components/calendar/WorkoutDetailPanel.tsx | head -30
```

Expected: lines showing `position: 'fixed'` and `slideInRight` animation

- [ ] **Step 2: Write failing mobile test**

Open `frontend/src/tests/WorkoutDetailPanel.test.tsx` and add this test inside the existing `describe` block:

```typescript
it('WorkoutDetailPanel_onMobile_usesMobileClass', () => {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: true, // mobile
    media: '(max-width: 767px)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })

  // WorkoutDetailPanel requires all these props (see WorkoutDetailPanel.tsx interface)
  render(
    <MemoryRouter>
      <WorkoutDetailPanel
        workout={mockWorkout}
        activity={null}
        template={mockTemplate}
        onClose={vi.fn()}
        onReschedule={vi.fn()}
        onRemove={vi.fn()}
        onUnpair={vi.fn()}
        onUpdateNotes={vi.fn()}
        onNavigateToBuilder={vi.fn()}
      />
    </MemoryRouter>
  )

  // Mobile panel should have the CSS class, not inline fixed-right positioning
  const panel = document.querySelector('.workout-detail-panel-mobile')
  expect(panel).toBeInTheDocument()
})
```

(Adapt `mockWorkout` to match whatever fixture is already in this test file — read it first to check the existing shape.)

- [ ] **Step 3: Run to confirm RED**

```bash
npm test -- --run src/tests/WorkoutDetailPanel.test.tsx
```

Expected: FAIL — `.workout-detail-panel-mobile` class not found

- [ ] **Step 4: Modify WorkoutDetailPanel to use mobile class**

In `WorkoutDetailPanel.tsx`, find the component's outer container (the panel `<div>` that is `position: fixed`). Import `useIsMobile` and conditionally apply either:

- Desktop: existing inline style `{ position: 'fixed', top: 0, right: isPanelOpen ? 0 : '-400px', ... }`
- Mobile: `className="workout-detail-panel-mobile"` with minimal inline override

The pattern to add at the top of the component:

```typescript
import { useIsMobile } from '../../hooks/useIsMobile'
// Inside component:
const isMobile = useIsMobile()
```

Then in the JSX, the panel container becomes:

```typescript
// Replace the desktop-only fixed panel div with:
<div
  className={isMobile ? 'workout-detail-panel-mobile' : undefined}
  style={isMobile ? undefined : {
    // ...existing desktop inline styles unchanged...
  }}
>
```

**Important:** Read the existing file fully before editing to preserve all existing functionality (backdrop, Escape key, notes debounce, etc.). Only the outermost container div changes.

- [ ] **Step 5: Run WorkoutDetailPanel tests to confirm GREEN**

```bash
npm test -- --run src/tests/WorkoutDetailPanel.test.tsx
```

Expected: all tests pass (both new mobile test and existing tests)

- [ ] **Step 6: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/components/calendar/WorkoutDetailPanel.tsx \
        frontend/src/tests/WorkoutDetailPanel.test.tsx
git commit -m "feat: WorkoutDetailPanel uses bottom sheet layout on mobile"
```

---

### Task 8: OnboardingWizard mobile — full-screen

**Files:**
- Modify: `frontend/src/components/onboarding/OnboardingWizard.tsx`
- Modify: `frontend/src/tests/OnboardingWizard.test.tsx` (add mobile test)

The wizard currently is a centered modal (`position: fixed`, `inset: 0` overlay with a centered card inside). On mobile it should be fully full-screen — the card fills the viewport with no border-radius or max-width cap.

Context from `features/onboarding/CLAUDE.md`:
- Modal pattern: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Fixed overlay `inset: 0`, `zIndex: 200`, `background: var(--overlay-bg)`
- Backdrop click does NOT close (intentional)

- [ ] **Step 1: Write failing test for mobile full-screen mode**

Open `frontend/src/tests/OnboardingWizard.test.tsx` and add this test. Use `vi.hoisted` if `mockOpen` already exists there; adapt to match the existing fixture pattern in the file.

```typescript
it('OnboardingWizard_onMobile_isFullScreen', () => {
  // Override matchMedia to simulate mobile
  window.matchMedia = vi.fn().mockReturnValue({
    matches: true, // mobile
    media: '(max-width: 767px)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })

  // Render with wizard open — adapt mock setup to match existing test helpers
  // (read existing test file first to see how `openWizard` is triggered)
  // The key assertion: wizard modal container has inset:0 (full-screen), not a max-width card
  // ...existing render setup from this test file...

  const dialog = screen.getByRole('dialog')
  // On mobile the modal fills screen — no max-width constraint
  expect(dialog).not.toHaveStyle({ maxWidth: expect.stringMatching(/px/) })
  // On mobile the modal has position: fixed, inset: 0
  expect(dialog).toHaveStyle({ position: 'fixed' })
})
```

**Important:** Read the existing `frontend/src/tests/OnboardingWizard.test.tsx` first to understand the test setup (how the wizard is opened, what mocks exist) before writing the full test body.

- [ ] **Step 2: Run to confirm RED**

```bash
npm test -- --run src/tests/OnboardingWizard.test.tsx
```

Expected: new test FAIL (wizard currently always has max-width on desktop style)

- [ ] **Step 3: Read OnboardingWizard to find its modal card styles**

```bash
grep -n "maxWidth\|borderRadius\|position\|zIndex\|modal\|dialog" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/components/onboarding/OnboardingWizard.tsx | head -25
```

Note the exact existing `style` object for the modal card (not the overlay — the overlay already fills screen; we want the card inside it to fill screen on mobile).

- [ ] **Step 4: Add `useIsMobile` and conditionally adjust modal card style**

Import `useIsMobile` and `CSSProperties` (if not already imported). Inside the component, add:

```typescript
import type { CSSProperties } from 'react'
import { useIsMobile } from '../../hooks/useIsMobile'

// Inside component:
const isMobile = useIsMobile()

// Replace the modal card's style object with:
const modalCardStyle: CSSProperties = isMobile
  ? {
      // Mobile: full-screen — fills entire viewport
      position: 'fixed',
      inset: 0,
      background: 'var(--bg-surface)',
      zIndex: 201,              // above the overlay (which is 200)
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      borderRadius: 0,
    }
  : {
      // Desktop: copy existing card style exactly from source file (read in Step 3)
      // ...existing styles unchanged...
    }
```

Apply `modalCardStyle` to the card container div. Keep the `role="dialog"` `aria-modal` attributes on the same element.

- [ ] **Step 5: Run tests to confirm GREEN**

```bash
npm test -- --run src/tests/OnboardingWizard.test.tsx src/tests/OnboardingContext.test.tsx
```

Expected: all tests pass including new mobile test

- [ ] **Step 6: Desktop regression check**

```bash
npm test -- --run && npx tsc -b --noEmit && echo "✅ Desktop OK"
```

- [ ] **Step 7: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/components/onboarding/OnboardingWizard.tsx \
        frontend/src/tests/OnboardingWizard.test.tsx
git commit -m "feat: OnboardingWizard full-screen on mobile"
```

---

### Task 9: HelpPage mobile — stacked cards + Replay Tour walkthrough

**Files:**
- Modify: `frontend/src/pages/HelpPage.tsx`
- Modify: `frontend/src/tests/HelpPage.test.tsx` (add mobile test)

HelpPage shows a grid of feature cards and a "Replay Tour" button. On mobile:
1. Feature cards grid → single column (stacked vertically)
2. Replay Tour button → full-width at top, prominent
3. The "Replay Tour" → `openWizard()` from `OnboardingContext` → opens the full-screen wizard (Task 8)
4. The Help page is accessed via More sheet → `/help` route (not a primary tab)

Context: `HelpPage.tsx` already exists with a working "Replay Tour" button via `OnboardingContext`. This task is purely about making the layout responsive.

- [ ] **Step 1: Write failing test for mobile card stacking**

Open `frontend/src/tests/HelpPage.test.tsx` and add:

```typescript
it('HelpPage_onMobile_featureCardsAreStacked', () => {
  // Override matchMedia to mobile
  window.matchMedia = vi.fn().mockReturnValue({
    matches: true,
    media: '(max-width: 767px)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })

  render(
    <MemoryRouter>
      <OnboardingProvider>
        <HelpPage />
      </OnboardingProvider>
    </MemoryRouter>
  )

  // On mobile, feature cards container should use single-column grid
  // Find the cards container — adapt selector to match actual DOM structure
  // (read existing test to see how HelpPage renders)
  const cardsContainer = document.querySelector('[data-testid="feature-cards-grid"]')
  // If data-testid doesn't exist, add it to HelpPage in Step 4 first
  expect(cardsContainer).toHaveStyle({ gridTemplateColumns: '1fr' })
})

it('HelpPage_onMobile_replayTourButtonIsVisible', () => {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: true,
    media: '(max-width: 767px)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })

  const { mockOpenWizard } = setupMocks() // adapt to existing mock pattern
  render(<HelpPage />)

  const replayBtn = screen.getByText(/replay tour/i)
  expect(replayBtn).toBeInTheDocument()
  fireEvent.click(replayBtn)
  expect(mockOpenWizard).toHaveBeenCalled()
})
```

**Important:** Read `frontend/src/tests/HelpPage.test.tsx` and `frontend/src/pages/HelpPage.tsx` first to understand existing structure before writing tests.

- [ ] **Step 2: Run to confirm RED**

```bash
npm test -- --run src/tests/HelpPage.test.tsx
```

Expected: new tests FAIL (grid not single-column on mobile yet; possibly no `data-testid` on grid)

- [ ] **Step 3: Read HelpPage.tsx to find the cards grid container**

```bash
grep -n "grid\|cards\|feature\|padding\|column" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/pages/HelpPage.tsx | head -30
```

- [ ] **Step 4: Modify HelpPage.tsx for mobile**

Import `useIsMobile` and `CSSProperties`. Find the feature cards grid container and:

```typescript
const isMobile = useIsMobile()

// Add data-testid to the grid container for testing:
// <div data-testid="feature-cards-grid" style={gridStyle}>

const gridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(280px, 1fr))',
  // ...existing gap, padding etc — copy from source...
}
```

Also add `className="mobile-page-content"` to the page's outer scrollable container so content doesn't hide behind the tab bar.

- [ ] **Step 5: Run tests to confirm GREEN**

```bash
npm test -- --run src/tests/HelpPage.test.tsx
```

Expected: all tests pass

- [ ] **Step 6: Desktop regression check**

```bash
npm test -- --run && npx tsc -b --noEmit && echo "✅ Desktop OK"
```

- [ ] **Step 7: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/pages/HelpPage.tsx \
        frontend/src/tests/HelpPage.test.tsx
git commit -m "feat: HelpPage stacked cards + full-width Replay Tour on mobile"
```

---

## Chunk 5: Responsive page audit — padding + overflow

All existing pages need small responsive padding fixes. Desktop styles are untouched. Mobile gets `padding: 12px 14px` instead of desktop's wider padding, and horizontal overflow is clipped.

### Task 11: CalendarPage mobile responsive

**Files:**
- Modify: `frontend/src/pages/CalendarPage.tsx`
- Modify: `frontend/src/components/calendar/CalendarView.tsx` (if it has fixed widths)

CalendarPage has a toolbar row with sync button and view toggle. On mobile this should stack or wrap.

- [ ] **Step 1: Read CalendarPage toolbar JSX**

```bash
grep -n "toolbar\|Sync\|week.*month\|display.*flex" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/pages/CalendarPage.tsx | head -30
```

- [ ] **Step 2: Add `useIsMobile` and wrap toolbar on mobile**

Import `useIsMobile` and make the toolbar `flexWrap: 'wrap'` on mobile. Also add `className="mobile-page-content"` to the scrollable main container so the bottom tab bar doesn't cover content.

In CalendarPage's outer `<div>` or `<main>` that wraps everything:
```typescript
const isMobile = useIsMobile()
// Add className="mobile-page-content" to the scrollable container
// Change toolbar flexWrap to: isMobile ? 'wrap' : 'nowrap'
```

- [ ] **Step 3: Run Calendar tests**

```bash
npm test -- --run src/tests/Calendar.test.tsx
```

Expected: all tests pass

- [ ] **Step 4: Desktop regression check**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npm test -- --run && npx tsc -b --noEmit && echo "✅ Desktop OK"
```

- [ ] **Step 5: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/pages/CalendarPage.tsx
git commit -m "fix: CalendarPage toolbar wraps on mobile"
```

---

### Task 10: Remaining pages responsive audit

**Note:** HelpPage is handled in Chunk 4 Task 9. This task covers: Library, Zones, Builder, PlanCoach, Settings.

**Files:**
- Modify: `frontend/src/pages/LibraryPage.tsx`
- Modify: `frontend/src/components/zones/ZoneManager.tsx`
- Modify: `frontend/src/pages/BuilderPage.tsx`
- Modify: `frontend/src/pages/PlanCoachPage.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`

For each page, the fix pattern is:
1. Read the file to find outer container's padding/max-width
2. Add `useIsMobile()`
3. Reduce horizontal padding on mobile: `padding: isMobile ? '12px 14px' : <existing>`
4. Add `className="mobile-page-content"` to the scrollable container
5. Ensure no `min-width` or `overflow: hidden` blocks mobile scroll
6. Run the existing test suite for that page → must stay GREEN
7. After each change, confirm `npm test -- --run` still passes in full

- [ ] **Step 1: LibraryPage**

```bash
grep -n "padding\|maxWidth\|overflow\|className" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/pages/LibraryPage.tsx | head -20
```

Apply `mobile-page-content` class + reduced padding. Run:
```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npm test -- --run src/tests/WorkoutLibrary.test.tsx && echo "✅ Library OK"
```

- [ ] **Step 2: ZoneManager**

ZoneManager renders the ZonesPage content. The form inputs (LTHR, threshold pace) need `width: 100%` on mobile.

```bash
grep -n "padding\|maxWidth\|width\|input" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/components/zones/ZoneManager.tsx | head -20
```

Add `useIsMobile()` in ZoneManager + full-width inputs on mobile. Run:
```bash
npm test -- --run src/tests/ZoneManager.test.tsx && echo "✅ Zones OK"
```

- [ ] **Step 3: BuilderPage**

Builder has a drag-and-drop canvas. Needs `overflowX: 'auto'` on mobile.

```bash
grep -n "padding\|maxWidth\|overflow" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/pages/BuilderPage.tsx | head -20
```

Add `useIsMobile()` + `overflowX: isMobile ? 'auto' : 'hidden'`. Run:
```bash
npm test -- --run src/tests/WorkoutBuilder.test.tsx && echo "✅ Builder OK"
```

- [ ] **Step 4: PlanCoachPage**

CSV diff table needs `overflowX: 'auto'` on mobile. File drop area should be full-width.

```bash
grep -n "padding\|overflow\|width" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/pages/PlanCoachPage.tsx | head -20
```

Run:
```bash
npm test -- --run src/tests/PlanCoach.test.tsx && echo "✅ PlanCoach OK"
```

- [ ] **Step 5: SettingsPage**

Garmin connect form should be full-width on mobile. No max-width cap.

```bash
grep -n "maxWidth\|padding\|width" \
  /Users/noa.raz/workspace/my-garmin-coach/frontend/src/pages/SettingsPage.tsx | head -20
```

- [ ] **Step 6: Final full desktop regression check**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npm test -- --run && npx tsc -b --noEmit && echo "✅ ALL DESKTOP OK"
```

Expected: every existing test passes

- [ ] **Step 7: Commit**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add frontend/src/pages/LibraryPage.tsx \
        frontend/src/pages/BuilderPage.tsx \
        frontend/src/pages/PlanCoachPage.tsx \
        frontend/src/pages/SettingsPage.tsx \
        frontend/src/components/zones/ZoneManager.tsx
git commit -m "fix: responsive padding and overflow on all pages for mobile"
```

---

## Final check

- [ ] **Run full test suite one last time**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach/frontend
npm test -- --run
```

Expected: all tests pass, no regressions

- [ ] **TypeScript build check**

```bash
npx tsc -b --noEmit && echo "TypeScript OK"
```

- [ ] **Update STATUS.md**

In `STATUS.md`, mark **Mobile Responsive** as ✅ Done and move it from In Progress.

- [ ] **Update PLAN.md feature table**

In root `PLAN.md` feature table, update Mobile Responsive row emoji to ✅.

- [ ] **Commit documentation**

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
git add STATUS.md PLAN.md
git commit -m "docs: mark mobile-responsive as complete"
```
