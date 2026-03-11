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

## FastAPI Static File Mount (Production)

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```
