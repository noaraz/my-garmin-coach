# Onboarding Feature — Patterns & Gotchas

## localStorage Key Pattern
Key: `onboarding_completed_${userId}` (userId from `useAuth().user?.id`)
- **Null-guard is mandatory.** AuthContext resolves asynchronously. If userId is undefined on
  the first render, skip the localStorage check — do not write `onboarding_completed_undefined`.
- Check in `useEffect` with `userId` as a dependency, not on every render.

## Replay Tour Pattern
`HelpPage` calls `openWizard()` from `OnboardingContext`. This works because `AppShell` (which
mounts `OnboardingWizard`) is a persistent layout component that does NOT unmount on navigation.
Navigating to `/help` does NOT remount `AppShell`, so the wizard's mount-time `useEffect` does
not re-fire. Only `openWizard()` can re-show the wizard after initial mount.

When the user opens the wizard via Replay:
1. `HelpPage` calls `openWizard()` — sets `isWizardOpen = true`
2. `OnboardingWizard` resets step to 0 when it becomes visible
3. On Finish/Skip: sets localStorage key, calls `closeWizard()`

## Navigation — Handlers Not Effects
Call `useNavigate` in `handleNext`/`handleBack` directly, NOT in `useEffect`.
React 18 StrictMode double-fires effects — calling navigate in useEffect would navigate twice.
See CLAUDE.md (root) StrictMode gotcha.

## Modal Pattern
Follow `DeletePlanModal.tsx`:
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Fixed overlay `inset: 0`, `zIndex: 200`, `background: var(--overlay-bg)`
- Backdrop click does NOT close (wizard is intentional, not accidental) — no onClick on the overlay

## Sidebar — Exempt from Zero-Hex Rule
`Sidebar.tsx` is the only component exempt from the zero-hardcoded-hex rule. It uses named
constants (`SIDE_BG`, `SIDE_BORD`, etc.). The Help nav item should follow the same pattern as
existing nav items (same `navStyle` function, same icon size 15×15).

## Context Provider Location
`OnboardingProvider` is mounted in `AppShell.tsx`, wrapping both `<Sidebar>` and `{children}`.
This means it is available to all protected routes and to the sidebar.
