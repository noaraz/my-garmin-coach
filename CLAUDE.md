# CLAUDE.md — GarminCoach

A self-hosted training platform for runners using Garmin watches.
Replaces TrainingPeaks for self-coached athletes.

- **STATUS.md** — what's done, in progress, next. Read before starting, update when done.
- **features/** — each feature has its own PLAN.md and CLAUDE.md.
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
- **NEVER commit directly to `main`.** Always work on a feature branch. The session start hook auto-creates one if needed.

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
| Zone Engine | `features/zone-engine/` | HR + pace zone calculation, recalculation |
| Workout Resolver | `features/workout-resolver/` | Zone→absolute target resolution, duration/distance estimation |
| Garmin Sync | `features/garmin-sync/` | Formatter, sync service, session management |
| Database + API | `features/database-api/` | SQLModel tables, FastAPI routes, services |
| Calendar | `features/calendar/` | Frontend calendar view, scheduling, drag-reschedule |
| Workout Builder | `features/workout-builder/` | Drag-and-drop visual builder, library |
| Auth | `features/auth/` | JWT, user accounts, invite system, token encryption |
| Infrastructure | `features/infrastructure/` | Docker Compose, Render deployment, project scaffolding |

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
It should read features/zone-engine/PLAN.md and follow TDD.
```

Parallel example (features 2-4 are independent pure logic):

```
Run these in parallel as subagents:
1. backend-dev: implement zone-engine (features/zone-engine/)
2. backend-dev: implement workout-resolver (features/workout-resolver/)
3. backend-dev: implement garmin formatter (features/garmin-sync/ — formatter only)
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
- **fastapi-templates** — installed at `.claude/skills/fastapi-templates/`. Async patterns, DI, middleware.
- **frontend-design** — installed at `.claude/skills/frontend-design/`. Use when building React components, pages, or UI. Generates distinctive, production-grade designs (avoid generic AI aesthetics). Invoke via Skill tool.

## Commands

Project slash commands in `.claude/commands/`:

| Command | Description |
|---------|-------------|
| `/ship` | Full ship workflow: tests → code review → fix prompt → local test steps → update docs → open PR |

## Workflow Patterns

- **Subagents for parallel features**: launch `backend-dev` agents in parallel for independent features (different file sets). They don't conflict if files don't overlap.
- **Reviewer agent**: delegates test-running to background subagent. Returns pass/fail + coverage.
- **`/code-review uncommitted changes`**: runs 5-agent review (CLAUDE.md, bugs, git history, PR history, comments) with confidence scoring. Issues scored ≥ 80 are actionable.
- **`create_app()` factory pattern**: `src/api/app.py` exports both `create_app()` and a module-level `app = create_app()` for backward compat with uvicorn.

## Frontend Patterns (added 2026-03-08)

- **Theming**: CSS custom properties only — no Tailwind dark: prefix. Variables in `:root` (dark by default) + `[data-theme="light"]` override in `index.css`. Toggle via `document.documentElement.dataset.theme`. Sidebar stays dark in both themes.
- **ThemeContext**: `React.createContext` + `useState` + `localStorage` persistence. Wrap `<App>` in `<ThemeProvider>`.
- **@dnd-kit/sortable drag reorder**: `SortableContext` (horizontal strategy) → `useSortable` per item → `arrayMove` in `onDragEnd`. Drag handle element gets `{...listeners}`, container gets `{...attributes}` + `ref={setNodeRef}`.
- **@dnd-kit pointer drag**: always add `activationConstraint: { distance: 8 }` to `PointerSensor` — without it, drag conflicts with click handlers and may not activate reliably.
- **ErrorBoundary**: class component with `getDerivedStateFromError`. Wrap each route element in `App.tsx`.
- **Vitest + vite.config.ts**: add `/// <reference types="vitest" />` at top of `vite.config.ts` for `test` property to typecheck.
- **TypeScript strict build**: `npm run build` runs `tsc -b` which is stricter than Vitest. Common gotchas: unused imports/vars, `null` vs `undefined` in props, missing explicit types on `as` casts.
- **Prod Docker**: `frontend/Dockerfile.prod` (node:20-alpine builder → nginx:alpine), `frontend/nginx.conf` (SPA try_files + `/api/` proxy to `http://backend:8000`).
- **Docker credential helper**: `docker-credential-desktop` must be in PATH. Prefix commands: `PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" docker compose ...`

## Color Token Conventions (added 2026-03-09)

**Rule: zero hardcoded hex values in component files.** All colors must use CSS custom properties.

### Available tokens (index.css)

| Token | Usage |
|-------|-------|
| `--bg-main` | Page background |
| `--bg-surface` | Cards, panels, modals |
| `--bg-surface-2` | Hover states, alternate rows |
| `--bg-surface-3` | Active/selected states |
| `--border` | Default border |
| `--border-strong` | Emphasized border |
| `--text-primary` | Main body text |
| `--text-secondary` | Labels, captions |
| `--text-muted` | Placeholder, disabled, de-emphasized |
| `--accent` | Primary CTA: blue buttons, today highlight, selected borders |
| `--accent-subtle` | Selected state background (low opacity blue) |
| `--text-on-accent` | Text on `--accent` backgrounds |
| `--zone-default` | Fallback zone color (gray) for unknown types |
| `--color-zone-1..5` | Zone step colors (blue → red). Available as CSS vars from Tailwind `@theme` |

### Patterns

```tsx
// ✅ Correct — always use var()
style={{ color: 'var(--text-muted)', background: 'var(--bg-surface)' }}

// ❌ Wrong — no hardcoded hex
style={{ color: '#555', background: '#1c1c1e' }}

// Zone stripes (WorkoutCard sport stripe)
style={{ background: 'var(--color-zone-1)' }}   // not Tailwind bg-blue-500
```

### Tailwind classes to avoid in new code
- `bg-white`, `text-gray-*`, `bg-gray-*` — use CSS vars instead
- `dark:` prefix — we use `[data-theme="light"]` overrides in index.css, not Tailwind dark mode

## workoutStats Utilities (added 2026-03-09)

Four pure helpers in `frontend/src/utils/workoutStats.ts` — shared between `WorkoutCard` and `TemplateCard`:

```typescript
computeDurationFromSteps(stepsJson: string | null | undefined): number | null
// Parses template.steps JSON, sums duration_sec recursively.
// Handles repeat groups: multiplies child seconds by group.repeat_count (default 1).
// Returns null if stepsJson is null/undefined/empty/invalid JSON or no time-based steps.

computeDistanceFromSteps(stepsJson: string | null | undefined): number | null
// Same logic but sums distance_m fields. Returns null if only time-based steps.

formatClock(seconds: number): string
// Clock format: 65 → "1:05", 2700 → "45:00", 4200 → "1:10:00"
// Omits hours column when < 3600s.

formatKm(metres: number): string
// "12.5 km" — always 1 decimal place.
```

**Usage pattern** (both WorkoutCard and TemplateCard):
```typescript
const durationSec = template.estimated_duration_sec ?? computeDurationFromSteps(template.steps)
const distanceM   = template.estimated_distance_m   ?? computeDistanceFromSteps(template.steps)
const hasDuration = durationSec != null && durationSec > 0
const hasDistance = distanceM   != null && distanceM   > 0
// Summary row: {hasDuration && formatClock(durationSec!)}  {hasDistance && formatKm(distanceM!)}
```

**Why steps fallback is necessary**: workout templates created by the builder typically have `estimated_duration_sec: null` in the DB (the builder doesn't compute/save it). The steps JSON always exists and contains the ground truth.

## Vitest Testing Gotchas (added 2026-03-09)

### React 18 StrictMode double-fires effects
`useEffect` runs **twice** in test environment (StrictMode). This consumes `mockResolvedValueOnce`:

```typescript
// ❌ Wrong — Once is consumed by first StrictMode call; second call gets stale default
mockFetchTemplates.mockResolvedValueOnce([...myTemplates])

// ✅ Correct — permanent override, reset in beforeEach
mockFetchTemplates.mockResolvedValue([...myTemplates])
// beforeEach: mockFetchTemplates.mockReset(); mockFetchTemplates.mockResolvedValue(defaults)
```

### `vi.hoisted()` for mutable mock references
When mock functions need to be referenced both inside `vi.mock()` factory AND in individual test bodies:

```typescript
// ✅ Correct — vi.hoisted runs before vi.mock, refs are stable
const { mockFetchTemplates } = vi.hoisted(() => ({
  mockFetchTemplates: vi.fn().mockResolvedValue(defaultTemplates),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, fetchWorkoutTemplates: mockFetchTemplates }
})

// In test: mockFetchTemplates.mockResolvedValue([...override])
```

### `findByText` vs `findAllByText` when content repeats
If multiple workouts map to the same template, the same duration text appears multiple times.
`findByText('15:00')` throws "Found multiple elements" — use `findAllByText('15:00')` instead.

## generateDescription Pattern (added 2026-03-09)

Two pure utility functions in `frontend/src/utils/generateDescription.ts`:

```typescript
generateDescription(steps: BuilderStep[]): string
// One-liner for template.description field
// Example: "10m@Z1, 45m@Z2, 5m@Z3" or "2K@Z1, 6x (0.5K@Z5 + 0.4K@Z1), 1K@Z2"
// Format per step: {value}{unit}@Z{zone}   (m=min, K=km)
// Repeat group:   "{n}x ({step1} + {step2})"

generateWorkoutDetails(steps: BuilderStep[], paceZones: PaceZone[]): string
// Multi-line structured text with resolved pace ranges
// Example:
//   Warm up
//     10 min @ 07:43–09:38 min/km
//   Repeat 6 times
//     1. Hard
//        0.50 km @ 05:02–05:30 min/km
//        Zone 5
```

**WorkoutBuilder usage**: auto-fills `description` via `useEffect` from `generateDescription(steps)` on step change, unless `isDescriptionEdited` is true (user manually typed). Fetches `paceZones` on mount for the details panel.

---

## Nice to Have (future features)

Ideas for future iterations, roughly in priority order.

### Test Run → Zone Update
When a user completes a deliberate effort (time trial, race, or 30-min test), they should be able to tag it and have zones auto-updated from the result.

**Flow:**
1. User marks a completed `ScheduledWorkout` as `is_zone_test: bool` + `test_type: "lthr" | "threshold_pace" | "max_hr"`
2. Backend reads the Garmin activity data for that workout (avg HR for LTHR, best pace for threshold_pace)
3. Updates the `AthleteProfile` with the new value
4. Triggers the existing zone recalculation cascade (already implemented in `zone_service`)

**Data model addition:**
```python
# ScheduledWorkout
is_zone_test: bool = False
test_type: Optional[str] = None   # "lthr" | "threshold_pace" | "max_hr"
```

**Backend:**
- `POST /api/v1/calendar/{id}/apply-as-zone-test` → reads Garmin activity, updates profile, recalculates zones
- Or: add `apply_zone_test` field to the `PATCH /api/v1/calendar/{id}` body

**Frontend:** "Apply as zone test" button on a completed workout card in the calendar.

---

### Playwright E2E Tests
Full browser tests for the critical user journey: login → set zones → build workout → schedule it → sync to Garmin.

---

### Mobile Responsive
CSS polish pass — the app is built desktop-first. Key breakpoints needed for calendar, sidebar, and workout builder on small screens.

---

### Rate Limiting on Auth Routes
Add `slowapi` (or similar) to limit `/api/v1/auth/login` and `/api/v1/auth/register` to e.g. 10 req/min per IP. Required before making the app publicly accessible.

---

### Refresh Token Rotation
Currently the refresh token is long-lived and static. Implement single-use rotation: each `/auth/refresh` call returns a new refresh token and invalidates the old one. Requires a `RefreshToken` DB table.

---

### Activity Feed / History
Show completed workouts pulled from Garmin Connect — not just scheduled ones. Useful for reviewing training load.
