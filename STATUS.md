# STATUS.md — GarminCoach Progress Tracker

Last updated: 2026-04-25 — v1.8.4 release

## In Progress

_(nothing)_

---

## v1.8.4 Release ✅

| Task | Status |
|------|--------|
| Preserve rescheduled workout on plan import (past_locked `<= today`) | ✅ |
| Sync `parsed_workouts` in `CalendarService.reschedule()` | ✅ |
| Fix `_get_completed_dates` to match by (name, steps_json) not name alone | ✅ |
| 665 backend tests passing, 81% coverage | ✅ |
| 340 frontend tests passing | ✅ |

---

## v1.8.3 Release ✅

| Task | Status |
|------|--------|
| Export activity data with full Garmin lap data | ✅ |
| 659 backend tests passing, 81% coverage | ✅ |
| 340 frontend tests passing | ✅ |

---

## Export Workouts ✅ (2026-04-21)

| Task | Status |
|------|--------|
| `get_activity_splits()` on adapter protocol + V1/V2 | ✅ |
| `ExportService.build_export()` — parallel Garmin fetch, best-effort | ✅ |
| `GET /api/v1/calendar/activities/export` — JSON file download | ✅ |
| `ExportModal` with `react-day-picker` range picker | ✅ |
| Export JSON button in CalendarPage toolbar | ✅ |
| 20 new tests (13 adapter, 4 service, 3 integration) | ✅ |
| 658 backend tests passing, 81% coverage | ✅ |
| 340 frontend tests passing | ✅ |

---

## v1.8.2 Release ✅

| Task | Status |
|------|--------|
| Add fetch_garmin_activity script for raw activity inspection | ✅ |
| Update garmin-fetch-activity skill | ✅ |
| All tests passing (638 backend, 334 frontend) | ✅ |
| Tagged and deployed to Render | ✅ |

---

## v1.8.1 Release ✅

| Task | Status |
|------|--------|
| Fix V2 adapter POST/PUT (use client.post/put instead of connectapi) | ✅ |
| Trim garmin-fetch-activity skill token footprint | ✅ |
| All tests passing (638 backend, 334 frontend) | ✅ |
| Tagged and deployed to Render | ✅ |

---

## v1.8.0 Release ✅

| Task | Status |
|------|--------|
| Activity refresh from Garmin (GPS drift recovery) | ✅ |
| Preview DB isolation via per-PR Neon branching | ✅ |
| All tests passing (637 backend, 334 frontend) | ✅ |
| Tagged and deployed to Render | ✅ |

---

## Preview DB Isolation ✅

Per-PR Neon branches so preview `alembic upgrade head` never touches prod.
Workflow: `.github/workflows/preview-db-isolation.yml`

| Task | Status |
|------|--------|
| GitHub secrets: `NEON_API_KEY`, `NEON_PROJECT_ID`, `RENDER_API_KEY` | ✅ |
| `.github/workflows/preview-db-isolation.yml` — create/delete Neon branch per PR | ✅ |
| `render.yaml` — comment documenting auto-injected preview `DATABASE_URL` | ✅ |
| `features/infrastructure/CLAUDE.md` — "Preview DB Isolation" section | ✅ |
| Verified: migration ran on `preview/pr-86`, `main` branch unchanged | ✅ |

---

## Activity Refresh — GPS Drift Recovery ✅

Feature: per-activity "Refresh from Garmin" button + upsert on Sync All
PR: #83 (`feature/activity-refresh`)

| Task | Status |
|------|--------|
| `get_activity()` to adapter protocol, V1, V2 | ✅ |
| Delegate through `GarminSyncService` → `SyncOrchestrator` | ✅ |
| `fetch_and_store` upsert + bounded query + `FetchResult.updated` | ✅ |
| `POST /calendar/activities/{id}/refresh` endpoint | ✅ |
| Frontend: `refreshActivity()`, `refreshOneActivity()`, `RefreshButton` | ✅ |
| Tests: 19 new tests (8 unit adapter, 3 unit fetch, 4 integration, 4 frontend) | ✅ |
| Docs: CLAUDE.md, PLAN.md, STATUS.md | ✅ |

---

## v1.7.0 Release ✅

| Task | Status |
|------|--------|
| Pre-flight checks (branch clean, tags fetched) | ✅ |
| Full test suite (621 backend + 330 frontend, 80.66% coverage) | ✅ |
| Version bump (frontend/package.json → 1.7.0) | ✅ |
| Tag + push | ⏳ |

---

## Garminconnect 0.3.x Migration ✅

Migrated from deprecated garth to python-garminconnect 0.3.x native DI OAuth.
Design spec: `docs/superpowers/specs/2026-04-14-garminconnect-03x-migration-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-14-garminconnect-03x-migration.md`

| Task | Status |
|------|--------|
| Phase 0: Update tracking docs | ✅ |
| Chunk 1: Infrastructure (protocol, exceptions, SystemConfig, admin endpoint) | ✅ |
| Chunk 2: V2 adapter, client factory, WorkoutFacade | ✅ |
| Chunk 3: Consumer migration (sync.py, garmin_connect.py, auto_reconnect.py) | ✅ |
| Chunk 4: Verification + final docs | ✅ |
| Code review fixes (auth_version DB lookup, _login_v2 exception translation, noqa) | ✅ |
| Version mismatch handling: disconnect + force reconnect on V1↔V2 token mismatch | ✅ |
| Simplify pass: `GarminAuthVersion(StrEnum)`, `get_db_auth_version()`, `clear_garmin_connection()` helpers; `client_cache.clear()` on admin toggle | ✅ |

---

## v1.6.3 Release ✅

| Task | Status |
|------|--------|
| Full test suite (603 backend + 330 frontend, 82.22% coverage) | ✅ |
| Security review (no findings) | ✅ |
| Version bump (frontend/package.json → 1.6.3) | ✅ |
| Tag + push | ⏳ |

---

## v1.6.2 Release ✅

| Task | Status |
|------|--------|
| Pre-flight checks (main, clean, Neon alembic at head) | ✅ |
| Full test suite (598 backend + 325 frontend, 81.77% coverage) | ✅ |
| Security review (no findings) | ✅ |
| Version bump (frontend/package.json → 1.6.2) | ✅ |
| Tag + push | ⏳ |

