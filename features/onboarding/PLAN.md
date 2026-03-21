# Onboarding Walkthrough + Help Page

## Goal
Give first-time users a guided tour of GarminCoach sections and recommend the setup sequence:
Connect Garmin → Set Zones → Build a Plan.

## Components

### OnboardingContext (`frontend/src/contexts/OnboardingContext.tsx`)
- `isWizardOpen: boolean`
- `openWizard(): void` — re-trigger from HelpPage without unmounting AppShell
- `closeWizard(): void`

### OnboardingWizard (`frontend/src/components/onboarding/OnboardingWizard.tsx`)
Modal overlay, 7 steps, each navigates to a route:

| # | Route | Title | Description |
|---|-------|-------|-------------|
| 1 | `/calendar` | Welcome to GarminCoach | Quick intro + recommended setup order |
| 2 | `/settings` | Connect Garmin | Link your Garmin account |
| 3 | `/zones` | Set Your Training Zones | Enter LTHR + threshold pace |
| 4 | `/calendar` | Your Training Calendar | Schedule workouts, use detail panel for actions |
| 5 | `/builder` | Build Workouts | Create zone-based structured workouts |
| 6 | `/library` | Workout Library | Saved templates |
| 7 | `/plan-coach` | Plan Coach | Import multi-week plan via CSV or AI |

localStorage key: `onboarding_completed_${userId}`
- Set on Skip or Finish
- Null-guard: only run check when userId is defined

### HelpPage (`frontend/src/pages/HelpPage.tsx`)
Route: `/help`
- Setup guide section: 3 numbered cards (Connect Garmin → Set Zones → Build a Plan)
- Feature overview: one card per section (same as wizard steps 2–7)
- "Replay tour" button: calls `openWizard()` from OnboardingContext

## Files Modified
- `frontend/src/components/layout/AppShell.tsx` — add OnboardingProvider + OnboardingWizard
- `frontend/src/components/layout/Sidebar.tsx` — Help nav item (? icon) between Plan Coach and Settings
- `frontend/src/App.tsx` — add `/help` route

## Tests
| Test | Expectation |
|------|-------------|
| wizard opens when localStorage key absent | isWizardOpen = true on mount |
| wizard does NOT open when key present | isWizardOpen = false on mount |
| Skip sets localStorage key and closes wizard | key set, isWizardOpen = false |
| Finish (step 7) sets key and closes wizard | key set, isWizardOpen = false |
| Next navigates to correct route | step 1→2 navigates to /settings |
| Replay opens wizard | openWizard() sets isWizardOpen = true |
| Null-guard | key `onboarding_completed_undefined` never set |

## Maintenance
When adding a new page/feature to GarminCoach:
1. Add a step to `STEPS` array in `OnboardingWizard.tsx`
2. Add a feature card in `HelpPage.tsx`
3. Update this PLAN.md
