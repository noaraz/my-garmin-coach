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
