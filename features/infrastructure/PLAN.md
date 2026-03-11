# Infrastructure — PLAN

## Description

Project scaffolding, Docker Compose for local dev, production Docker build,
and Render deployment. This is the foundation everything else runs on.

Track progress in **STATUS.md**.

---

## Tasks

### Scaffolding
- [ ] Create directory structure: `backend/src/`, `backend/tests/`, root files
- [ ] Write `backend/pyproject.toml` with all dependencies
- [ ] Write `backend/Dockerfile` (dev, with hot reload)
- [ ] Write `docker-compose.yml` (backend service, named volume, hot reload)
- [ ] Write minimal `backend/src/api/app.py` with `/api/health` endpoint
- [ ] Write `.env.example` documenting all env vars
- [ ] Write `.gitignore`
- [ ] Verify: `docker compose up --build` starts backend on :8000
- [ ] Verify: `curl localhost:8000/api/health` returns `{"status":"ok"}`
- [ ] Verify: `docker compose exec backend pytest --co` runs without errors

### Production Docker (after features 2–7 are done)
- [ ] Write `Dockerfile.prod` (multi-stage: build React → serve via FastAPI)
- [ ] Write `docker-compose.prod.yml`
- [ ] Verify: `docker compose -f docker-compose.prod.yml up --build` serves full app
- [ ] Add FastAPI StaticFiles mount for React build

### Database Migrations ✅ Done (2026-03-11)
- [x] Add Alembic to `backend/pyproject.toml` **main** dependencies (not dev-only — needed in prod container)
- [x] Run `alembic init alembic` inside the backend container
- [x] Configure `alembic/env.py`: import all models, set `target_metadata = SQLModel.metadata`, derive sync URL from `DATABASE_URL` env var (strips `+aiosqlite`), set `compare_type=False`
- [x] Generate initial migration from empty DB: `alembic revision --autogenerate -m "initial schema"` — creates all 7 tables from scratch
- [x] Add `import sqlmodel` to the generated migration file (alembic autogenerate omits this import)
- [x] Dockerfile.prod CMD runs `alembic upgrade head` before uvicorn starts — alembic is sole schema authority on first deploy
- [x] Stamp local Docker volume DB: `alembic stamp head` (local DB already had tables from `create_all()`)

> **First Render deploy**: DB is empty. `alembic upgrade head` in the container CMD creates all tables
> via the initial migration. `create_all()` in the lifespan then runs but is a no-op (tables exist).
> No manual stamping needed — alembic already recorded the revision in `alembic_version`.

> **Going forward**: for any schema change, run `alembic revision --autogenerate -m "desc"` locally,
> review the generated file, add `import sqlmodel` if the file uses `sqlmodel.sql.sqltypes.AutoString`,
> apply locally (`alembic upgrade head`), commit migration file, then the next deploy applies it automatically.

> **Known issue**: `create_db_and_tables()` in `app.py` lifespan still calls `SQLModel.metadata.create_all()`.
> This is a no-op when alembic has already created tables, but it means alembic is not the *sole* schema
> authority. Should be removed in a future cleanup (see STATUS.md).

> **Known issue**: `InviteCode` model is missing from `alembic/env.py` imports. The comment says
> "Import all models so autogenerate detects them" but `InviteCode` is omitted. Add
> `from src.auth.models import User, InviteCode` to fix future autogenerate accuracy (see STATUS.md).

### Security Review (before Render deploy)
- [ ] Run `/code-review` on the full codebase (auth routes, token handling, Garmin OAuth, CORS)
- [ ] Verify: no secrets in code or git history
- [ ] Verify: JWT expiry + refresh flow is correct
- [ ] Verify: Garmin tokens are encrypted at rest (Fernet), never logged
- [ ] Verify: all routes require auth except `/api/health`, `/api/v1/auth/login`, `/api/v1/auth/register`
- [ ] Verify: invite-only registration is enforced
- [ ] Verify: CORS origins locked to production domain in `render.yaml`

### Render Deployment (first deploy)
- [ ] Go to render.com → New Web Service → connect GitHub repo
- [ ] Render auto-detects `render.yaml` — no manual env var setup needed (JWT_SECRET + GARMINCOACH_SECRET_KEY auto-generated, disk provisioned, autoDeploy: false)
- [ ] Push `v0.1.0` tag → CI gate → approve in GitHub → Render deploy hook fires automatically
- [ ] Container starts: `alembic upgrade head` creates all tables, then uvicorn starts
- [ ] Create admin user via Render Shell (first-time only):
  ```bash
  # In Render Shell at /app:
  python3 - <<'EOF'
  import asyncio, os
  from sqlmodel.ext.asyncio.session import AsyncSession
  from sqlalchemy.ext.asyncio import create_async_engine
  from src.auth.models import User
  from src.auth.utils import get_password_hash

  async def main():
      engine = create_async_engine(os.environ["DATABASE_URL"])
      async with AsyncSession(engine) as session:
          user = User(email="your@email.com", hashed_password=get_password_hash("yourpassword"))
          session.add(user)
          await session.commit()
          print(f"Created: {user.email}")

  asyncio.run(main())
  EOF
  ```
- [ ] Verify: `https://garmincoach.onrender.com` loads login page
- [ ] Verify: login works
- [ ] Verify: Garmin connect flow works end-to-end

### Release Management
See **`RELEASING.md`** at the repo root — versioning scheme, full workflow, GitHub Release commands.

- [ ] After Render deploy is verified: follow `RELEASING.md` to tag `v1.0.0` and create GitHub Release

---

## Reference: pyproject.toml

```toml
[project]
name = "garmin-coach"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104",
    "uvicorn[standard]>=0.24",
    "sqlmodel>=0.0.14",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.19",
    "garminconnect>=0.2.19",
    "pydantic>=2.5",
    "pydantic-settings>=2.0",
    "httpx>=0.25",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "cryptography>=41.0",
    "alembic>=1.13",   # must be in main deps — used by Dockerfile.prod CMD
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "httpx>=0.25",
    "ruff>=0.1",
]
```

## Reference: docker-compose.yml (Local Dev)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=sqlite:///data/garmincoach.db
      - GARMINCOACH_SECRET_KEY=local-dev-secret-change-in-prod
      - JWT_SECRET=local-dev-jwt-secret-change-in-prod
      - ENVIRONMENT=development
    volumes:
      - ./backend/src:/app/src
      - ./backend/tests:/app/tests
      - backend_data:/data
    command: uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

volumes:
  backend_data:
```

## Reference: docker-compose.prod.yml

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=sqlite:///data/garmincoach.db
      - GARMINCOACH_SECRET_KEY=${GARMINCOACH_SECRET_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - ENVIRONMENT=production
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    volumes: ["app_data:/data"]

volumes:
  app_data:
```

## Reference: Dockerfile.prod

```dockerfile
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir -e "."
COPY backend/src ./src
COPY --from=frontend-build /frontend/dist ./static
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Reference: Render Setup

1. Connect GitHub repo → New Web Service → Docker
2. Env vars: `GARMINCOACH_SECRET_KEY`, `JWT_SECRET`, `ALLOWED_ORIGINS`, `ENVIRONMENT=production`
3. Persistent disk: mount `/data`, 1 GB
4. Upgrade path: $7/mo for always-on, or Oracle Cloud free tier + Coolify
