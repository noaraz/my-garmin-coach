# PLAN.md — GarminCoach Architecture & Roadmap

## Vision

A self-hosted web application that replaces TrainingPeaks for self-coached runners
using Garmin watches. Visual calendar, drag-and-drop workout builder, zone management,
bidirectional sync with Garmin Connect, and activity compliance tracking.

Track progress in **STATUS.md**. Update it after completing each task.
Release process in **RELEASING.md** — versioning, GitHub tags, Render deploy workflow.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Frontend                      │
│              (Vite + TypeScript + Tailwind)           │
│                                                      │
│  ┌──────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ Calendar  │  │   Workout     │  │    Zone      │  │
│  │   View    │  │   Builder     │  │   Manager    │  │
│  └──────────┘  └───────────────┘  └──────────────┘  │
│                                                      │
│  ┌──────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ Workout  │  │  Garmin Sync  │  │  Settings /  │  │
│  │ Library  │  │   Dashboard   │  │  Google Auth │  │
│  └──────────┘  └───────────────┘  └──────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │ REST API (JSON)
┌────────────────────┴────────────────────────────────┐
│               Python Backend (FastAPI)               │
│                                                      │
│  ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │   Zone     │ │   Workout    │ │    Garmin     │  │
│  │  Engine    │ │  Resolver    │ │  Adapter      │  │
│  └────────────┘ └──────────────┘ └───────────────┘  │
│                                                      │
│  ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │  Calendar  │ │   Library    │ │     Auth      │  │
│  │  Service   │ │   Service    │ │   (Google)    │  │
│  └────────────┘ └──────────────┘ └───────────────┘  │
│                                                      │
│  ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │  Activity  │ │  Sync        │ │  TTL Cache    │  │
│  │  Fetch Svc │ │ Orchestrator │ │ (User/Zones)  │  │
│  └────────────┘ └──────────────┘ └───────────────┘  │
│                                                      │
│   SQLite (dev) / Neon PostgreSQL (prod)              │
│   via SQLModel + SQLAlchemy (async)                  │
└────────────────────┬────────────────────────────────┘
                     │ python-garminconnect (via garth)
                     │ ← → bidirectional sync
                     │ Fixie proxy (OAuth only)
                     ▼
              Garmin Connect → Garmin Watch
```

---

## Tech Stack

| Layer      | Technology                                  |
| ---------- | ------------------------------------------- |
| Frontend   | React 18 + TypeScript + Tailwind + dnd-kit  |
| Backend    | FastAPI (Python 3.11+) + SQLModel + SQLite (dev) / Neon PostgreSQL (prod) |
| Garmin     | python-garminconnect (~1.8K★) via garth (~757★) |
| Auth       | Google OAuth + python-jose (JWT) + Fernet (token encryption) |
| Testing    | pytest + Vitest + React Testing Library      |
| Infra      | Docker Compose (dev + prod) → Render (free)  |
| Proxy      | Fixie (static IP for Garmin OAuth in prod)   |
| Cache      | In-memory TTL cache (User, Profile, Zones)   |

---

## Feature Build Order

Each feature has its own `PLAN.md` (description, tasks, tests, data model)
and `CLAUDE.md` (patterns, gotchas) in `features/<name>/`.

| Order | Feature | Path | Dependencies | Status |
|-------|---------|------|-------------|--------|
| 1 | Infrastructure | `features/infrastructure/` | — | ✅ |
| 2 | Zone Engine | `features/zone-engine/` | — (pure logic) | ✅ |
| 3 | Workout Resolver | `features/workout-resolver/` | zone-engine | ✅ |
| 4 | Garmin Sync | `features/garmin-sync/` | workout-resolver | ✅ |
| 5 | Database + API | `features/database-api/` | all above | ✅ |
| 6 | Calendar | `features/calendar/` | database-api | ✅ |
| 7 | Workout Builder | `features/workout-builder/` | database-api, calendar | ✅ |
| 8 | Auth | `features/auth/` | database-api | ✅ |
| — | Polish + Deploy | in infrastructure/ | all above | ✅ |
| — | DB Migrations (Alembic) | `features/infrastructure/` | auth | ✅ |
| — | Google OAuth | `features/auth/` | auth | ✅ |
| — | Neon PostgreSQL | `features/infrastructure/` | — | ✅ |
| — | Fixie Proxy | `features/infrastructure/` | — | ✅ |
| — | Neon Query Optimization | — | neon-postgresql | ✅ |
| 9 | Activity Fetch | `features/garmin-activity-fetch/` | garmin-sync, calendar | 🟡 |

Features 2–4 are pure logic with zero I/O. Feature 5 adds persistence.
Features 6–7 are frontend. Feature 8 is auth. Deploy after auth.
Feature 9 adds bidirectional Garmin sync with compliance tracking.

---

## Key Mechanisms

### 1. Zone Cascade

The core value — what TrainingPeaks does that we're replicating:

```
1. User changes LTHR (e.g. 170 → 175)
2. Zone engine recalculates all 5 HR zones from percentages
3. All future scheduled workouts re-resolved (zone refs → new absolute targets)
4. Changed workouts re-pushed to Garmin Connect
5. Next watch sync → athlete sees updated targets
```

### 2. Activity Compliance (Feature 9)

```
1. Activities fetched from Garmin → stored in GarminActivity table
2. Auto-matched to scheduled workouts by date + running type (longest duration wins)
3. Calendar shows compliance colors:
   - Green (±20%): on target
   - Yellow (21-50%): close
   - Red (>50%): off target
   - Grey: unplanned activity (no scheduled workout)
   - Muted: missed (past-date scheduled workout, no activity)
4. Users can manually pair/unpair to correct mismatches
```

---

## Design Principles

1. **TDD**: Test → red → implement → green → refactor.
2. **Pure core**: Zone engine, resolver, formatter have zero I/O.
3. **Thin API**: Routers validate and delegate. Logic in services + pure core.
4. **Mock the boundary**: Garmin sync always mocked in CI.
5. **Zone cascade is the killer feature**: Must work flawlessly.
6. **Bidirectional sync**: Push workouts, fetch activities. Both best-effort.
