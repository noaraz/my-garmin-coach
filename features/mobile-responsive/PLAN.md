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