---

## v1.6.1 Release ✅

| Task | Status |
|------|--------|
| Pre-flight checks (main, clean, Neon alembic at head) | ✅ |
| Full test suite (585 backend + 325 frontend, 81.58% coverage) | ✅ |
| Security review (no findings ≥ 80) | ✅ |
| Fix: backend _zone_label open target_type guard | ✅ |
| Version bump (frontend/package.json → 1.6.1) | ✅ |
| Tag + push | ⏳ |

---

## Calendar UX Improvements ✅

| Task | Status |
|------|--------|
| Persist month/week view preference in localStorage | ✅ |
| Search bar in WorkoutPicker modal (name filter) | ✅ |

---

## v1.6.0 Release ✅

| Task | Status |
|------|--------|
| Pre-flight checks (main, clean, Neon alembic at head) | ✅ |
| Full test suite (585 backend + 310 frontend, 82% coverage) | ✅ |
| Version bump (frontend/package.json → 1.6.0) | ✅ |
| Tag + push | ✅ |

---

## Calendar-Based Sync Reconciliation ✅

| Task | Status |
|------|--------|
| Fix Render logging (app logger not visible) | ✅ |
| `get_calendar_items` through adapter → sync_service → orchestrator | ✅ |
| `find_unscheduled_workouts` in `dedup.py` (TDD, 6 unit tests) | ✅ |
| Calendar-based reconciliation with re-schedule path in `sync_all` | ✅ |
| `rescheduled` field in `SyncAllResponse` + frontend `types.ts` | ✅ |
| Integration tests updated (38/38 pass) | ✅ |
| Calendar column (`CAL ✓` / `CAL ✗`) in compare script | ✅ |
| Fix: Garmin calendar API uses 0-indexed months | ✅ |
| `unschedule_workout` through all 3 layers | ✅ |
| `find_duplicate_calendar_entries` in `dedup.py` (TDD, 7 unit tests) | ✅ |
| Duplicate calendar entry cleanup in `sync_all` | ✅ |
| Full test suite: 576 backend + 310 frontend pass, 82% coverage | ✅ |
| Docs wrap-up | ✅ |

Supersedes template-based reconciliation from 2026-03-31.

---

## v1.6.0 — Refresh Token Rotation + Auto-Login ✅

### Refresh Token Rotation + Auto-Login
| Task | Status |
|------|--------|
| Phase 0: Docs update | ✅ |
| Phase 1: RefreshToken model + Alembic migration | ✅ |
| Phase 2: Backend TDD (jwt, schemas, service, routers) | ✅ |
| Phase 3: Frontend TDD (client.ts, AuthContext, logout callers, SettingsPage) | ✅ |
| Phase 4: Verification (564 backend + 309 frontend tests pass) | ✅ |
| Phase 5: Docs wrap-up | ✅ |
| Phase 6: Code review fixes (isLoading race, theft commit, delete_cookie attrs, handleSignOutAll nav) | ✅ |

---

## v1.5.0 Release ✅

### v1.5.0 Release
| Task | Status |
|------|--------|
| Garmin auto-reconnect with encrypted credentials (30-day expiry) | ✅ |
| Exchange 429 storm prevention (early-exit, 30-min cooldown, client cache) | ✅ |
| Reconnect prompt for existing users without stored credentials | ✅ |
| 33 new unit tests (auto_reconnect, client_cache, encryption, exchange_429) | ✅ |
| Migration: add garmin credential fields (g2a3b4c5d678) | ✅ |
| Bump frontend/package.json to 1.5.0 | ✅ |
| Tag v1.5.0 + push | ✅ |

---

## v1.4.2 Release ✅

### v1.4.2 Release
| Task | Status |
|------|--------|
| Redesigned mobile calendar toolbar into two-row layout | ✅ |
| Fixed all 404 variants in `_is_garmin_404` to unblock stuck syncs | ✅ |
| Fixed token persistence tests to use configured secret key | ✅ |
| Bump frontend/package.json to 1.4.2 | ✅ |
| Tag v1.4.2 + push | ✅ |

---

## Previous: Garmin Auto-Reconnect + Exchange 429 Fix ✅

| Task | Status |
|------|--------|
| Phase 0: Commit design spec + update docs | ✅ |
| Phase 1: Exchange storm prevention (early-exit, cooldown, client cache) | ✅ |
| Phase 2: Auto-reconnect with encrypted credentials | ✅ |
| Phase 3: Frontend 30-day expiry UX | ✅ |
| Phase 4: Tests (33 new unit tests) | ✅ |
| Phase 5: Post-implementation docs + skill update | ✅ |
| Phase 6: Reconnect prompt for existing users | ✅ |

---

## Previous Focus: Mobile Calendar Toolbar Redesign ✅

### Mobile Calendar Toolbar Redesign
| Task | Status |
|------|--------|
| Split single-row toolbar into two rows on mobile (nav row + action row) | ✅ |
| Row 1: `[‹] [date — clamp() fluid text] [›]` — centered date, full-width | ✅ |
| Row 2: `[Today] [• GARMIN] [SYNC ALL]` — space-between, consistent heights | ✅ |
| SYNC ALL: change from filled accent to outlined accent (border + text, no fill) | ✅ |
| Today + SYNC ALL: unified `height: 26px` so both rows are vertically balanced | ✅ |
| Date font-size: `clamp(10px, 3.5vw, 13px)` — scales with viewport width | ✅ |
| Garmin dot: `visibility:hidden` while loading (layout stable, no shift) | ✅ |
| Fix: cross-month week label includes end month name ("Mar 29 – Apr 4") | ✅ |
| Tests: cross-month label + Garmin layout stability (4 new tests) | ✅ |

---

## Garmin Sync 404 Hotfix ✅

