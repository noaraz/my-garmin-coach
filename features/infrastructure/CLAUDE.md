# Infrastructure — CLAUDE

## Docker Gotchas

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

### Known issues (tracked in STATUS.md)

1. **`create_db_and_tables()` still runs in lifespan** — `app.py` calls `SQLModel.metadata.create_all()` on startup. Since alembic runs first, this is always a no-op on an existing DB. But it means alembic is not strictly the sole schema manager. Remove when convenient.

2. **`InviteCode` missing from `env.py` imports** — `alembic/env.py` imports `AthleteProfile, HRZone, PaceZone, WorkoutTemplate, ScheduledWorkout, User` but not `InviteCode`. The comment says "Import all models so autogenerate detects them." Future `alembic revision --autogenerate` runs will miss changes to `InviteCode`. Fix: `from src.auth.models import User, InviteCode`.

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
