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
- More sheet (slides up from bottom): Builder · Plan Coach · Settings · Help · Sign Out
- New `/today` route as mobile home screen — week strip, hero workout card, quick status chips
- `WorkoutDetailPanel` → bottom sheet (60vh slide-up) on mobile
- `OnboardingWizard` → 90vh bottom sheet with handle bar on mobile
- `HelpPage` → stacked cards (normal mobile page, NOT a bottom sheet)
- `CalendarPage` → `MobileCalendarDayView` on mobile (day strip + vertical list)
- All existing pages → responsive padding/overflow fixes

## Breakpoint
`< 768px` — `@media (max-width: 767px)` in CSS, `matchMedia('(max-width: 767px)')` in JS

## New Files
- `frontend/src/hooks/useIsMobile.ts`
- `frontend/src/components/layout/BottomTabBar.tsx`
- `frontend/src/pages/TodayPage.tsx`
- `frontend/src/components/calendar/MobileCalendarDayView.tsx`

## Modified Files
- `frontend/src/index.css` — mobile CSS vars + @media rules
- `frontend/src/App.tsx` — /today route + SmartRedirect
- `frontend/src/components/layout/AppShell.tsx` — mobile layout switch
- `frontend/src/components/layout/Sidebar.tsx` — aria-label on aside
- `frontend/src/components/calendar/WorkoutDetailPanel.tsx` — bottom sheet on mobile
- `frontend/src/components/onboarding/OnboardingWizard.tsx` — 90vh bottom sheet on mobile
- `frontend/src/pages/HelpPage.tsx` — stacked cards on mobile
- `frontend/src/pages/CalendarPage.tsx` — MobileCalendarDayView + selectedDay state + hide week/month toggle
- `frontend/src/pages/LibraryPage.tsx` — responsive padding
- `frontend/src/components/zones/ZoneManager.tsx` — full-width inputs on mobile
- `frontend/src/pages/BuilderPage.tsx` — overflow-x auto on mobile
- `frontend/src/pages/PlanCoachPage.tsx` — table overflow-x auto on mobile
- `frontend/src/pages/SettingsPage.tsx` — full-width form on mobile

## Test Files
- `frontend/src/tests/useIsMobile.test.ts` (new)
- `frontend/src/tests/AppShell.test.tsx` (new)
- `frontend/src/tests/BottomTabBar.test.tsx` (new — includes Sign Out test)
- `frontend/src/tests/SmartRedirect.test.tsx` (new)
- `frontend/src/tests/TodayPage.test.tsx` (new)
- `frontend/src/tests/WorkoutDetailPanel.test.tsx` (existing — add mobile test)
- `frontend/src/tests/OnboardingWizard.test.tsx` (existing — add mobile test)
- `frontend/src/tests/HelpPage.test.tsx` (existing — add mobile test)

## Constraints
- Zero backend changes
- Desktop layout unchanged — all existing tests continue to pass
- No hardcoded hex in new files — use CSS vars

## Completed Tasks
| Task | Status |
|------|--------|
| Phase 0: MD files (STATUS.md, CLAUDE.md, PLAN.md, feature folder) | ✅ |
| Chunk 1: useIsMobile hook + CSS mobile vars + AppShell mobile layout | ✅ |
| Chunk 2: BottomTabBar + More sheet + /today route | ✅ |
| Chunk 3: TodayPage (week strip, hero card, chips) | ✅ |
| Chunk 4: WorkoutDetailPanel bottom sheet + OnboardingWizard 90vh sheet + HelpPage mobile | ✅ |
| Chunk 5: All pages responsive padding/overflow audit | ✅ |
| Fix: WorkoutDetailPanel height 75vh → 60vh | ✅ |
| Fix: BottomTabBar Sign Out button (calls logout() from useAuth) | ✅ |
| Fix: BottomTabBar test — add useAuth mock + Sign Out test | ✅ |
| MobileCalendarDayView component (day strip + vertical workout list) | ✅ |
| CalendarPage: selectedDay state + MobileCalendarDayView integration | ✅ |
| CalendarPage: hide week/month toggle on mobile | ✅ |
| Display Settings section in SettingsPage (mobile only) — theme toggle | ✅ |
| Fix: TodayPage date parsing — parseLocalDate() helper for local midnight | ✅ |
| CalendarPage mobile toolbar redesign — two-row layout (nav row + action row) | ✅ |
| SYNC ALL mobile: outlined accent style (no fill) to match Today ghost button | ✅ |
| Today + SYNC ALL: unified height: 26px in action row | ✅ |
| Date font-size: clamp(10px, 3.5vw, 13px) — fluid text scaling | ✅ |