### Garmin Sync — Stale ID 404 Fix
| Task | Status |
|------|--------|
| Fix `_is_garmin_404` three-tier detection (GarthHTTPError → curl_cffi → string fallback) | ✅ |
| Add test for curl_cffi unwrapped 404 path | ✅ |
| Update `features/garmin-sync/CLAUDE.md` with three-tier docs + stale ID recovery guide | ✅ |
| Update root CLAUDE.md dedup section | ✅ |
| PR #68 open with Render Preview | ✅ |

---

## v1.4.1 Release

### v1.4.1 Release
| Task | Status |
|------|--------|
| Fix: document alembic unknown-revision recovery procedure | ✅ |
| Fix: add Neon pre-flight alembic check to /release workflow | ✅ |
| Improve alembic-migration skill with recovery procedure + pre-release check | ✅ |
| Bump frontend/package.json to 1.4.1 | ✅ |
| Tag v1.4.1 + push | ✅ |

---

### v1.4.0 Release ✅
| Task | Status |
|------|--------|
| Workout removal confirmation dialog | ✅ |
| Today button on calendar toolbar | ✅ |
| Fix: persist Garmin OAuth2 token across restarts | ✅ |
| Fix: reconcile stale Garmin workout IDs on sync | ✅ |
| Bump frontend/package.json to 1.4.0 | ✅ |
| Tag v1.4.0 + push | ✅ |

---

## Current Focus: Garmin Token Persist + Sync From Panel ✅

### Garmin OAuth2 Token Persistence + Sync-From-Panel
| Task | Status |
|------|--------|
| Fix: `_persist_refreshed_token()` — persist garth OAuth2 token to DB after sync to prevent 429 storm | ✅ |
| Typed 404 detection: `GarthHTTPError` + `_is_garmin_404()` helper | ✅ |
| Remove dead calendar reconciliation (Garmin GET /schedule/{id} returns 404 always) | ✅ |
| Add `syncOneWorkout` to `useCalendar` hook | ✅ |
| Add `onSync` prop + "Sync to Garmin" button to `WorkoutDetailPanel` | ✅ |
| Wire `onSync` in `CalendarPage` and `TodayPage` (no garminConnected guard) | ✅ |
| `unsynced_workouts.py` diagnostic script (supports prod via DATABASE_URL) | ✅ |
| Tests: token persistence, sync-from-panel (hook + panel + calendar), typed 404 | ✅ |
| Fix dedup 404 path: move `return None` inside `else` so 404 falls through to push | ✅ |
| Add `dump_token()` through all three layers (Adapter → SyncService → Orchestrator) | ✅ |
| Fix `_persist_refreshed_token` to use `sync_service.dump_token()` (not `.adapter`) | ✅ |
| Add `cache.invalidate()` after token persist commit | ✅ |

---

## Current Focus: Calendar Today Button

### Calendar Today Button
| Task | Status |
|------|--------|
| Update docs (STATUS.md, calendar PLAN.md, calendar CLAUDE.md) | ✅ |
| Write Today button tests (TDD RED) | ✅ |
| Implement Today button (GREEN) | ✅ |
| Run all tests + TypeScript build | ✅ |
| Final docs update | ✅ |

---

## Current Focus: Workout Removal Confirmation ✅

### Workout Removal Confirmation
| Task | Status |
|------|--------|
| Update docs (STATUS.md, features/calendar/PLAN.md, features/calendar/CLAUDE.md) | ✅ |
| Write RemoveWorkoutModal tests (TDD RED) | ✅ |
| Create RemoveWorkoutModal component (GREEN) | ✅ |
| Wire CalendarPage confirmation state | ✅ |
| Simplify WorkoutDetailPanel (remove window.confirm) | ✅ |
| Update Calendar + WorkoutDetailPanel tests | ✅ |
| Run all tests + TypeScript build | ✅ |
| Final docs update + commit + push | ✅ |

## Backlog

| Task | Priority | Notes |
|------|----------|-------|
| Test Run → Zone Update | Medium | Tag a completed workout as zone test, auto-update thresholds from Garmin activity data |
| Rate Limiting on Auth Routes | Medium | `slowapi` on login/register — required before public access |
| ESLint v9 → v10 upgrade | Low | 5 moderate `brace-expansion` CVEs (dev-only). Breaking change, may need lint config updates. After upgrade, restore `--audit-level=moderate` in `.github/workflows/ci.yml` |
| Activity Feed / History | Low | Show completed Garmin activities beyond scheduled workouts |

---

## Current Focus: v1.3.2 Release ✅

### v1.3.2 Release
| Task | Status |
|------|--------|
| Fix Garmin workout duplication on reschedule | ✅ |
| Chrome TLS facade for all Garmin API calls + Akamai exchange fix | ✅ |
| Coverage gate 80%, activity fetch integration tests, Playwright E2E suite | ✅ |
| Fix reschedule sets sync_status=modified + mobile day strip navigation | ✅ |
| Security: sanitize fetch_error, bound fetch_days, enforce GOOGLE_CLIENT_ID in prod | ✅ |
| Tag v1.3.2 + push | ✅ |

---

## Current Focus: Garmin Sync Dedup ✅

### Garmin Duplication Fix + Dedup
| Task | Status |
|------|--------|
| Fix orphan bug in `_sync_and_persist` — skip push when delete fails, retain garmin_workout_id | ✅ |
| Add `get_workouts()` to GarminAdapter + GarminSyncService + SyncOrchestrator | ✅ |
| Build dedup matching service (`garmin/dedup.py`) — name-based matching | ✅ |
| Wire dedup into `sync_all` — link existing Garmin workouts before push | ✅ |
| Add orphan cleanup sweep in `sync_all` — delete untracked Garmin workouts matching our templates | ✅ |
| Wire dedup into `commit_plan` — pre-link new SWs to existing Garmin workouts | ✅ |
| Tests: 14 new tests (unit + integration), all 481 passing, 82% coverage | ✅ |

---


## Current Focus: Garmin 429 Fix — Chrome TLS Facade ✅

### Garmin API 429 Fix
| Task | Status |
|------|--------|
| Phase 0: Update docs (STATUS.md, CLAUDE.md, PLAN.md, feature docs, skill) | ✅ |
| Extract ChromeTLSSession to shared client_factory.py (TDD) | ✅ |
| Refactor garmin_connect.py to use create_login_client() | ✅ |
| Refactor sync.py to use create_api_client() | ✅ |
| Update feature CLAUDE.md — correct "Only login is affected" | ✅ |
| Run revise-claude-md on all touched CLAUDE.md files | ✅ |

