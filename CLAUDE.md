# CLAUDE.md — GarminCoach

A self-hosted training platform for runners using Garmin watches.
Replaces TrainingPeaks for self-coached athletes.

- **STATUS.md** — what's done, in progress, next. Read before starting, update when done.
- **docs/features/** — each feature has its own PLAN.md and CLAUDE.md.
- **.claude/agents/** — specialist agents for parallel work.

---

## Stack

| Layer      | Technology                                  |
| ---------- | ------------------------------------------- |
| Frontend   | React 18 + TypeScript + Tailwind + dnd-kit  |
| Backend    | FastAPI (Python 3.11+) + SQLModel + SQLite  |
| Garmin     | python-garminconnect (via garth OAuth)       |
| Auth       | python-jose (JWT) + passlib (bcrypt) + Fernet |
| Testing    | pytest + Vitest + React Testing Library      |
| Infra      | Docker Compose (dev + prod) → Render         |

---

## Principles

1. **Tests first.** Write the test → red → implement → green → refactor.
2. **Pure core.** Zone engine, resolver, formatter have zero I/O.
3. **One commit per thing.** Tests for X → implement X. Don't mix.
4. **Check STATUS.md.** Know where you are. Update when done.

---

## Conventions

### Python
- `ruff` for lint + format
- Type hints on all signatures
- Pydantic for request/response schemas
- `from __future__ import annotations`
- No bare `except`

### TypeScript
- Strict mode, no `any`
- Functional components, custom hooks
- `const` by default

### Testing
- Names: `test_<what>_<when>_<expect>`
- One behavior per test, Arrange-Act-Assert
- `@pytest.mark.parametrize` for variations
- Coverage: 95% pure core, 80% services/API

### Git
- Conventional commits: `test:`, `feat:`, `fix:`, `refactor:`

---

## TDD Rules

```
1. Write test → imports module that doesn't exist yet
2. Run → RED (ImportError or AssertionError)
3. Implement minimum to pass → GREEN
4. Refactor → run again → still GREEN
5. Repeat
```

```bash
pytest tests/unit/ -v                              # unit
pytest tests/integration/ -v                       # API + DB
pytest -v --cov=src --cov-report=term-missing      # all + coverage
docker compose exec backend pytest -v              # in container
npm test -- --run                                   # frontend
```

---

## Security (Always)

1. NEVER store Garmin passwords. OAuth tokens only, discard password immediately.
2. NEVER log passwords, tokens, or session cookies.
3. NEVER use raw SQL.
4. NEVER use `dangerouslySetInnerHTML`.
5. NEVER commit secrets. `.env` is gitignored.

---

## Features

Each feature has its own `PLAN.md` (what to build, tests, data model) and
`CLAUDE.md` (patterns, gotchas, reference data specific to that feature).

| Feature | Path | Description |
| ------- | ---- | ----------- |
| Zone Engine | `docs/features/zone-engine/` | HR + pace zone calculation, recalculation |
| Workout Resolver | `docs/features/workout-resolver/` | Zone→absolute target resolution, duration/distance estimation |
| Garmin Sync | `docs/features/garmin-sync/` | Formatter, sync service, session management |
| Database + API | `docs/features/database-api/` | SQLModel tables, FastAPI routes, services |
| Calendar | `docs/features/calendar/` | Frontend calendar view, scheduling, drag-reschedule |
| Workout Builder | `docs/features/workout-builder/` | Drag-and-drop visual builder, library |
| Auth | `docs/features/auth/` | JWT, user accounts, invite system, token encryption |
| Infrastructure | `docs/features/infrastructure/` | Docker Compose, Render deployment, project scaffolding |

---

## Agents

Specialist agents in `.claude/agents/` for parallel and delegated work.

| Agent | File | Role |
| ----- | ---- | ---- |
| backend-dev | `.claude/agents/backend-dev.md` | Python tests + implementation, TDD |
| frontend-dev | `.claude/agents/frontend-dev.md` | React components + tests, RTL |
| reviewer | `.claude/agents/reviewer.md` | Run tests, check coverage, verify quality (read-only) |
| infra | `.claude/agents/infra.md` | Docker, deployment, scaffolding |

### Using Agents as Subagents

For independent features that don't touch the same files, delegate to subagents:

```
Use the backend-dev agent to implement the zone-engine feature.
It should read docs/features/zone-engine/PLAN.md and follow TDD.
```

Parallel example (features 2-4 are independent pure logic):

```
Run these in parallel as subagents:
1. backend-dev: implement zone-engine (docs/features/zone-engine/)
2. backend-dev: implement workout-resolver (docs/features/workout-resolver/)
3. backend-dev: implement garmin formatter (docs/features/garmin-sync/ — formatter only)
After all three complete, use the reviewer agent to verify.
```

### Using Agent Teams (Experimental)

For cross-layer work where agents need to coordinate:

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

```
Create a team:
1. "backend" (backend-dev) — build database-api feature
2. "frontend" (frontend-dev) — build calendar feature
3. "reviewer" — review both when done
Backend and frontend work in parallel. Frontend depends on API types
so backend should share its types.ts early.
```

### Cost Optimization

Set subagents to use Sonnet while the main session uses Opus:

```bash
export CLAUDE_CODE_SUBAGENT_MODEL="claude-sonnet-4-5-20250929"
```

---

## Skills & Tools

- **Do NOT install generic skills.** Feature CLAUDE.md files have all needed context.
- **jezweb/claude-skills/fastapi** — install when implementing auth feature.
- **garmin-workouts-mcp** — reference only, NOT a dependency.
