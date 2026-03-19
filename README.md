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
# edit .env.prod — fill in all values (see comments in the file)
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

Render uses `render.yaml` at the repo root. It provisions the web service and auto-generates secrets.

Production uses [Neon](https://neon.tech) (free tier) for PostgreSQL — Render free tier has no persistent disk, so SQLite is not viable.

**First deploy:**

1. Create a Neon project at [neon.tech](https://neon.tech) and copy the connection string.
2. Go to [render.com](https://render.com) → New → Blueprint → connect the GitHub repo.
3. Render detects `render.yaml` — auto-generates `JWT_SECRET` and `GARMINCOACH_SECRET_KEY`.
4. Set these manually in the Render dashboard → Environment:
   - `DATABASE_URL` — Neon connection string (`postgresql+asyncpg://...?ssl=require`)
   - `GOOGLE_CLIENT_ID` — from Google Cloud Console
   - `BOOTSTRAP_SECRET` — `openssl rand -hex 32`
   - `FIXIE_URL` — from [usefixie.com](https://usefixie.com) (optional, avoids Garmin 429s)
5. `autoDeploy: false` — deploys are triggered manually or via the `/release` workflow.

On container start, `alembic upgrade head` runs automatically before uvicorn — it creates all tables on the first deploy and applies any new migrations on subsequent deploys.

**Create the first user** (one-time):

Navigate to `https://your-app.onrender.com/setup`, sign in with Google, and enter the `BOOTSTRAP_SECRET` value from the Render dashboard. This calls `POST /api/v1/auth/bootstrap` and creates the admin account. The endpoint disables itself once the first user exists.

**Trigger a deploy:**

Use the `/release` command in Claude Code, or push a version tag and approve the GitHub Actions gate.