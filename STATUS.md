# STATUS.md — GarminCoach Progress Tracker

Last updated: 2026-03-21 (v1.0.0 — first public release)

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
| Integration tests | ⬜ |

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
| Playwright E2E tests | ⬜ |
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
| Mobile responsive | ⬜ |

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

- **`google_auth` two sequential commits**: `auth/service.py` `google_auth()` has two `session.commit()` calls (line ~155: create user, line ~161: mark invite used). Should be batched into one commit for atomicity and to reduce DB round-trips. Requires restructuring the FK dependency (user must exist before invite references it). Related CLAUDE.md rule: "Batch commits. Call session.add() multiple times, then a single session.commit()."
- **`reset_admins` has no rate limiting**: `POST /api/v1/auth/reset-admins` is a destructive endpoint (factory reset) with no rate limiting. An attacker who brute-forces the setup token can wipe all users. Needs `slowapi` or equivalent before public deployment. Flagged as Critical in PR #19 review. See CLAUDE.md "Nice to Have — Rate Limiting on Auth Routes."

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