---

## Known Issues Cleanup ✅

### Cleanup Tasks
| Task | Status |
|------|--------|
| Add coverage gate task to STATUS.md | ✅ |
| Fix Ruff E402 in calendar.py + F821 in test_api_calendar.py | ✅ |
| Backend coverage gate: write tests to reach 80%+, restore gate from 79 → 80 | ✅ |
| Activity Fetch: integration tests (fetch/match counts, unplanned activities, pair/unpair edge cases) | ✅ |
| Playwright E2E: install + configure + write 7 critical journey tests | ✅ |

---

## Current Focus: Reschedule Fix ✅

### Reschedule Fix
| Task | Status |
|------|--------|
| Backend: `reschedule()` sets `sync_status="modified"` when date changes (was "synced") | ✅ |
| Frontend: mobile reschedule navigates day strip to new date | ✅ |
| Backend tests: 5 cases covering date change, notes-only, same-date, pending, failed | ✅ |
| Frontend tests: mobile reschedule navigation test | ✅ |
| Security: pin urllib3>=2.6.3 (CVE-2026-21441) | ✅ |

---

## Current Focus: Calendar Sun-Sat Week Start ✅

### Calendar Month View Sun-Sat
| Task | Status |
|------|--------|
| Change month view week start from Monday to Sunday | ✅ |
| Update calendar tests for Sun-Sat layout | ✅ |
| PR #58 merged — v1.3.1 released | ✅ |

---

## Current Focus: Garmin SSO — Akamai Fix ✅

### Garmin SSO Akamai Bot Detection
| Task | Status |
|------|--------|
| Diagnose 429 on Garmin login — Akamai blocks Python requests TLS fingerprint | ✅ |
| Confirm Fixie proxy routes correctly (CONNECT logs in Fixie dashboard) | ✅ |
| Compare login approaches via test_garmin_login.py | ✅ |
| Implement `_ChromeTLSSession(impersonate="chrome120")` — no proxy needed | ✅ |
| Retry flow: attempt 1 no proxy, attempt 2 Fixie fallback on 429 | ✅ |
| Add meaningful logs to Garmin connect flow | ✅ |
| Update all CLAUDE.md / PLAN.md / STATUS.md docs | ✅ |
| PR #56 merged — v1.3.0 released | ✅ |

---

## Current Focus: Claude Code Automation Suite ✅

### Claude Code Automation
| Task | Status |
|------|--------|
| MCP servers: context7, github, postgres, playwright, memory (.mcp.json) | ✅ |
| Hooks: post-edit lint (ruff, tsc), pre-edit guard (.env block) | ✅ |
| Agents: dependency-auditor, e2e-test-writer, migration-validator, schema-sync, security-auditor | ✅ |
| Skills: alembic-migration, api-contract-check, coverage-gate, env-var-audit, new-feature | ✅ |
| Plugin: garmincoach plugin.yaml | ✅ |
| CI: coverage gate lowered to 79% (restore to 80% — see Cleanup Tasks) | ✅ |

---

## Current Focus: Zones UX — Auto-Recalculate on Save ✅

### Zones Simplification
| Task | Status |
|------|--------|
| Remove standalone Recalculate / Update from Threshold buttons | ✅ |
| HRZoneTable: make BPM cells display-only (remove click-to-edit) | ✅ |
| ZoneManager.handleSave: auto-call recalcHR + recalcPace after save | ✅ |
| Update ZoneManager tests | ✅ |

---

## Current Focus: Mobile Responsive ✅

Visual design: `frontend/public/mobile-mockup.html` (open in browser to see all screens)
Implementation plan: `docs/superpowers/plans/2026-03-21-mobile-responsive.md`
Feature docs: `features/mobile-responsive/`

### Mobile Responsive
| Task | Status |
|------|--------|
| Phase 0: MD files (STATUS.md, CLAUDE.md, PLAN.md, feature folder) | ✅ |
| Chunk 1: useIsMobile hook + CSS mobile vars + AppShell mobile layout | ✅ |
| Chunk 2: BottomTabBar + More sheet + /today route | ✅ |
| Chunk 3: TodayPage (week strip, hero card, chips) | ✅ |
| Chunk 4: WorkoutDetailPanel bottom sheet + OnboardingWizard 90vh sheet + HelpPage mobile page | ✅ |
| Chunk 5: All pages responsive padding/overflow audit | ✅ |
| Fix: WorkoutDetailPanel height 75vh → 60vh | ✅ |
| Fix: BottomTabBar Sign Out button in More sheet | ✅ |
| MobileCalendarDayView: day strip + vertical workout/activity list | ✅ |
| CalendarPage: hide week/month toggle on mobile | ✅ |
| Display Settings section in SettingsPage (mobile only) — theme toggle | ✅ |
| Fix: TodayPage date parsing uses local midnight (was UTC, broke in non-UTC timezones) | ✅ |

---

## Current Focus: Onboarding + Help Page ✅

Design spec: `docs/superpowers/specs/` (brainstorming session)
Feature docs: `features/onboarding/`

### Onboarding Walkthrough + Help Page ✅
| Task | Status |
|------|--------|
| Create features/onboarding/ PLAN.md + CLAUDE.md | ✅ |
| OnboardingContext.tsx (isWizardOpen, openWizard, closeWizard) | ✅ |
| OnboardingWizard.tsx — 7-step modal tour, localStorage flag, live navigation | ✅ |
| AppShell: OnboardingProvider + OnboardingWizard | ✅ |
| HelpPage.tsx — setup guide + feature overview + Replay Tour | ✅ |
| App.tsx: /help route | ✅ |
| Sidebar: Help nav item (? icon) between Plan Coach and Settings | ✅ |
| Tests: OnboardingContext (3), OnboardingWizard (7), HelpPage (5) | ✅ |
| Update STATUS.md + root CLAUDE.md | ✅ |

