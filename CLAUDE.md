# CLAUDE.md — GarminCoach

A self-hosted training platform for runners using Garmin watches.
Replaces TrainingPeaks for self-coached athletes.

- **STATUS.md** — what's done, in progress, next. Read before starting, update when done.
- **features/** — each feature has its own PLAN.md and CLAUDE.md.
- **docs/superpowers/specs/** — design specs (brainstorming output). **docs/superpowers/plans/** — implementation plans (writing-plans output).
- **.claude/agents/** — specialist agents for parallel work.
- **docs/claude-automation.md** — MCP servers, hooks, agents, and skills available in this repo. Read when deciding how to query the DB, check GitHub, run browser automation, or invoke any slash command.

---

## Stack

| Layer      | Technology                                  |
| ---------- | ------------------------------------------- |
| Frontend   | React 18 + TypeScript + Tailwind + dnd-kit  |
| Backend    | FastAPI (Python 3.11+) + SQLModel + SQLite (dev) / PostgreSQL (prod) |
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
- `ruff` for lint + format (includes `DTZ` rules — bans `datetime.utcnow()` etc.)
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
- **Class-based async tests**: `asyncio_mode = "auto"` covers `class TestFoo: async def test_...` — no `@pytest.mark.asyncio` needed. After removing decorators, also remove `import pytest` (ruff F401 will flag it as unused).

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
pytest tests/unit/test_foo.py -v --no-cov          # fast TDD iteration (skip coverage)
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
| Activity Fetch | `features/garmin-activity-fetch/` | Fetch Garmin activities, compliance tracking, bidirectional sync |
| Workout Detail Panel | `features/calendar/` | Slide-out Quick View panel for workout/activity details |
| Plan Coach | `features/plan-coach/` | Multi-week training plan via CSV import or Gemini Flash chat; validate/diff/commit pipeline; smart merge (keep unchanged + completed workouts on re-import) |
| Status Indicators | `features/status-indicators/` | Garmin connection dot + Zones "Not set" inline warning in sidebar; Garmin toolbar button on CalendarPage |
| Onboarding | `features/onboarding/` | First-time modal wizard (7 steps, localStorage flag) + Help page with Replay tour |
| Mobile Responsive | `features/mobile-responsive/` | Bottom tab bar, TodayPage, responsive layout for all pages |

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

- **wrap-up-docs-check** — installed at `.claude/skills/wrap-up-docs-check/`. Run when user signals feature complete ("all good", "ship it", "done"). Checks root STATUS.md + PLAN.md + CLAUDE.md and feature subfolder docs are updated, then runs `revise-claude-md` on all touched CLAUDE.md files.
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
| `/release` | Release workflow: pre-flight → tests → security review → version bump → tag → push (triggers GitHub Actions gate) |

## Workflow Patterns

- **Subagents for parallel features**: launch `backend-dev` agents in parallel for independent features (different file sets). They don't conflict if files don't overlap.
- **Reviewer agent**: delegates test-running to background subagent. Returns pass/fail + coverage.
- **`/code-review uncommitted changes`**: runs 5-agent review (CLAUDE.md, bugs, git history, PR history, comments) with confidence scoring. Issues scored ≥ 80 are actionable.
- **`create_app()` factory pattern**: `src/api/app.py` exports both `create_app()` and a module-level `app = create_app()` for backward compat with uvicorn.

## Google OAuth Gotchas (added 2026-03-17)

- **`aud` is NOT in the userinfo response** — `/oauth2/v3/userinfo` does not expose the token audience. Only ID tokens (JWTs) have `aud`. For access tokens, use the tokeninfo endpoint.
- **Audience validation via tokeninfo** — `GET https://oauth2.googleapis.com/tokeninfo?access_token={token}` returns `azp` (authorized party = the OAuth2 client_id). Check `azp == settings.google_client_id`.
- **`VITE_GOOGLE_CLIENT_ID` is a build-time variable** — Vite bakes it into the bundle at `npm run build`. In `Dockerfile.prod`, pass it as a Docker `ARG` before `RUN npm run build`. Reuse `GOOGLE_CLIENT_ID` (already in Render) via `ARG GOOGLE_CLIENT_ID` → `ENV VITE_GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID` — no separate Render env var needed.
- **Don't mock `_google_userinfo` in tests** — mocking the whole function hides bugs in its body. Mock `httpx.AsyncClient` instead so the audience check, email_verified check, and URL logic are all exercised.
- **Google OAuth popup on mobile is broken** — `window.open()` popup UX is unusable on mobile browsers. Implicit redirect flow (`response_type=token`) requires registering exact redirect URIs in Google Cloud Console and is not worth implementing. Mobile users use the same popup flow as desktop (acceptable tradeoff).

## Settings / Garmin Connect UI (added 2026-03-09)

- **Route**: `/settings` → `SettingsPage.tsx` — protected, wrapped in AppShell + ErrorBoundary
- **Sidebar**: Settings nav item with gear icon — last in nav list
- **Garmin status**: `getGarminStatus()` called on mount; shows green dot "Connected" or red dot "Not connected" at all times
- **Connect form**: email + password inputs → `connectGarmin(email, password)` → token encrypted by backend, credentials never stored
- **Disconnect**: `disconnectGarmin()` → backend clears encrypted token + `garmin_connected = False`
- **API functions**: `getGarminStatus`, `connectGarmin`, `disconnectGarmin` in `frontend/src/api/client.ts`
- **Type**: `GarminStatusResponse { connected: boolean }` in `frontend/src/api/types.ts`

## Typography (updated 2026-03-16)

- **Display/headers**: `'IBM Plex Sans Condensed'` — section labels, page titles, zone badges, button text
- **Body**: `'IBM Plex Sans'` — descriptive text, form labels, guide card content
- **Mono/numbers**: `'IBM Plex Mono'` — BPM values, pace values, mono subtitles, "or:" hint lines
- Google Fonts import in `index.css` — `IBM+Plex+Sans+Condensed`, `IBM+Plex+Sans`, `IBM+Plex+Mono`
- CSS `@theme` vars: `--font-family-display`, `--font-family-body`, `--font-family-mono`
- **Zone method**: Friel only — `MethodSelector` component deleted. `zone_service.py` hardcodes `method="friel"`. Do not re-introduce method selection.

## Docker + Dev Environment Gotchas (added 2026-03-17)

### venv-in-Docker (updated 2026-03-23)
Both `Dockerfile.prod` (Stage 2) and `backend/Dockerfile` use a venv at `/venv` to avoid the pip root-user warning. Always follow this pattern when adding Python Docker images:
```dockerfile
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install --no-cache-dir -e "."
```
`/venv` is owned by root but world-readable — `appuser` can execute from it without owning it.

### Local API testing — JWT token generation
Generate a valid token without Google OAuth (container must be running):
```bash
docker compose exec backend python3 -c "
from src.auth.jwt import create_access_token
print(create_access_token(user_id=1, email='your@email.com', is_admin=True))
"
```
Use with `curl -H "Authorization: Bearer <token>"`. Token expires per `ACCESS_TOKEN_EXPIRE_MINUTES`.

### macOS bind-mount sync issue
`./backend/tests:/app/tests` volume mounts don't always reflect local file changes immediately
inside running containers on macOS. If tests still run old code after editing, force-sync with:

```bash
docker cp backend/tests/integration/test_api_auth.py garmincoach-backend-1:/app/tests/integration/test_api_auth.py
```

Replace the container name and path as needed. This is only a workaround — the underlying cause
is macOS fsevents latency on bind mounts.

### Local prod testing with .env.prod
`.env.prod` exists at repo root (gitignored) with production secrets. Use it to test the
prod docker-compose locally:

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  up --build
```

### Frontend build outside Docker
`npm run build` calls `tsc` which is not in PATH outside Docker. Use `npx tsc -b && npx vite build` when running the build locally.

### pip-audit outside Docker
`pip-audit` is not installed globally — run `pip install pip-audit` first. Use `pip-audit --local` to audit only project deps; without `--local` the output is flooded with unrelated system package CVEs.

### `create_db_and_tables()` removed (2026-03-19)
This function no longer exists in `src/db/database.py`. Alembic (`alembic upgrade head`) is the sole schema authority. Do not recreate it.

---

## Frontend Patterns (added 2026-03-08)

- **Theming**: CSS custom properties only — no Tailwind dark: prefix. Variables in `:root` (dark by default) + `[data-theme="light"]` override in `index.css`. Toggle via `document.documentElement.dataset.theme`. Sidebar stays dark in both themes.
- **ThemeContext**: `React.createContext` + `useState`. Default = `prefers-color-scheme`; localStorage only written on explicit toggle (not in sync effect). Live OS changes followed when no localStorage key exists. Wrap `<App>` in `<ThemeProvider>`.
- **@dnd-kit/sortable drag reorder**: `SortableContext` (horizontal strategy) → `useSortable` per item → `arrayMove` in `onDragEnd`. Drag handle element gets `{...listeners}`, container gets `{...attributes}` + `ref={setNodeRef}`.
- **@dnd-kit pointer drag**: always add `activationConstraint: { distance: 8 }` to `PointerSensor` — without it, drag conflicts with click handlers and may not activate reliably.
- **ErrorBoundary**: class component with `getDerivedStateFromError`. Wrap each route element in `App.tsx`.
- **Vitest + vite.config.ts**: add `/// <reference types="vitest" />` at top of `vite.config.ts` for `test` property to typecheck.
- **TypeScript strict build**: `npm run build` runs `tsc -b` which is stricter than Vitest. Common gotchas: unused imports/vars, `null` vs `undefined` in props, missing explicit types on `as` casts.
- **Prod Docker**: `frontend/Dockerfile.prod` (node:20-alpine builder → nginx:alpine), `frontend/nginx.conf` (SPA try_files + `/api/` proxy to `http://backend:8000`).
- **Docker credential helper**: `docker-credential-desktop` must be in PATH. Prefix commands: `PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" docker compose ...`
- **CSS `@keyframes` must be global for inline animation** — keyframes defined inside an `@media` block are NOT reachable by `style={{ animation: 'myAnim 280ms ease' }}`. Define `@keyframes` at the top level in `index.css` even if the animation is only used in mobile contexts.

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

### Additional tokens (added 2026-03-21)
- `--color-success-glow` / `--color-error-glow` — rgba glow variants for `box-shadow` on status dots (e.g. `0 0 0 2px var(--color-success-glow)`)
- `--color-success-bg` / `--color-error-bg` — subtle background fill for status badges
- **Sidebar.tsx is the only component exempt from the zero-hex rule** — it's always dark and uses its own named constants (`SIDE_GARMIN_CONNECTED` etc.). No other component has this exemption.

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

## WorkoutDetailPanel Patterns (added 2026-03-20)

- **Panel trigger**: `WorkoutCard` and `UnplannedActivityCard` fire `onCardClick` callback instead of navigating
- **State management**: `CalendarPage` holds `selectedWorkout` / `selectedActivity` state; panel is purely presentational
- **Data source**: All data already in CalendarPage state from `CalendarResponse` — panel open = zero DB queries
- **Notes save**: Debounced 500ms on input change, flush on blur. Uses extended PATCH `/calendar/{id}` with optional `notes` field
- **Compliance badge mapping**: `on_target` → "ON TARGET", `close` → "CLOSE", `off_target` → "OFF TARGET", `completed_no_plan` → "COMPLETED"
- **formatPace**: Already exists in `frontend/src/utils/formatting.ts` — `formatPace(secPerKm)` → `"6:00/km"`
- **Panel close**: X button, click backdrop, Escape key — all handled in `WorkoutDetailPanel.tsx`

## Alembic + SQLite Gotchas (added 2026-03-17)

### Always set `render_as_batch=True`

SQLite does not support `ALTER COLUMN` natively. Without `render_as_batch=True` in `alembic/env.py`,
operations like making a column nullable are **silently ignored** — alembic reports success but the
schema doesn't change. Always include this in `run_migrations_online()`:

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    render_as_batch=True,  # Required for SQLite ALTER COLUMN support
)
```

### Always copy alembic into the Docker image

`alembic/` and `alembic.ini` must be in the Dockerfile `COPY` list — they are not source code
and easy to forget. Without them, `alembic upgrade head` can't run in the container.

```dockerfile
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
```

### Run `alembic upgrade head` on container startup

`SQLModel.metadata.create_all` only creates **new** tables — it never alters existing ones.
If a migration adds a column or changes a constraint, `create_all` silently skips it.
Always run migrations before starting uvicorn:

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.api.app:app --host 0.0.0.0 --port 8000"]
```

Same for the `docker-compose.yml` `command:` override (it supersedes the Dockerfile CMD):

```yaml
command: sh -c "alembic upgrade head && uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload"
```

### When a migration was stamped but not applied

If alembic says `(head)` but the schema is wrong, the migration ran without batch mode and was a
no-op. Fix: stamp back to the previous revision, then upgrade:

```bash
alembic stamp <previous-revision-id>
alembic upgrade head
```

---

## Date Parsing — Local Midnight Rule (added 2026-03-23)

`new Date("YYYY-MM-DD")` parses as **UTC midnight** — in non-UTC timezones this is "yesterday" in local time, breaking `isToday`/`isYesterday`/`isSameDay`. Always parse date-only strings as local midnight:

```ts
// ✅ Correct — local midnight
const [y, m, d] = dateStr.split('-').map(Number)
return new Date(y, m - 1, d)

// ❌ Wrong — UTC midnight, fails in UTC- timezones
new Date("2026-03-23")      // → 2026-03-22T16:00:00 in Pacific time
```

Same rule in tests: use local date format for today's date constant:
```ts
// ✅ Correct
const now = new Date()
const TODAY = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

// ❌ Wrong
const TODAY = new Date().toISOString().split('T')[0]  // UTC date, wrong in UTC- timezones
```

`formatDateHeader()` in `formatting.ts` is safe — it appends `'T00:00:00'` before parsing.

---

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

### `useNavigate` requires a Router context in tests (added 2026-03-09)
Any component that calls `useNavigate()` will crash tests with *"useNavigate() may be used only in the context of a Router component."* Wrap renders in `MemoryRouter`:

```typescript
import { MemoryRouter } from 'react-router-dom'

// ✅ Correct — create a renderPage helper
const renderPage = (props: { initialDate?: Date } = {}) =>
  render(<MemoryRouter><CalendarPage {...props} /></MemoryRouter>)

// ❌ Wrong — bare render breaks when any child uses useNavigate
render(<CalendarPage />)
```

Add this wrapper whenever a component or any of its children uses `useNavigate`, `useParams`, `useLocation`, etc.

### `window.matchMedia` not available in jsdom (added 2026-03-19)
jsdom doesn't implement `matchMedia`. A global stub is in `frontend/src/tests/setup.ts` (default: `matches: false` = light mode). Override per-test before rendering:

```typescript
window.matchMedia = vi.fn().mockReturnValue({
  matches: true, // true = dark mode
  media: '(prefers-color-scheme: dark)',
  onchange: null,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
})
```

### ThemeContext localStorage write rule (added 2026-03-19)
`localStorage.setItem('theme', ...)` belongs **only in `toggleTheme`**, not in the DOM-sync `useEffect`. Writing in the sync effect causes the live OS listener guard (`if (!localStorage.getItem('theme'))`) to always see a value and never fire — silently breaking OS-follow behaviour.

### localStorage persistence scope (added 2026-03-19)
localStorage lives in the **browser** — it is unaffected by Render cold restarts or hard browser refresh (Cmd+Shift+R). It is only cleared by: explicit site data clear, incognito mode, or `localStorage.removeItem()`. Cross-device sync requires a DB column; same-device persistence does not.

## FastAPI Optional Dependency Pattern (added 2026-03-09)

Use `try/except` inside a dependency to make an integration optional — returns `None` instead of raising HTTP 403 when the service isn't configured:

```python
async def get_optional_garmin_sync_service(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SyncOrchestrator | None:
    try:
        return await _get_garmin_sync_service(current_user=current_user, session=session)
    except HTTPException:
        return None
```

Callers check `if garmin is not None:` before using. Keeps Garmin logic out of the service layer and makes all Garmin calls best-effort without breaking the primary operation.

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

**Data integrity rule**: `description` must always be derived from `steps` — they are never independent. Whenever `steps` is written to the DB, `description` must be recomputed and saved in the same operation. The Garmin sync reads `template.description` directly, so a stale or null description sends the wrong text to the watch. Full rule in `features/workout-builder/CLAUDE.md`.

---

## Testing in Git Worktrees (added 2026-03-22)

When running tests inside a worktree, the main repo container already holds port 8000.
Never use `docker cp` to sync files — it conflicts with parallel worktree sessions.
Instead, create a local venv:

```bash
cd backend
/Users/noa.raz/.pyenv/versions/3.11.3/bin/python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing
.venv/bin/ruff check src/ tests/
```

Integration tests default to SQLite in-memory — no DB container required.

### File paths in worktrees
Always write files to the worktree path, not the main repo root. Files written to `/workspace/my-garmin-coach/` land on the `main` branch working tree. Files written to `/workspace/my-garmin-coach/.claude/worktrees/<name>/` land on the feature branch.

### MCP servers in worktrees
Each worktree has its own `.mcp.json` (copied from the template at worktree creation time). This file uses `${GITHUB_PERSONAL_ACCESS_TOKEN}` / `${NEON_READONLY_URL}` env var placeholders — but the **Claude Code desktop app does not source `~/.zshrc`**, so those vars are always empty.

**Fix**: hardcode credentials directly in the worktree's `.mcp.json` (it is gitignored):
```json
"env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here" }
```
Also update the project-root `.mcp.json` with the same hardcoded values (desktop app reads from the root first, then the worktree). Restart Claude Code after any `.mcp.json` change — MCP servers are spawned at session start and don't hot-reload.

---

## Ruff E402 — Logger Placement (added 2026-03-22)

`logger = logging.getLogger(__name__)` must be placed **after all module-level imports**, not between them. Placing it between stdlib and third-party imports triggers E402 on every subsequent import. Correct pattern:

```python
import logging
from sqlmodel import select
from src.auth.models import User
# ... all imports ...

logger = logging.getLogger(__name__)  # ← after all imports
router = APIRouter(...)
```

---

## Test Type Hints for Locally-Imported Classes (added 2026-03-22)

When a test helper imports a class inside the function body, don't use it as a string forward ref in the return type — ruff raises F821 even with `from __future__ import annotations`. Use `Any` instead:

```python
from typing import Any

async def _make_activity(self, session: AsyncSession) -> Any:
    from src.db.models import GarminActivity  # local import
    ...
```

---

## Garmin Calendar Cleanup After Pairing (added 2026-03-22)

Garmin's own calendar shows BOTH the scheduled planned workout AND the completed activity after a run. Our app correctly shows only the paired card; Garmin does not auto-remove the plan.

**Fix**: `sync_all` (`backend/src/api/routers/sync.py`) runs an idempotent cleanup sweep after `match_activities()`:
- Queries `completed=True, garmin_workout_id IS NOT NULL` within the sync date window
- Deletes each from Garmin (best-effort, logged + swallowed on failure), clears `garmin_workout_id = None`
- One final `session.commit()` if any rows were touched
- Handles both newly-paired workouts AND retroactive past paired workouts (clearing on next Sync All)

`pair_activity` endpoint (`backend/src/api/routers/calendar.py`) does the same inline before commit, using the optional `get_optional_garmin_sync_service` dependency (already imported, already used by the delete endpoint).

**Why idempotent**: once `garmin_workout_id` is cleared, the query finds no rows on subsequent syncs.

---

## Garmin SSO & API — Akamai Bot Detection (updated 2026-03-25)

Garmin uses **Akamai Bot Manager**. Different subdomains have **different Akamai configs**:

| Subdomain | curl_cffi (chrome TLS) | Standard Python TLS |
|-----------|----------------------|---------------------|
| `sso.garmin.com` (SSO login) | ✅ Allowed | ❌ Blocked |
| `connectapi.garmin.com` (API calls) | ✅ Allowed | ❌ Blocked |
| `connectapi.garmin.com` (OAuth exchange) | ❌ **Blocked** | ✅ Allowed |

**Current fix**: `ChromeTLSSession(impersonate="chrome124")` in `backend/src/garmin/client_factory.py` — single source of truth for all Garmin client creation. `CHROME_VERSION` constant controls the version.

**Factory functions** (both inject `ChromeTLSSession`):
- `create_login_client(proxy_url=None)` → `garth.Client` — used by `garmin_connect.py` for SSO login
- `create_api_client(token_json)` → `GarminAdapter` — used by `sync.py` for all API calls

**Token exchange — DO NOT override `refresh_oauth2`**: garth's native `sso.exchange()` creates a `GarminOAuth1Session(parent=ChromeTLSSession)` which uses standard Python TLS for the exchange. Akamai **allows** standard Python TLS on the exchange endpoint but **blocks** curl_cffi. The login flow proves this — the exchange during login uses standard Python TLS and works from Render without Fixie.

**Anti-pattern**: monkey-patching `refresh_oauth2` to route the exchange through `ChromeTLSSession`/curl_cffi causes 429. This was attempted and reverted (PR #61).

**Retry flow** (login only):
1. Attempt 1: chrome124 TLS, no proxy
2. Attempt 2 (on 429): chrome124 TLS + Fixie proxy — fallback if Akamai updates IP detection

**`ChromeTLSSession` shim** — `curl_cffi.requests.Session` is not a drop-in for `requests.Session`. garth accesses `sess.adapters` and `sess.hooks` internally. The subclass pre-populates both. Never patch attributes one-by-one (fragile — more attributes may break on garth version changes).

```python
class ChromeTLSSession(cffi_requests.Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _rs = requests.Session()
        self.adapters = _rs.adapters
        self.hooks = _rs.hooks
```

**Debugging 429s**: Always check which library raises the error first (`curl_cffi/requests/models.py` vs `requests/models.py`). If curl_cffi raises it, the fix is to NOT use curl_cffi for that endpoint. See `.claude/skills/garmin-429-debug/SKILL.md` for the full diagnostic flow.

- `curl-cffi>=0.6` in `backend/pyproject.toml`
- `FIXIE_URL` optional fallback in `settings.fixie_url` — not required, only consumed on login 429 retry
- **Re-test with `test_garmin_login.py`** (repo root) if 429s return — runs 4 approaches side-by-side to isolate IP vs TLS issues when Akamai updates detection

---

## Neon PostgreSQL — Production DB (added 2026-03-18)

- **Why Neon**: Render free tier has no persistent storage — SQLite is wiped on every restart.
  Neon provides free hosted PostgreSQL (0.5 GB, no credit card, no 7-day pause like Supabase).
- **Split**: Local dev uses SQLite (`sqlite+aiosqlite:////data/garmincoach.db` default).
  Production uses Neon via `DATABASE_URL=postgresql+asyncpg://...` env var.
- **`DATABASE_URL` format for Neon**: `postgresql+asyncpg://user:pass@host.neon.tech/db?ssl=require`
  (asyncpg driver required for SQLAlchemy async; `?ssl=require` mandatory for Neon TLS)
- **Alembic URL stripping**: `alembic/env.py` strips `+aiosqlite` or `+asyncpg` to get the sync URL,
  then converts `ssl=require` → `sslmode=require` (asyncpg vs psycopg2 SSL param names differ):
  `url.replace("+aiosqlite","").replace("+asyncpg","").replace("ssl=require","sslmode=require")`
- **Two drivers needed**: `asyncpg` (SQLAlchemy async runtime) + `psycopg2-binary` (alembic sync migrations).
  Both must be in `[project.dependencies]`.
- **`render_as_batch`**: `True` for SQLite (required for `ALTER COLUMN`), `False` for PostgreSQL.
  `alembic/env.py` sets it conditionally: `render_as_batch=_sync_url.startswith("sqlite")`
- **Naive UTC datetimes**: PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` rejects timezone-aware datetimes.
  All `datetime.now(timezone.utc)` calls that write to DB columns must strip tzinfo:
  `datetime.now(timezone.utc).replace(tzinfo=None)`
- **Render setup**: Set `DATABASE_URL` manually in Render dashboard (not in `render.yaml` — contains credentials).
  Remove the `disk:` block from `render.yaml` (was silently ignored anyway on free tier).
- **Tests**: Integration tests default to SQLite in-memory. Set `TEST_DATABASE_URL=postgresql+asyncpg://...`
  to run the full integration suite against a real PostgreSQL DB.
- **asyncpg rejects libpq-style query params.** `sslmode=require`, `channel_binding=prefer`, etc. cause `TypeError: connect() got an unexpected keyword argument`. asyncpg only accepts `ssl=require`. If Render's DATABASE_URL has libpq params, they must be stripped before `create_async_engine`.
- **User model is Google OAuth only.** `password_hash`, `failed_login_attempts`, `locked_until` dropped (migration `b4e2f1a3c789`). Do not re-add password auth fields.

---

## DB Query Guidelines — Neon Free Tier (added 2026-03-19)

Neon free tier = 100 CU-hours/month. Every DB round-trip costs compute time. Follow these rules:

- **No N+1 queries.** When loading related entities in a loop, batch-load with `SELECT ... WHERE id IN (...)` first, then look up from a dict. Never call `session.get()` inside a loop.
- **Bulk operations.** Use `sqlalchemy.delete()` for multi-row deletes, not fetch-then-delete-each. Use `session.execute()` (not `session.exec()`) for non-SELECT statements (`delete()`, `update()`).
- **Batch commits.** Call `session.add()` multiple times, then a single `session.commit()`. Never commit inside loops.
- **Parallel independent queries.** Use `asyncio.gather()` for independent DB reads in the same request. Example: fetching HR zones + pace zones concurrently instead of sequentially. See `features/garmin-sync/CLAUDE.md` for the pattern used in `_get_zone_maps`.
- **Never hold a session open during external API calls.** Garmin API calls take 1-2s each. Committing DB writes before starting external calls frees the connection pool. For zone-change sync, the entire Garmin sync is now a `BackgroundTask` — see `features/garmin-sync/CLAUDE.md` for the `background_sync` pattern.
- **Never commit partial state before an external API call.** If the API fails, the committed rows become orphaned garbage. Pattern: load all needed DB data → call external API → commit everything in one transaction. Example: `send_chat_message` loads history, calls Gemini, then persists both user + assistant messages in a single commit.
- **`session.refresh()` after commit is a wasted round-trip.** The in-memory object already reflects the committed state. Remove it. Exception: post-act refreshes in integration tests where the row was mutated by a service/router call externally — then `session.refresh()` is the correct way to read back the updated state. The integration test conftest sets `expire_on_commit=False`, so object `.id` is always populated after `session.commit()` without refresh.
- **Cache-aware writes.** Any service that writes to a cached entity must call `cache.invalidate()` after commit. Cached entities: User, AthleteProfile, HRZone, PaceZone. Cache module: `backend/src/core/cache.py`.
- **Cache as dicts, not ORM objects.** SQLAlchemy ORM objects are bound to a session — caching them causes `DetachedInstanceError` on the next request. Serialize to a plain dict before `cache.set()`, reconstruct with `Model(**dict)` on hit. See `auth/dependencies.py` (User) and `services/profile_service.py` (AthleteProfile).
- **Don't cache on write paths.** After creating/updating, call `cache.invalidate()` — don't `cache.set()`. Let the next read populate. Bulk deletes (e.g. `reset_admins`) must call `cache.clear()` after commit.
- **Connection pool.** Production uses `pool_pre_ping=True` and `pool_recycle=270`. Don't change these without understanding Neon's scale-to-zero behavior (5-min idle timeout).
- **No raw SQL.** Always use SQLAlchemy/SQLModel constructs — per Security rules above.
- **`session.add()` after ORM mutation.** Async SQLAlchemy does not always track in-place attribute changes. After mutating an existing ORM object (e.g. `workout.completed = True`), call `session.add(workout)` before commit.

---

## Ruff DTZ Rules — Datetime Convention Enforcement (added 2026-03-20)

`pyproject.toml` enables `extend-select = ["DTZ"]` (flake8-datetimez). This bans:
- `datetime.utcnow()` → use `datetime.now(timezone.utc).replace(tzinfo=None)`
- `datetime.utcfromtimestamp()` → use `datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)`
- `date.today()` in prod code → use `datetime.now(timezone.utc).date()`

`tests/**` are exempt from `DTZ011` (`date.today()` is fine in tests).

The `.replace(tzinfo=None)` is required because PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` columns reject aware datetimes.

---

## Render Preview Deployments (added 2026-03-20)

- **Trigger**: PR title containing `[Render Preview]` triggers a Render preview deployment via GitHub Deployments API
- **Preview env vars are separate** from the main Render service. They don't auto-inherit updates — must be set independently in Render dashboard → "Preview Environments" settings
- **Common failure**: `DATABASE_URL=postgresql://...` (missing `+asyncpg`) → `psycopg2 is not async` error. Must be `postgresql+asyncpg://...`
- **Check deployment status**: `gh api repos/noaraz/my-garmin-coach/deployments -q '.[0].id'` → `gh api .../deployments/{id}/statuses -q '.[0] | {state, environment_url}'`
- **States**: `success` (live), `in_progress` (building), `inactive` (spun down, wakes on request), `failure` (check logs)

---

## Context Refresh Pattern (added 2026-03-21)

When wiring `refresh()` / `refreshZones()` from a shared context into a component, call it in **all** write handlers — not just the primary one. Put it in a `finally` block so it runs even on error. Example: `ZoneManager.handleSave` calls `refreshZones()` in `finally` so the sidebar indicator always reflects current DB state, regardless of whether the save succeeded or failed.

## ZoneManager UX Pattern (added 2026-03-23)

- **Single Save action**: `handleSave` calls `save(profile)` → `recalcHR()` → `recalcPace()` in sequence. No standalone recalc buttons.
- **Saving indicator**: `isSaving` boolean state passed to `ThresholdInput` — button shows "Saving…" and is `disabled` while the async chain is in flight.
- **HR zones are display-only**: `HRZoneTable` renders BPM values as plain text; no click-to-edit. Zones update only via the Save recalc.
- **`refreshZones()` in `finally`**: always runs after save, even on error, so the sidebar indicator stays in sync with DB state.

## PLAN.md Tracking (added 2026-03-21)

Root `PLAN.md` feature table emoji must be updated to ✅ when a feature is complete — same cadence as `STATUS.md`. Easy to miss since STATUS.md is the primary tracking file.

## Git Rebase Without Editor (added 2026-03-21)

`GIT_EDITOR=true git rebase --continue` — skips the commit message editor when continuing a rebase after resolving conflicts.

## Status Indicators (added 2026-03-20)

- **GarminStatusContext** (`frontend/src/contexts/GarminStatusContext.tsx`): fetches `getGarminStatus()` on mount, exposes `garminConnected: boolean | null` + `refresh()`. Provider mounted in `AppShell.tsx`.
- **ZonesStatusContext** (`frontend/src/contexts/ZonesStatusContext.tsx`): fetches `fetchProfile()` on mount, derives `zonesConfigured = profile.threshold_pace !== null`, exposes `zonesConfigured: boolean | null` + `refreshZones()`. Provider mounted in `AppShell.tsx`.
- **Sidebar Garmin row**: `<button>` below Settings NavLink. `aria-label="Garmin: Connected – go to Settings"` / `"Not connected"` variant. Hover via local `hovered` state + `onMouseEnter`/`onMouseLeave`. Constants: `SIDE_GARMIN_CONNECTED = '#22c55e'`, `SIDE_GARMIN_DISCONNECTED = '#ef4444'`, `SIDE_ZONES_WARN = '#f59e0b'`.
- **CalendarPage auto-sync migration**: null guard (`if (garminConnected === null) return`) MUST come before `autoSyncDone` ref check to avoid the ref being consumed on the first null render before context resolves. Effect deps: `[garminConnected]`.
- **SettingsPage**: calls `refresh()` from `useGarminStatus()` after connect and after disconnect.
- **ZoneManager**: calls `refreshZones()` from `useZonesStatus()` in a `finally` block in `handleSave` — runs on both success and error paths.
- **Sidebar tests**: wrap render in `<GarminStatusProvider><ZonesStatusProvider>`. Both contexts need mocks via `vi.hoisted`.
- **Calendar tests**: wrap `renderPage` in `<GarminStatusProvider>`. Add `mockGetGarminStatus` to `vi.hoisted` + existing `vi.mock('../api/client')` factory.

## Onboarding Maintenance (added 2026-03-21)

When adding a new page/feature to GarminCoach, also:
1. Add a step to `STEPS` array in `frontend/src/components/onboarding/OnboardingWizard.tsx`
2. Add a feature card in `frontend/src/pages/HelpPage.tsx`
3. Update `features/onboarding/PLAN.md`

**localStorage key**: `onboarding_completed_${userId}` — one per user, set on wizard Finish or Skip.
Replay Tour (HelpPage) clears the key and calls `openWizard()` from `OnboardingContext`.
`OnboardingProvider` is mounted in `AppShell.tsx` (outermost provider, wraps GarminStatusProvider + ZonesStatusProvider).

---

## PlanPromptBuilder Patterns (added 2026-03-22)

### Fetch button state machine
`fetchState: 'idle' | 'fetching' | 'done' | 'empty' | 'error'` drives the fetch button label and inline feedback badge.
`idle → fetching → done | empty | error`. `empty` = API returned 0 results; `error` = network/auth failure.
`activities` is never cleared on re-fetch or error — old data stays in the prompt until a new fetch succeeds.
Do not collapse `error` into `empty` — user must know whether they have no runs or whether the fetch failed.

### Health notes field
`healthNotes: string` — free text textarea placed after the long run day select.
When non-empty, the prompt includes: `My current health & shape: [notes]`.
When empty, the line is omitted entirely from the generated prompt.

### Rolling 2–3 week horizon
`buildPrompt()` uses a rolling 2–3 week window (not a fixed calendar range). Activity section label: `## Recent Training (last 14 days)`. Only rendered when `activities.length > 0`.

### Why `useEffect` was removed
Silent auto-fetch hid what Garmin context was being injected into the prompt. The explicit fetch button lets the user inspect which activities are included before copying to their LLM.

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

**`webServer` config required**: `playwright.config.ts` must include a `webServer` block (`command: 'npm run dev'`, `url: 'http://localhost:5173'`, `reuseExistingServer: !process.env.CI`). Without it, `npx playwright test` fails with `ERR_CONNECTION_REFUSED` unless the dev server is already running manually.

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
