# STATUS.md — GarminCoach Progress Tracker

Last updated: 2026-03-17 (post-release hotfixes — Google client_id build arg, tokeninfo audience validation)

## Current Focus: Next Feature

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
| Fix: remove create_db_and_tables() from lifespan — alembic is sole schema authority | ⬜ |
| Fix: add InviteCode to alembic/env.py model imports (autogenerate misses it) | ⬜ |

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
| Post-ship: clock-format duration + distance summary on cards | ✅ |
| Post-ship: description stacking (per comma-segment) | ✅ |
| Post-ship: workoutStats.ts shared utils + 41 new edge-case tests | ✅ |
| Post-ship: vite proxy localhost fallback for outside-Docker dev | ✅ |
| Post-ship: Garmin delete-on-unschedule (optional dep pattern) | ✅ |
| Post-ship: Zone/profile change → auto re-sync modified Garmin workouts | ✅ |
| Post-ship: Cascade date filter fix (get_all_incomplete, user_id on ScheduledWorkout) | ✅ |
| Post-ship: Calendar workout card click → navigate to /builder?id= | ✅ |
| Post-ship: workout_description forwarded through formatter → Garmin payload | ✅ |
| Post-ship: SyncOrchestrator.delete_workout() method | ✅ |
| Post-ship: garth client.dumps() API fix | ✅ |
| Post-ship: WorkoutBuilder edit mode (initialId prop + updateTemplate) | ✅ |
| Post-ship: Calendar sync button debounce + spinner animation | ✅ |
| Post-ship: Zone manager Friel-only + threshold guide card | ✅ |
| Post-ship: App font refresh → IBM Plex Sans family | ✅ |
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
