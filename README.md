# my-garmin-coach

A self-hosted training platform for runners using Garmin watches.

---

## Deployment

### Local Dev

Hot reload for both backend and frontend. Uses hardcoded dev secrets — do not use in production.

```bash
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

Run tests:

```bash
docker compose exec backend pytest -v
```

---

### Local Prod

Builds production images (minified React + optimised backend) using real secrets from `.env.prod`.

Copy `.env.example` to `.env.prod` and fill in values:

```bash
cp .env.example .env.prod
# edit .env.prod — set JWT_SECRET, GARMINCOACH_SECRET_KEY, BOOTSTRAP_SECRET, CORS_ORIGINS, GOOGLE_CLIENT_ID, etc.
```

Generate secrets:

```bash
openssl rand -hex 32   # use once for JWT_SECRET, once for GARMINCOACH_SECRET_KEY
```

Start:

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  up --build
```

App is served on http://localhost (port 80). The frontend (nginx) proxies `/api/` to the backend container.

---

### Render

Render uses `render.yaml` at the repo root. It provisions the web service, persistent disk (`/data`), and auto-generates secrets.

**First deploy:**

1. Go to [render.com](https://render.com) → New → Blueprint → connect the GitHub repo.
2. Render detects `render.yaml` — no manual env var setup needed.
3. Set `GOOGLE_CLIENT_ID` manually in the Render dashboard (not in `render.yaml`).
4. `autoDeploy: false` — deploys are triggered manually or via the `/release` workflow.

On container start, `alembic upgrade head` runs automatically before uvicorn — it creates all tables on the first deploy and applies any new migrations on subsequent deploys.

**Create the first user** (one-time):

Navigate to `https://your-app.onrender.com/setup` and enter your email, password, and the `BOOTSTRAP_SECRET` value from the Render dashboard. This calls `POST /api/v1/auth/bootstrap` and creates the admin account.

**Trigger a deploy:**

Use the `/release` command in Claude Code, or push a version tag and approve the GitHub Actions gate.