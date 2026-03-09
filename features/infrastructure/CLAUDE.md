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

## Database Schema Migrations — Critical Pre-Render Step

### The problem
SQLModel calls `SQLModel.metadata.create_all()` on startup. This creates tables that don't exist
yet, but **never alters existing tables**. Tests use in-memory SQLite (always fresh schema) so
drift between the live DB and the current models is invisible to the test suite.

### What happened (2026-03-09)
The Docker-volume DB was created before the auth feature added `user_id`,
`garmin_oauth_token_encrypted`, and `garmin_connected` columns. The backend 500-errored on
Garmin connect. Fixed by running manual `ALTER TABLE` inside the container:

```bash
docker compose exec backend python - <<'EOF'
import sqlite3, os
db_path = "/data/garmincoach.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
stmts = [
    "ALTER TABLE athleteprofile ADD COLUMN user_id INTEGER REFERENCES user(id)",
    "ALTER TABLE athleteprofile ADD COLUMN garmin_oauth_token_encrypted TEXT",
    "ALTER TABLE athleteprofile ADD COLUMN garmin_connected BOOLEAN DEFAULT 0",
    "ALTER TABLE workouttemplate ADD COLUMN user_id INTEGER REFERENCES user(id)",
    "ALTER TABLE hrzone ADD COLUMN user_id INTEGER REFERENCES user(id)",
    "ALTER TABLE pacezone ADD COLUMN user_id INTEGER REFERENCES user(id)",
    "ALTER TABLE scheduledworkout ADD COLUMN user_id INTEGER REFERENCES user(id)",
]
for s in stmts:
    try:
        cur.execute(s)
        print(f"OK: {s}")
    except Exception as e:
        print(f"SKIP ({e}): {s}")
conn.commit()
conn.close()
EOF
```

### Before Render deploy — run the same statements on the Render DB
The Render persistent disk DB has the old schema too. Options:
1. SSH into Render instance and run the script above (pointing at the Render `/data` path)
2. Or set up Alembic first (see PLAN.md) and run `alembic upgrade head` instead

### Long-term fix: Alembic
See `Database Migrations` section in PLAN.md. Until Alembic is set up, every new column requires
a manual ALTER TABLE on both the local Docker volume DB and the Render DB.

---

## FastAPI Static File Mount (Production)

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```
