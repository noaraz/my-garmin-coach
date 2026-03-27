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
- More sheet items (slide-up): Builder · Plan Coach · Settings · Help · Sign Out
- Sign Out calls `logout()` from `useAuth()` — closes sheet, fires logout
- More sheet uses `.mobile-bottom-sheet` CSS class (in `@media` block in `index.css`)
- Backdrop: `data-testid="more-sheet-backdrop"` for test selection
- **Test**: `BottomTabBar.test.tsx` mocks `useAuth` via `vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ logout: mockLogout }) }))`
- **Mock is load-bearing**: `BottomTabBar.tsx` calls `useAuth()` for logout. If `BottomTabBar.test.tsx` loses the `vi.mock('../contexts/AuthContext', ...)` block (e.g. from a linter revert), all 6 tests fail with "useAuth is not a function". Always restore the mock.

## CSS mobile vars
- `--bottom-tab-height: 56px` — added to existing `:root` block in `index.css` (NOT a second block)
- `--bottom-sheet-radius: 16px` — same
- `.mobile-page-content` — class for scrollable containers needing bottom padding above tab bar
- `.workout-detail-panel-mobile` — **60vh** bottom sheet for WorkoutDetailPanel (NOT 75vh)

## WorkoutDetailPanel field names (CRITICAL)
- `ScheduledWorkout.date` (NOT `scheduled_date`)
- `ScheduledWorkoutWithActivity.activity: GarminActivity | null` (NOT `garmin_activity`)
- `GarminActivity` has NO `compliance_level` field
- `WorkoutDetailPanel` requires: `onReschedule`, `onRemove`, `onUnpair`, `onUpdateNotes`, `onNavigateToBuilder`
  — pass no-ops in TodayPage since it's view-only

## OnboardingWizard Mobile
- On mobile: **90vh bottom sheet** with handle bar (8px × 40px pill, rounded, draggable feel)
- Slides up via `@keyframes slideUpSheet` (defined globally outside `@media` so inline animation styles work)
  — `animation: slideUpSheet 280ms ease`
- NOT full-screen on mobile — uses border-radius `var(--bottom-sheet-radius)` at top corners
- On desktop: existing centered modal (max-width ~540px, border-radius, shadow) — unchanged
- Wizard navigates between routes — all existing routes work with BottomTabBar

## MobileCalendarDayView
- Replaces the cramped 7-column `CalendarView` grid on mobile
- Component: `frontend/src/components/calendar/MobileCalendarDayView.tsx`
- 7-day horizontal strip: each day is a `<button>` showing abbreviated day name + date number + workout dot indicator
  - `data-testid="mobile-day-strip"`
  - `aria-label="Select YYYY-MM-DD"` + `aria-pressed={isSelected}`
  - Selected state: accent background + 2px bottom border accent
- Vertical scrollable day list below strip (`data-testid="mobile-day-list"`)
  - Workout cards: name, duration·distance in mono, activity actual stats if paired, Done/Synced badges, remove button
  - Activity cards: accent left border, name, duration·distance·pace
  - "+ Add Workout" dashed button at bottom
- `CalendarPage` holds `selectedDay: string` state — initialized to today's date string
- `handlePrev`/`handleNext` also call `setSelectedDay` to keep selection in sync when week changes
- Week/month toggle wrapped in `{!isMobile && (...)}` — completely hidden on mobile

## HelpPage Mobile
- Feature cards: `grid-template-columns: 1fr` on mobile (stacked), multi-column on desktop
- Setup steps: `flexDirection: 'column'` on mobile, `'row'` on desktop
- HelpPage is a **normal mobile-compatible page**, NOT a bottom sheet
- Replay Tour button: `openWizard()` from `OnboardingContext` — opens the OnboardingWizard (90vh bottom sheet)
- The onboarding wizard activates because `useIsMobile` returns true — no special Help logic needed

## Display Settings — SettingsPage (mobile only)

