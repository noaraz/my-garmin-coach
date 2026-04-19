# Infrastructure — CLAUDE

## Docker Gotchas

- **Always use a venv in Python Docker images**: Install into `/venv` to avoid the pip-root-user warning and follow official Docker best practice. Pattern used in both `Dockerfile.prod` and `backend/Dockerfile`:
  ```dockerfile
  RUN python -m venv /venv
  ENV PATH="/venv/bin:$PATH"
  RUN pip install --no-cache-dir -e "."
  ```
  `/venv` is created as root but is world-readable, so `appuser` can execute from it at runtime.

- **Proxy in Docker Compose**: frontend proxies to `http://backend:8000`, not `localhost`.
- **Volumes**: Mount `src/` for hot reload. Use anonymous volumes for `node_modules`:
  ```yaml
  volumes:
    - ./frontend/src:/app/src
    - /app/node_modules
  ```
- **SQLite on named volume**: DB file must be on `backend_data:/data`, not container fs.
- **Production**: FastAPI serves React build as static files. No separate frontend
  container. No CORS needed.

## Env Vars

```
GARMINCOACH_SECRET_KEY   # master encryption key (32+ random chars)
JWT_SECRET               # JWT signing key (separate from above)
DATABASE_URL             # sqlite+aiosqlite:////data/garmincoach.db  ← aiosqlite driver required
ENVIRONMENT              # development | production
CORS_ORIGINS             # read by Settings.cors_origins (list[str])
GARMIN_TOKENS_DIR        # /data/garmin-tokens
```

> **Note:** CORS is configured in `create_app()` via `CORSMiddleware` (not Nginx). Origins come from
> `src/core/config.py` `Settings.cors_origins` (default: localhost:5173 and localhost:3000).

## Database Schema Migrations

### How it works (as of 2026-03-11)

Alembic is the **sole schema authority** for production. `Dockerfile.prod` CMD:

```
alembic upgrade head && uvicorn src.api.app:app ...
```

- On first deploy (empty DB): alembic creates all 7 tables via the initial migration
- On subsequent deploys: alembic applies any new migration files, then uvicorn starts
- `alembic` must be in **main** `[project.dependencies]` — not dev-only — so it's installed in the prod image

### Schema change workflow

```bash
# 1. Modify the SQLModel in src/
# 2. Generate migration (run inside container or with empty-DB test image)
docker compose exec backend alembic revision --autogenerate -m "describe change"
# 3. IMPORTANT: add 'import sqlmodel' to the generated file if it uses AutoString
#    Alembic autogenerate omits this import — migration will NameError without it
# 4. Review the generated file in backend/alembic/versions/
# 5. Apply locally
docker compose exec backend alembic upgrade head
# 6. Commit the migration file with the model change
# 7. Next deploy applies it automatically (alembic runs before uvicorn)
```

### Local DB state

The local Docker-volume DB (`backend_data:/data/garmincoach.db`) was stamped at head after manual `ALTER TABLE` statements were run during the auth feature. It is in sync with the current schema.

---

## Render Deployment Notes

- **Render Shell**: Not available on the free plan. Use the "Events" tab in the Render
  dashboard to inspect build and deploy logs. To exec into a running container, upgrade
  to a paid plan.
- **autoDeploy: false**: Render does not deploy on every push. Trigger deploys manually
  via the Render dashboard or use the `/release` workflow (tags + deploy hook).
- **Docker build stage**: The `frontend-build` stage in `Dockerfile.prod` must set
  `ENV NODE_ENV=development` before `npm ci`, otherwise Docker may skip `devDependencies`
  (which includes `vite` and `tsc`), causing a silent build failure where `/app/static`
  is never created and FastAPI serves 404 for all SPA routes.

---

## Neon PostgreSQL — Production DB (added 2026-03-18)

### Why Neon

Render free tier has no persistent disk. SQLite at `/data/garmincoach.db` is wiped on every
container restart (inactivity spin-down or redeployment). Neon was chosen over Supabase because
Supabase pauses projects after 7 days of inactivity (requires a manual click to restore — unusable
for a personal tool used weekly). Neon scales to zero after 5 min idle but restores transparently
on the next query (cold start ~1s, invisible to users).

### DATABASE_URL split: SQLite (dev) vs PostgreSQL (prod)

```
Dev  (docker-compose.yml):     DATABASE_URL=sqlite+aiosqlite:////data/garmincoach.db   ← default
Prod (Render env dashboard):   DATABASE_URL=postgresql+asyncpg://user:pass@host.neon.tech/db?ssl=require
```

`?ssl=require` is mandatory — Neon requires TLS.

### Alembic URL stripping (`alembic/env.py`)

Alembic uses a synchronous driver (`psycopg2` for PostgreSQL, `sqlite3` for SQLite). Strip the
async driver suffix before passing to alembic, and also convert the SSL param:

```python
_db_url = os.environ.get("DATABASE_URL", "sqlite:////data/garmincoach.db")
_sync_url = _db_url.replace("+aiosqlite", "").replace("+asyncpg", "")
# asyncpg uses ?ssl=require; psycopg2 uses ?sslmode=require
_sync_url = _sync_url.replace("ssl=require", "sslmode=require")
```

Both `asyncpg` and `psycopg2-binary` must be in `[project.dependencies]`:
- `asyncpg` — used by SQLAlchemy async engine at runtime
- `psycopg2-binary` — used by alembic's synchronous migration engine

`render_as_batch` is required for SQLite ALTER COLUMN but must be off for PostgreSQL (it causes
unnecessary wrapping). Set it conditionally:

