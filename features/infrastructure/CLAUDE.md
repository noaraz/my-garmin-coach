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

## FastAPI Static File Mount (Production)

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```
