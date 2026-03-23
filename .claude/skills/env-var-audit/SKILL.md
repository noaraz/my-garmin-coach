---
name: env-var-audit
description: Audit environment variable drift between backend/src/core/config.py Settings class, .env.example, docker-compose.yml, and render.yaml. Run when adding new settings or before any release.
---

Check env var consistency across all 4 sources:

## 1. Read `backend/src/core/config.py`
Extract all field names from the `Settings(BaseSettings)` class.
Note which have defaults (optional at runtime) vs no defaults (required at runtime).

## 2. Read `.env.example`
Extract all `VAR_NAME=` keys.

## 3. Read `docker-compose.yml`
Extract `environment:` entries under the `backend` service.
Format: `VAR_NAME: ...` or `VAR_NAME=...` or `- VAR_NAME`.

## 4. Read `render.yaml`
Extract `envVars:` entries under the backend service.
Format: `key: VAR_NAME`.

## 5. Report drift

Output format:
```
[MISSING FROM .env.example] VAR_NAME — required/optional
[MISSING FROM docker-compose.yml] VAR_NAME — required/optional
[MISSING FROM render.yaml] VAR_NAME — required/optional
[UNDECLARED IN config.py] VAR_NAME — found in env files but no matching Settings field
```

## Notes

- `DATABASE_URL` and credential vars (JWT_SECRET_KEY, FERNET_KEY, etc.) are intentionally absent from `render.yaml` — they're set manually in the Render dashboard. Flag as `[RENDER-ONLY — confirm intentional]`.
- `FIXIE_URL` is prod-only (empty in dev). Expected to be missing from docker-compose.yml.
- `VITE_GOOGLE_CLIENT_ID` is a frontend build-time var passed as Docker ARG — it's in Dockerfile.prod, not docker-compose.yml. Expected.

If no drift: `"No env var drift detected."`