- **Where**: `SettingsPage.tsx` — added after the Garmin Connect section
- **Mobile-only guard**: `{isMobile && <div>...</div>}` — on desktop the Sidebar toggle handles theme switching
- **Hook**: `useTheme()` from `ThemeContext` — provides `{ theme, toggleTheme }`
- **Test**: `frontend/src/tests/SettingsPage.test.tsx` — uses `vi.hoisted` for `mockIsMobile` and `mockToggleTheme`; two `describe` blocks — mobile (section visible) + desktop (section absent)
- **Mock pattern**: `vi.mock('../hooks/useIsMobile', () => ({ useIsMobile: () => mockIsMobile() }))` with `mockIsMobile.mockReturnValue(true/false)` per describe block

## Date Parsing — Local Midnight Rule

`new Date("YYYY-MM-DD")` is parsed as **UTC midnight** — in non-UTC timezones this is "yesterday" in local time, breaking `isToday`/`isYesterday`/`isSameDay` comparisons.

**Fix**: Parse date-only strings as local midnight:
```ts
const [y, m, d] = dateStr.split('-').map(Number)
return new Date(y, m - 1, d)  // local midnight, not UTC
```

Applied in `TodayPage.tsx` (`parseLocalDate` helper). Same pattern needed anywhere date strings from the API are compared to local dates.

**Test fix**: Use local date format for test constants:
```ts
const now = new Date()
const TODAY = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
// NOT: new Date().toISOString().split('T')[0]  ← UTC date, wrong in UTC- timezones
```

## CalendarPage Mobile Toolbar — Two-Row Layout (added 2026-03-27)

The CalendarPage toolbar wraps to two rows on mobile (`isMobile = true`):

**Row 1 — Navigation** (`padding: '8px 14px 6px'`):
```
[‹]  [Mar 22 – 28]  [›]
```
- `<` and `>` are fixed 27×27px icon buttons
- Date `<span>` is `flex: 1; text-align: center; font-size: clamp(10px, 3.5vw, 13px)` — fluid text, never truncates
- `white-space: nowrap; overflow: hidden` prevents wrapping even for long month names

**Row 2 — Actions** (`justify-content: space-between; padding: '4px 14px 8px'; borderTop: '1px solid var(--border)'`):
```
[Today]  [• GARMIN]  [SYNC ALL]
```
- All three items: `height: 26px` — unified vertical alignment
- **Today**: `border: 1px solid var(--border-strong)`, transparent bg, muted text — ghost style
- **GARMIN dot**: uses `visibility: garminConnected === null ? 'hidden' : 'visible'` — **NOT** conditional render
  - `visibility: hidden` keeps the button in the DOM so the `justify-content: space-between` row stays stable while status loads
  - Conditional render (`{garminConnected !== null && <button>}`) causes a 3→2 child shift that jumps layout
  - **Test pattern**: `visibility: hidden` elements are excluded from a11y tree — use `document.querySelector('[aria-label*="Garmin"]')` to find them, not `screen.queryByRole`
- **SYNC ALL**: `border: 1px solid var(--accent)`, transparent bg, accent text — **outlined accent, NOT filled**
  - Using filled accent (blue bg) looked mismatched next to the ghost Today button — stick to outlined

**Why outlined for SYNC ALL on mobile**: In a space-between row with peer buttons, a heavy filled CTA dominates visually. Outlined keeps equal weight while still being distinctly blue.

**Cross-month week label**: use `sameMonth` check to decide end-date format:
```tsx
const sameMonth = start.getMonth() === end.getMonth()
return `${format(start, 'MMM d')} – ${format(end, sameMonth ? 'd' : 'MMM d')}`
// Same month: "Mar 22 – 28"  |  Cross-month: "Mar 29 – Apr 4"
```

## Desktop Regression Policy
After every task: `npm test -- --run && npx tsc -b --noEmit`
If any existing test fails, fix before proceeding. Never skip.