---

## Current Focus: Plan Coach

Design spec: `docs/superpowers/specs/2026-03-17-plan-coach-design.md`
Implementation plan: `docs/superpowers/plans/indexed-twirling-phoenix.md`

### Plan Coach — Phase 0: Scaffold ✅
| Task | Status |
|------|--------|
| Update design spec with final decisions | ✅ |
| Create features/plan-coach/PLAN.md + CLAUDE.md | ✅ |
| Update STATUS.md | ✅ |
| Update root CLAUDE.md (revise-claude-md) | ✅ |
| Update root PLAN.md | ✅ |

### Plan Coach — Phase 1: Backend ✅
| Task | Status |
|------|--------|
| TrainingPlan model + training_plan_id FK on ScheduledWorkout | ✅ |
| Alembic migration: add_training_plan | ✅ |
| plan_step_parser.py (pure, 96% coverage) | ✅ |
| plan_import_service.py (validate, commit, delete, get_active) | ✅ |
| plans.py router (validate, commit, active, delete) | ✅ |
| Unit tests: test_plan_step_parser.py (32 tests) | ✅ |
| Integration tests: test_api_plans.py (19 tests) | ✅ |

### Plan Coach — Phase 2: CSV Import UI `feature/plan-coach-phase-2` ✅
| Task | Status |
|------|--------|
| PlanCoachPage.tsx + /plan-coach route | ✅ |
| CsvImportTab.tsx + ValidationTable.tsx + LlmPromptTemplate.tsx | ✅ |
| API client functions + types | ✅ |
| Sidebar nav item | ✅ |
| RTL tests | ✅ |

### Plan Coach — Phase 3: Active Plan View + Re-import Diff `feature/plan-coach-phase-3` ✅
| Task | Status |
|------|--------|
| ActivePlanCard.tsx + DeletePlanModal.tsx + DiffTable.tsx | ✅ |
| CsvImportTab: DiffTable + Apply Changes button | ✅ |
| PlanCoachPage: active plan state + delete modal | ✅ |
| Plan badge on WorkoutCard + TemplateCard | ✅ |
| CalendarPage: fetch active plan name for badges | ✅ |
| RTL tests (17 new tests, 29 total in PlanCoach.test.tsx) | ✅ |

---

## Current Focus: Status Indicators

Design spec: `docs/superpowers/specs/2026-03-20-garmin-status-indicator-design.md`
Implementation plan: `docs/superpowers/plans/2026-03-20-garmin-status-indicators.md`

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

### Plan Coach — Phase 4: Chat (Gemini Flash) `feature/plan-coach-phase-4` ✅
| Task | Status |
|------|--------|
| PlanCoachMessage model + alembic migration | ✅ |
| gemini_client.py + plan_coach_service.py | ✅ |
| Chat API endpoints (history + message) | ✅ |
| ChatTab.tsx (thread, plan detection, validate/commit flow) | ✅ |
| Unit + integration + RTL tests | ✅ |

### Plan Coach — Phase 4b: Prompt Builder (replaces Chat tab) `feature/plan-coach-phase-4` ✅
| Task | Status |
|------|--------|
| Hide Chat tab — PlanCoachPage simplified to CSV-only flow | ✅ |
| PlanPromptBuilder.tsx — form-driven prompt generator | ✅ |
| CsvImportTab uses PlanPromptBuilder instead of LlmPromptTemplate | ✅ |
| Prompt includes "output CSV only, no markdown" instruction | ✅ |
| ActivePlanCard: rename "Upload New Plan" → "Upload / Update Plan" | ✅ |
| Frontend tests: fix tab-bar + empty state text for Phase 4b changes | ✅ |

### Plan Coach — Phase 6: Prompt Improvements `feature/plan-coach-prompt-improvements` ✅
| Task | Status |
|------|--------|
| Update all MD files (STATUS.md, PLAN.md, CLAUDE.md, feature docs) | ✅ |
| `buildPrompt()` — rolling 2–3 week horizon, health notes param, re-run note, 14-day activity label | ✅ |
| Remove `useEffect` auto-fetch; add `handleFetchActivities` with `fetchState` state machine | ✅ |
| Add health textarea (after long run day select) | ✅ |
| Add fetch button + inline feedback badge (above generated prompt) | ✅ |
| Remove old "Recent training included in prompt" summary block | ✅ |
| Code review fixes: `'error'` state in catch, date window off-by-one (-13), label casing | ✅ |

### Plan Coach — Phase 7: Validation Template Status Column ✅
| Task | Status |
|------|--------|
| Backend: ValidateRow.template_status, validate_plan query, integration test | ✅ |
| Frontend: ValidationTable Library column, NEW badge, 3 RTL tests | ✅ |

### Plan Coach — Bugfix: rescheduled workout incorrectly removed on plan import ✅
| Task | Status |
|------|--------|
| Fix `_compute_diff` + `commit_plan`: `< today` → `<= today` so today's workouts are past_locked | ✅ |
| Fix `CalendarService.reschedule()`: sync `parsed_workouts` JSON when workout date changes | ✅ |
| Unit test: `test_today_workout_not_in_new_plan_is_past_locked` | ✅ |
| Unit tests: `test_reschedule_updates_plan_parsed_workouts`, `test_reschedule_no_plan_does_not_raise` | ✅ |
| Docs: features/plan-coach/CLAUDE.md updated | ✅ |

