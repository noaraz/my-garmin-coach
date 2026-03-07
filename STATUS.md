# STATUS.md — GarminCoach Progress Tracker

Last updated: not started

## Current Focus: Infrastructure (Scaffolding)

---

### Infrastructure
| Task | Status |
|------|--------|
| Repo structure + pyproject.toml | ⬜ |
| backend/Dockerfile + docker-compose.yml | ⬜ |
| Minimal FastAPI health check | ⬜ |
| .env.example + .gitignore | ⬜ |
| docker compose up works | ⬜ |
| pytest runs in container | ⬜ |

### Zone Engine
| Task | Status |
|------|--------|
| models.py (Zone, ZoneConfig, ZoneSet) | ⬜ |
| Tests: test_hr_zones.py | ⬜ |
| Implement: hr_zones.py | ⬜ |
| Tests: test_pace_zones.py | ⬜ |
| Implement: pace_zones.py | ⬜ |
| Coverage >95% | ⬜ |

### Workout Resolver
| Task | Status |
|------|--------|
| models.py (WorkoutStep, ResolvedStep) | ⬜ |
| Tests: test_workout_resolver.py | ⬜ |
| Implement: resolver.py | ⬜ |
| Tests: test_workout_estimator.py | ⬜ |
| Implement: estimator.py | ⬜ |

### Garmin Sync
| Task | Status |
|------|--------|
| garmin/constants.py | ⬜ |
| Tests: test_garmin_converters.py | ⬜ |
| Implement: converters.py | ⬜ |
| Tests: test_garmin_formatter.py | ⬜ |
| Implement: formatter.py | ⬜ |
| Tests: test_garmin_sync.py (mocked) | ⬜ |
| Implement: sync_service.py + session.py | ⬜ |
| Implement: sync_orchestrator.py | ⬜ |

### Database + API
| Task | Status |
|------|--------|
| db/models.py (SQLModel tables) | ⬜ |
| db/database.py | ⬜ |
| Tests: test_db.py | ⬜ |
| Tests: test_api_profile.py | ⬜ |
| Tests: test_api_zones.py | ⬜ |
| Tests: test_api_workouts.py | ⬜ |
| Tests: test_api_calendar.py | ⬜ |
| Tests: test_api_sync.py | ⬜ |
| Implement: services + routers | ⬜ |
| Zone change cascade | ⬜ |

### Calendar (Frontend)
| Task | Status |
|------|--------|
| Scaffold React + Vite + TS + Tailwind | ⬜ |
| Dockerfile.dev + add to docker-compose | ⬜ |
| api/types.ts + api/client.ts | ⬜ |
| Tests: ZoneManager.test.tsx | ⬜ |
| Implement: Zone Manager page | ⬜ |
| Tests: Calendar.test.tsx | ⬜ |
| Implement: Calendar view | ⬜ |
| Layout: AppShell + Sidebar | ⬜ |

### Workout Builder (Frontend)
| Task | Status |
|------|--------|
| Tests: WorkoutBuilder.test.tsx | ⬜ |
| Implement: StepTimeline + StepBar | ⬜ |
| Implement: StepConfigPanel | ⬜ |
| Implement: drag-and-drop | ⬜ |
| Tests: WorkoutLibrary.test.tsx | ⬜ |
| Implement: Library page | ⬜ |

### Integration + Polish
| Task | Status |
|------|--------|
| Playwright E2E tests | ⬜ |
| Error boundaries + loading states | ⬜ |
| Dockerfile.prod + docker-compose.prod.yml | ⬜ |
| Dark mode | ⬜ |
| Mobile responsive | ⬜ |

### Auth + Deployment
| Task | Status |
|------|--------|
| Tests: test_api_auth.py | ⬜ |
| Implement: auth module | ⬜ |
| Add auth to all routes | ⬜ |
| user_id FK migration | ⬜ |
| Tests: test_garmin_connect_flow.py | ⬜ |
| Garmin token encryption | ⬜ |
| Invite code system | ⬜ |
| Frontend: login page | ⬜ |
| Deploy to Render | ⬜ |

---

## Legend
⬜ not started · 🟡 in progress · ✅ done · ❌ blocked

## Notes
<!-- decisions, blockers, changes -->
