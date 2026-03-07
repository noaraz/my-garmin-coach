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

### Render Deployment (after auth is done)
- [ ] Push to GitHub with `Dockerfile.prod` at root
- [ ] Create Render Web Service (Docker, free tier)
- [ ] Set environment variables in Render dashboard
- [ ] Configure persistent disk at `/data` (1 GB)
- [ ] Verify: app accessible at `https://your-app.onrender.com`

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
    "python-garminconnect>=0.2.19",
    "pydantic>=2.5",
    "httpx>=0.25",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "cryptography>=41.0",
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