### Plan Coach — Phase 5: Smart Plan Merge `feature/smart-plan-merge` ✅
| Task | Status |
|------|--------|
| Docs: PLAN.md, CLAUDE.md, STATUS.md, root CLAUDE.md | ✅ |
| Backend: enrich WorkoutDiff + DiffResult schema | ✅ |
| Backend: _compute_diff with completed_dates + 5 buckets | ✅ |
| Backend: validate_plan completed_dates query | ✅ |
| Backend: commit_plan smart merge (batch load, classify, bulk delete) | ✅ |
| Backend unit tests: _compute_diff (3 tests) | ✅ |
| Backend integration tests: commit_plan smart merge (3 tests) | ✅ |
| Frontend: WorkoutDiff + DiffResult types | ✅ |
| Frontend: DiffTable — 5 row variants + before→after changed | ✅ |
| Frontend: DiffTable RTL tests (4 tests) | ✅ |
| **Code review fix**: chat transaction safety — call Gemini before any DB commit | ✅ |
| **Code review fix**: bulk UPDATE training_plan_id on kept ScheduledWorkouts | ✅ |
| **Code review fix**: remove wasted session.refresh() calls after commit | ✅ |
| **SDK upgrade**: google-generativeai → google-genai>=1.0 (genai.Client, gemini-2.0-flash-lite) | ✅ |
| plan_step_parser: accept `+` as top-level step separator (LLM output format) | ✅ |
| calendar_service: detect distance steps by key presence (plan-imported steps) | ✅ |
| **Template dedup fix**: deduplicate by (name + steps JSON) instead of name-only — same name + same steps → single shared template; same name + different steps → separate templates | ✅ |

### Workout Detail Panel (previous focus) ✅
| Task | Status |
|------|--------|
| Docs: root PLAN.md, CLAUDE.md, feature docs, STATUS.md | ✅ |
| Backend: extend PATCH /calendar/{id} for notes | ✅ |
| Frontend: WorkoutDetailPanel shell (overlay, slide, close) | ✅ |
| Frontend: WorkoutDetailPlanned content | ✅ |
| Frontend: WorkoutDetailCompleted content | ✅ |
| Frontend: WorkoutDetailUnplanned content | ✅ |
| Frontend: Card click → panel (replace builder navigation) | ✅ |
| Frontend: CalendarPage panel state + render | ✅ |
| Frontend: Notes save (debounced, useCalendar hook) | ✅ |
| Frontend: Tests | ✅ |

### Activity Fetch (previous focus)
| Task | Status |
|------|--------|
| GarminActivity model + alembic migration | ✅ |
| Extract GarminAdapter to shared module | ✅ |
| Compliance utility (frontend + backend) | ✅ |
| ActivityFetchService (fetch/dedup/match) | ✅ |
| API: pair/unpair endpoints, CalendarResponse wrapper | ✅ |
| Bidirectional sync (extend sync/all) | ✅ |
| Frontend: types, client, useCalendar hook updates | ✅ |
| Frontend: WorkoutCard compliance colors | ✅ |
| Frontend: UnplannedActivityCard component | ✅ |
| Frontend: auto-sync on mount, reschedule action | ✅ |
| Integration tests | ✅ |

---

