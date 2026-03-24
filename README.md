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

## Training Zones — Reference Inputs

When setting up the Zone Manager for the first time, use these reference values based on your fitness level.

Zones are calculated using the **Friel method** (% of LTHR) for HR, and **Daniels-style** (% of threshold speed) for pace.

### Average runner

| Input | Value |
|-------|-------|
| LTHR | 160 bpm |
| Threshold Pace | 330 sec/km (5:30/km) |

| Zone | BPM | Pace |
|------|-----|------|
| Z1 Easy | 0–130 | 6:58–7:51 /km |
| Z2 Moderate | 131–142 | 6:19–6:53 /km |
| Z3 Tempo | 143–149 | 5:47–6:15 /km |
| Z4 Threshold | 150–158 | 5:20–5:44 /km |
| Z5 Interval | 160–176 | 4:47–5:17 /km |

### Less fit / returning runner

| Input | Value |
|-------|-------|
| LTHR | 150 bpm |
| Threshold Pace | 390 sec/km (6:30/km) |

| Zone | BPM | Pace |
|------|-----|------|
| Z1 Easy | 0–122 | 8:14–9:17 /km |
| Z2 Moderate | 123–134 | 7:28–8:08 /km |
| Z3 Tempo | 135–140 | 6:51–7:23 /km |
| Z4 Threshold | 141–149 | 6:19–6:46 /km |
| Z5 Interval | 150–165 | 5:39–6:15 /km |

To find your actual values: run 30 min all-out — LTHR ≈ average HR of the last 20 min, threshold pace ≈ average pace of the full effort. Or use your recent 10K race data.

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
   - `FIXIE_URL` — from [usefixie.com](https://usefixie.com) (optional — Garmin login uses Chrome 120 TLS fingerprint to bypass Akamai bot detection; Fixie is only a fallback if Akamai updates its detection and starts blocking cloud IPs again)
5. `autoDeploy: false` — deploys are triggered manually or via the `/release` workflow.

On container start, `alembic upgrade head` runs automatically before uvicorn — it creates all tables on the first deploy and applies any new migrations on subsequent deploys.

**Create the first user** (one-time):

Navigate to `https://your-app.onrender.com/setup` and enter your email, password, and the `BOOTSTRAP_SECRET` value from the Render dashboard. This calls `POST /api/v1/auth/bootstrap` and creates the admin account.

**Trigger a deploy:**

Use the `/release` command in Claude Code, or push a version tag and approve the GitHub Actions gate.