```python
_is_sqlite = _sync_url.startswith("sqlite")
context.configure(
    ...,
    render_as_batch=_is_sqlite,
)
```

### Running integration tests against PostgreSQL

The integration test fixture in `tests/integration/conftest.py` accepts `TEST_DATABASE_URL`:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@host.neon.tech/testdb?ssl=require \
  pytest tests/integration/ -v
```

Default (no env var) = SQLite in-memory, unchanged.

### Provisioning a Neon project

1. neon.com → free account (no credit card)
2. New project → region closest to Render service (e.g. `us-east-1`)
3. Connection string → "Connection pooling" OFF → copy `postgresql://...` URL
4. Prepend `+asyncpg`: `postgresql+asyncpg://user:pass@host.neon.tech/db?ssl=require`
5. Render dashboard → backend service → Environment → `DATABASE_URL` = the URL above
6. Never commit this URL to `render.yaml` or any tracked file

---

## Render Preview Environments (added 2026-03-20)

- **Preview env vars are separate** from the main Render service — they don't auto-inherit updates. Set `DATABASE_URL`, `GARMINCOACH_SECRET_KEY`, `GOOGLE_CLIENT_ID` independently in Render dashboard → service → "Preview Environments" settings
- **`DATABASE_URL` must use `+asyncpg`** driver: `postgresql+asyncpg://...`. Plain `postgresql://...` causes `psycopg2 is not async` crash at startup
- **Deployment status via GitHub API**: `gh api repos/noaraz/my-garmin-coach/deployments` → get latest deployment ID → check `statuses` endpoint for `state`, `environment_url`, `log_url`

## Preview DB Isolation (added 2026-04-18)

Render Preview environments use a dedicated Neon **branch** (`preview`) inside the same
Neon project. Before each preview deploy, a GitHub Actions workflow resets this branch to
the `main` (prod) state — copy-on-write, instant, free. The preview container then runs
`alembic upgrade head` on the isolated branch. Prod is never touched.

### One-time setup

1. **neon.tech** → garmincoach project → Branches → create branch `preview` from `main`
   - Copy the preview branch connection string (ends in `?ssl=require`) — this is `PREVIEW_DATABASE_URL`
   - Copy the preview branch ID (`br-xxxx-yyyy` shown in branch details) — `NEON_PREVIEW_BRANCH_ID`
   - Copy the main branch ID (`br-xxxx-yyyy` — different from preview) — `NEON_MAIN_BRANCH_ID`
   - Account Settings → API Keys → create a new API key — `NEON_API_KEY`
   - Project Settings → copy the project ID (e.g. `long-fog-12345678`) — `NEON_PROJECT_ID`

2. **Render dashboard** → Account Settings → API Keys → create key — `RENDER_API_KEY`

3. **GitHub** → repo Settings → Secrets and variables → Actions → add:
   - `NEON_API_KEY`
   - `NEON_PROJECT_ID`
   - `NEON_PREVIEW_BRANCH_ID`
   - `NEON_MAIN_BRANCH_ID`
   - `RENDER_API_KEY`
   - `PREVIEW_DATABASE_URL` (the Neon preview branch connection string — contains credentials, never commit this)

   No per-PR secrets needed — the workflow finds the right preview service dynamically by matching the PR branch name.

### How it works on each PR push

```
PR pushed to GitHub
    └── GitHub Actions: preview-db-reset.yml
            1. POST /neon/.../branches/{preview_id}/restore   ← reset to prod state (instant)
            2. sleep 10s
            3. GET /render/.../services/{preview_id}/env-vars  ← read current env vars
            4. Replace DATABASE_URL with preview Neon branch URL
            5. PUT /render/.../services/{preview_id}/env-vars  ← update in place
            6. POST /render/.../services/{preview_id}/deploys  ← trigger rebuild

Render container starts → alembic upgrade head → runs on preview branch only
```

### Gotchas

- **First deploy of a brand-new preview uses prod DATABASE_URL** — Render creates the service by copying the base service's env vars (prod DATABASE_URL). Push a commit immediately after creating the preview to let the workflow correct it before any migrations run.
- **Preview service lookup by branch name** — the workflow searches Render services filtered by name `garmincoach` and matches on `branch == PR branch name`. If the preview service isn't found, the workflow warns and skips (no error) — create the preview in Render first, then push a commit.
- **Preview branch URL is static** — the Neon preview branch connection string never changes even after resets. It's a persistent credential.
- **Two open PRs share one preview branch** — sequential is fine for a solo project; simultaneous deploys would conflict (last reset wins).
- **Neon restore is async** — the workflow sleeps 10s. If `alembic upgrade head` fails with `relation does not exist`, increase the sleep in the workflow.
- **Branch IDs vs branch names** — the Neon restore API requires branch IDs (`br-xxxx-yyyy`), not names. Get them from neon.tech → Branches → click the branch → copy the ID from the URL or details panel.
- **Render PUT env-vars replaces all vars** — the workflow GETs the full current list first, updates only `DATABASE_URL`, then PUTs the complete list back. This preserves `JWT_SECRET`, `GARMINCOACH_SECRET_KEY`, etc.

---

## FastAPI Static File Mount (Production)

`StaticFiles(html=True)` does NOT do SPA fallback — it returns 404 for paths like `/login`
that don't exist as files. Use a catch-all route instead:

```python
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    # Serve hashed JS/CSS assets
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    # Catch-all: serve exact static file or fall back to index.html (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        file = static_dir / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(static_dir / "index.html")
```