### Infrastructure
| Task | Status |
|------|--------|
| Repo structure + pyproject.toml | ✅ |
| backend/Dockerfile + docker-compose.yml | ✅ |
| Minimal FastAPI health check | ✅ |
| .env.example + .gitignore | ✅ |
| docker compose up works | ✅ |
| pytest runs in container | ✅ |
| Add alembic to pyproject.toml (main deps, not dev-only) | ✅ |
| alembic init + configure env.py (models + sync URL) | ✅ |
| Generate initial migration (creates all 7 tables from scratch) | ✅ |
| Apply migration to local Docker volume DB | ✅ |
| Dockerfile.prod CMD: alembic upgrade head on startup (before uvicorn) | ✅ |
| GitHub Actions: CI workflow (tests on push/PR) | ✅ |
| GitHub Actions: Release workflow with approval gate + Render deploy hook | ✅ |
| Release notes extracted from tag annotation into GitHub Release | ✅ |
| pip-audit: document + ignore CVE-2024-23342 (ecdsa, no fix available) | ✅ |
| Security review + fixes (ownership checks, exception leakage) | ✅ |
| HTTP security headers (nginx CSP/HSTS/X-Frame + FastAPI middleware) | ✅ |
| Fix: SPA routing in production (FastAPI catch-all + NODE_ENV=development in Dockerfile.prod) | ✅ |
| **Bootstrap endpoint**: POST /api/v1/auth/bootstrap — creates first user + 5 invite codes, locked after first user exists (Render free plan has no Shell access) — see `features/auth/CLAUDE.md` | ✅ |
| First deploy to Render (connect GitHub → Render dashboard) | ✅ |
| Verify Render: login + profile + Garmin connect | ✅ |
| Tag v0.1.0 + push (triggers CI gate → GitHub Release → Render deploy) | ✅ |
| Tag v0.1.1 + push (SPA routing fix + Calendar test reliability) | ✅ |
| Tag v0.2.0 + push (Google OAuth, admin bootstrap, invite system, security hardening) | ✅ |
| Fix: pass GOOGLE_CLIENT_ID as VITE_GOOGLE_CLIENT_ID in prod Docker build | ✅ |
| Fix: Google tokeninfo endpoint for audience validation (azp claim, not aud on userinfo) | ✅ |
| Tag v0.2.1 + push (Google OAuth audience validation hotfix) | ✅ |
| Fix: remove create_db_and_tables() from lifespan — alembic is sole schema authority | ✅ |
| Fix: add InviteCode to alembic/env.py model imports (autogenerate misses it) | ✅ |
| Fixie proxy for Garmin OAuth in production (avoids 429 from shared datacenter IPs) | ✅ |
| Tag v0.2.2 + push (Fixie proxy) | ✅ |
| Security hardening: ProxyError handler, fixie_url validation, test isolation fixes | ✅ |
| Tag v0.2.3 + push (proxy security hardening) — deployed to Render ✅ | ✅ |
| Pre-release security fixes (PR #41): zone cache dicts, Gemini ValueError, IDOR, session concurrency, unpair completed | ✅ |
| Tag v1.0.0 + push — first public release, GitHub Release created, deployed to Render ✅ | ✅ |
| Tag v1.0.1 + push — sidebar version sync, security fixes | ✅ |
| Tag v1.1.0 + push — mobile responsive, plan coach improvements, Garmin pairing fix | ✅ |
| Tag v1.2.0 + push — Neon PostgreSQL migration, performance optimizations, caching | ✅ |
| Tag v1.3.0 + push — Akamai bot-detection bypass (curl_cffi chrome120), 429 retry flow | ✅ |
| Tag v1.3.1 + push — Sun-Sat week start, /release automation, reschedule sync fix | ✅ |
| Tag v1.3.2 + push — Garmin sync dedup, Chrome TLS facade, E2E tests, security hardening | ✅ |
| Tag v1.4.0 + push — workout confirmation dialog, Today button, Garmin token persist, sync-from-panel | ✅ |
| Migrate production DB to Neon PostgreSQL (fix Render ephemeral storage loss) | ✅ |
| Add asyncpg + psycopg2-binary drivers + fix alembic URL stripping for PostgreSQL | ✅ |
| Unit tests: alembic URL normalization for both SQLite and PostgreSQL | ✅ |
| Integration tests: TEST_DATABASE_URL env var support in conftest.py | ✅ |
| Fix: naive UTC datetimes in User/InviteCode models (PostgreSQL TIMESTAMP WITHOUT TIME ZONE) | ✅ |
| **Neon optimization**: Connection pool tuning (pool_pre_ping, pool_recycle) | ✅ |
| **Neon optimization**: Bulk DELETE in zone repositories | ✅ |
| **Neon optimization**: Fix N+1 in _cascade_re_resolve (batch template load) | ✅ |
| **Neon optimization**: Fix N+1 in sync router (preload templates) | ✅ |
| **Neon optimization**: Batch auth operations (bootstrap invites, reset_admins) | ✅ |
| **Neon optimization**: In-memory TTL cache (User, Profile, Zones) | ✅ |

### Zone Engine
| Task | Status |
|------|--------|
| models.py (Zone, ZoneConfig, ZoneSet) | ✅ |
| Tests: test_hr_zones.py | ✅ |
| Implement: hr_zones.py | ✅ |
| Tests: test_pace_zones.py | ✅ |
| Implement: pace_zones.py | ✅ |
| Coverage >95% | ✅ |

### Workout Resolver
| Task | Status |
|------|--------|
| models.py (WorkoutStep, ResolvedStep) | ✅ |
| Tests: test_workout_resolver.py | ✅ |
| Implement: resolver.py | ✅ |
| Tests: test_workout_estimator.py | ✅ |
| Implement: estimator.py | ✅ |

### Garmin Sync
| Task | Status |
|------|--------|
| garmin/constants.py | ✅ |
| Tests: test_garmin_converters.py | ✅ |
| Implement: converters.py | ✅ |
| Tests: test_garmin_formatter.py | ✅ |
| Implement: formatter.py | ✅ |
| Tests: test_garmin_sync.py (mocked) | ✅ |
| Implement: sync_service.py + session.py | ✅ |
| Implement: sync_orchestrator.py | ✅ |

### Database + API
| Task | Status |
|------|--------|
| db/models.py (SQLModel tables) | ✅ |
| db/database.py | ✅ |
| Tests: test_db.py | ✅ |
| Tests: test_api_profile.py | ✅ |
| Tests: test_api_zones.py | ✅ |
| Tests: test_api_workouts.py | ✅ |
| Tests: test_api_calendar.py | ✅ |
| Tests: test_api_sync.py | ✅ |
| Implement: services + routers | ✅ |
| Zone change cascade | ✅ |
| Async migration (aiosqlite + AsyncSession) | ✅ |
| Repository layer (BaseRepository + domain repos) | ✅ |
| BaseSettings config (pydantic-settings) | ✅ |
| CORS middleware + /api/v1/ prefix | ✅ |
| Async class-based services with shims | ✅ |

### Calendar (Frontend)
| Task | Status |
|------|--------|
| Scaffold React + Vite + TS + Tailwind | ✅ |
| Dockerfile.dev + add to docker-compose | ✅ |
| api/types.ts + api/client.ts | ✅ |
| Tests: ZoneManager.test.tsx | ✅ |
| Implement: Zone Manager page | ✅ |
| Tests: Calendar.test.tsx | ✅ |
| Implement: Calendar view | ✅ |
| Layout: AppShell + Sidebar | ✅ |
| Month view changed to Sun–Sat week layout | ✅ |

### Workout Builder (Frontend)
| Task | Status |
|------|--------|
| Tests: WorkoutBuilder.test.tsx | ✅ |
| Implement: StepTimeline + StepBar | ✅ |
| Implement: StepConfigPanel | ✅ |
| Implement: drag-and-drop | ✅ |
| Tests: WorkoutLibrary.test.tsx | ✅ |
| Implement: Library page | ✅ |

### Integration + Polish
| Task | Status |
|------|--------|
| Playwright E2E tests | ✅ |
| Error boundaries + loading states | ✅ |
| Dockerfile.prod + docker-compose.prod.yml + render.yaml | ✅ |
| Dark/light theme toggle (CSS vars + ThemeContext) | ✅ |
| Design polish (Field Monitor aesthetic — all components) | ✅ |
| Post-ship: light theme card bg fix, sidebar tone, font scaling | ✅ |
| Post-ship: remove drag-and-drop from calendar | ✅ |
| Post-ship: system theme as default (prefers-color-scheme) | ✅ |
| Post-ship: clock-format duration + distance summary on cards | ✅ |
| Post-ship: description stacking (per comma-segment) | ✅ |
| Post-ship: workoutStats.ts shared utils + 41 new edge-case tests | ✅ |
| Post-ship: vite proxy localhost fallback for outside-Docker dev | ✅ |
| Post-ship: Garmin delete-on-unschedule (optional dep pattern) | ✅ |
| Post-ship: Zone/profile change → auto re-sync modified Garmin workouts | ✅ |
| Post-ship: Fire-and-forget Garmin sync (BackgroundTasks + asyncio.gather) — zone/profile endpoints now return <100ms | ✅ |
| Post-ship: Cascade date filter fix (get_all_incomplete, user_id on ScheduledWorkout) | ✅ |
| Post-ship: Calendar workout card click → navigate to /builder?id= | ✅ |
| Post-ship: workout_description forwarded through formatter → Garmin payload | ✅ |
| Post-ship: SyncOrchestrator.delete_workout() method | ✅ |
| Post-ship: garth client.dumps() API fix | ✅ |
| Post-ship: WorkoutBuilder edit mode (initialId prop + updateTemplate) | ✅ |
| Post-ship: Calendar sync button debounce + spinner animation | ✅ |
| Post-ship: Zone manager Friel-only + threshold guide card | ✅ |
| Post-ship: App font refresh → IBM Plex Sans family | ✅ |
| Post-ship: Dynamic sidebar version from package.json (`__APP_VERSION__` via Vite define, strips `-dev` in prod) | ✅ |
| Post-ship: useCalendar.ts stale closure fix — useRef(range) so async callbacks read latest range | ✅ |
| Post-ship: WorkoutDetailPanel step rendering — ParsedStep + formatStep() + StepList component | ✅ |
| Mobile responsive | ✅ |
| Post-ship: Zones UX — single Save recalculates HR + pace zones; HR table display-only; saving indicator | ✅ |

### Auth + Deployment
| Task | Status |
|------|--------|
| Tests: test_api_auth.py | ✅ |
| Implement: auth module | ✅ |
| Add auth to all routes | ✅ |
| user_id FK migration | ✅ |
| Tests: test_garmin_connect_flow.py | ✅ |
| Garmin token encryption | ✅ |
| HKDF key derivation for Garmin token encryption (replaces SHA-256) | ✅ |
| Invite code system | ✅ |
| Frontend: AuthContext + login/register pages + protected routes | ✅ |
| Frontend: Settings page + Garmin Connect UI | ✅ |
| Password manager support (name/autocomplete/action + Credential Management API) | ✅ |
| **Google OAuth migration**: remove email/password login/register, add POST /auth/google | ✅ |
| **Google OAuth**: User model — add google_oauth_sub (unique), make password_hash nullable | ✅ |
| **Google OAuth**: Bootstrap updated — accepts google_access_token instead of email/password | ✅ |
| **Google OAuth**: Frontend — GoogleLogin button on LoginPage, RegisterPage, SetupPage | ✅ |
| **Google OAuth**: AuthContext — googleLogin(idToken, inviteCode?) replaces login/register | ✅ |
| **Google OAuth security**: reject unverified emails (email_verified check); sub-only user lookup (no email takeover) | ✅ |
| **Admin bootstrap + invite UI**: SetupPage, /setup route, SettingsPage admin section, invite link generation | ✅ |
| **Reset-admins endpoint**: POST /auth/reset-admins (setup token protected, factory reset) | ✅ |
| **Code review fixes**: dead schemas removed, tokenUrl fixed, datetime.utcnow → timezone.utc, isTokenExpired missing exp | ✅ |
| Deploy to Render | ✅ |

---

## Legend
⬜ not started · 🟡 in progress · ✅ done · ❌ blocked

## Known Issues (to fix later)

- **Backend dependency CVEs (pip-audit warnings)**: `pip-audit --local` currently reports several CVEs that are pre-existing and not caused by project code changes. Context for future sessions:
  - `urllib3 2.5.0` — CVE-2025-66418, CVE-2025-66471, CVE-2026-21441 → fix: upgrade to `urllib3>=2.6.3` in pyproject.toml (or let `python-garminconnect` pull the latest transitively)
  - `pyasn1 0.6.2` — CVE-2026-30922 → fix: upgrade to `pyasn1>=0.6.3`
  - `selenium 3.141.0` — PYSEC-2023-206, PYSEC-2022-43167 → selenium is pulled in by `garth` (Garmin auth library); not a direct dependency; no fix available without upstream change
  - `wheel 0.45.1` — CVE-2026-24049 → build tool, not a runtime dependency; upgrade or ignore
  - The only approved-ignore CVE is `GHSA-25h7-pfq9-p65f` (ecdsa, used by `garth`; no fix available) — already in the ship workflow's `pip-audit --ignore-vuln` flag. Do NOT add new --ignore-vuln flags without reviewing the CVE.

- **`reset_admins` has no rate limiting**: `POST /api/v1/auth/reset-admins` is a destructive endpoint (factory reset) with no rate limiting. An attacker who brute-forces the setup token can wipe all users. Needs `slowapi` or equivalent before public deployment. Flagged as Critical in PR #19 review. See CLAUDE.md "Nice to Have — Rate Limiting on Auth Routes."

- **Rate limiting on bootstrap + reset-admins** (security, moderate effort): `POST /api/v1/auth/bootstrap` and `POST /api/v1/auth/reset-admins` have no rate limiter — only a static setup token. Requires adding `slowapi` package, a `Limiter` instance in `app.py`, and `@limiter.limit("10/minute")` on both endpoints. Low exploitability today (invite-only app, endpoints require `BOOTSTRAP_SECRET`), but required before any public deployment. See "Nice to Have — Rate Limiting on Auth Routes" in CLAUDE.md.


## Notes
- Features dir is `features/` (not `docs/features/`) — agent prompts should reference this path
- Docker binary at `/Applications/Docker.app/Contents/Resources/bin/docker` (not in default PATH — add to ~/.zshrc)
- Zone engine coverage: 97% (hr_zones line 43, models line 51, pace_zones line 39 are the three uncovered lines — all minor)
- Dockerfile uses non-root `appuser`; dev hot-reload is via compose `command:` override only
- `pct_max_hr` / `pct_hrr` methods prefer `ZoneConfig.max_value` when set, fall back to `threshold`
- `scripts/try_it.py` provides an end-to-end local demo: `docker compose exec backend python scripts/try_it.py`
- **DB migrations**: Managed by Alembic (in `backend/alembic/`). Tests use in-memory DBs so schema drift is invisible to CI. For schema changes: `alembic revision --autogenerate -m "desc"` → apply locally → apply on Render before deploying.
- **HKDF breaking change**: Garmin token encryption switched from SHA-256 to HKDF. Any existing encrypted tokens in the DB are invalidated — connected Garmin accounts must reconnect after deployment.
- **Calendar test date-drift**: `Calendar.test.tsx` uses hardcoded dates (`baseWorkouts` at 2026-03-09–11). Tests that render without `initialDate` will fail once those dates fall outside the current week. Fix: pass `initialDate: new Date('2026-03-09')` to any `renderPage()` call that needs to see those workouts.
