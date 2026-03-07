# PLAN.md — GarminCoach Architecture & Roadmap

## Vision

A self-hosted web application that replaces TrainingPeaks for self-coached runners
using Garmin watches. Visual calendar, drag-and-drop workout builder, zone management,
and sync to Garmin Connect.

Track progress in **STATUS.md**. Update it after completing each task.

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
│  ┌──────────┐  ┌───────────────┐                     │
│  │ Workout  │  │  Garmin Sync  │                     │
│  │ Library  │  │   Dashboard   │                     │
│  └──────────┘  └───────────────┘                     │
└────────────────────┬────────────────────────────────┘
                     │ REST API (JSON)
┌────────────────────┴────────────────────────────────┐
│               Python Backend (FastAPI)               │
│                                                      │
│  ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │   Zone     │ │   Workout    │ │    Garmin     │  │
│  │  Engine    │ │  Resolver    │ │  Sync Service │  │
│  └────────────┘ └──────────────┘ └───────────────┘  │
│                                                      │
│  ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │  Calendar  │ │   Library    │ │     Auth      │  │
│  │  Service   │ │   Service    │ │   Service     │  │
│  └────────────┘ └──────────────┘ └───────────────┘  │
│                                                      │
│             SQLite via SQLModel/SQLAlchemy            │
└────────────────────┬────────────────────────────────┘
                     │ python-garminconnect (via garth)
                     ▼
              Garmin Connect → Garmin Watch
```

---

## Feature Build Order

Each feature has its own `PLAN.md` (description, tasks, tests, data model)
and `CLAUDE.md` (patterns, gotchas) in `docs/features/<name>/`.

| Order | Feature | Path | Dependencies |
|-------|---------|------|-------------|
| 1 | Infrastructure | `docs/features/infrastructure/` | — |
| 2 | Zone Engine | `docs/features/zone-engine/` | — (pure logic) |
| 3 | Workout Resolver | `docs/features/workout-resolver/` | zone-engine |
| 4 | Garmin Sync | `docs/features/garmin-sync/` | workout-resolver |
| 5 | Database + API | `docs/features/database-api/` | all above |
| 6 | Calendar | `docs/features/calendar/` | database-api |
| 7 | Workout Builder | `docs/features/workout-builder/` | database-api, calendar |
| 8 | Auth | `docs/features/auth/` | database-api |
| — | Polish + Deploy | in infrastructure/ | all above |

Features 2–4 are pure logic with zero I/O. Feature 5 adds persistence.
Features 6–7 are frontend. Feature 8 is auth. Deploy after auth.

---

## Key Mechanism: Zone Cascade

The core value — what TrainingPeaks does that we're replicating:

```
1. User changes LTHR (e.g. 170 → 175)
2. Zone engine recalculates all 5 HR zones from percentages
3. All future scheduled workouts re-resolved (zone refs → new absolute targets)
4. Changed workouts re-pushed to Garmin Connect
5. Next watch sync → athlete sees updated targets
```

---

## Tech Stack

| Layer      | Technology                                  |
| ---------- | ------------------------------------------- |
| Frontend   | React 18 + TypeScript + Tailwind + dnd-kit  |
| Backend    | FastAPI (Python 3.11+) + SQLModel + SQLite  |
| Garmin     | python-garminconnect (~1.8K★) via garth (~757★) |
| Auth       | python-jose (JWT) + passlib (bcrypt) + Fernet |
| Testing    | pytest + Vitest + React Testing Library      |
| Infra      | Docker Compose (dev + prod) → Render (free)  |

---

## Design Principles

1. **TDD**: Test → red → implement → green → refactor.
2. **Pure core**: Zone engine, resolver, formatter have zero I/O.
3. **Thin API**: Routers validate and delegate. Logic in services + pure core.
4. **Mock the boundary**: Garmin sync always mocked in CI.
5. **Zone cascade is the killer feature**: Must work flawlessly.
