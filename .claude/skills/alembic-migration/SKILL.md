---
name: alembic-migration
description: Create and apply Alembic migrations for GarminCoach with all SQLite/PostgreSQL gotchas handled (render_as_batch, naive datetimes, Docker COPY, batch_alter_table). Invoke when adding or changing DB columns or tables.
disable-model-invocation: true
---

Steps for every Alembic migration in GarminCoach:

## 1. Check current state
```bash
docker compose exec backend alembic current
```

## 2. Generate migration
```bash
docker compose exec backend alembic revision --autogenerate -m "<short description>"
```

## 3. Inspect the generated file in `backend/alembic/versions/`

Validate:
- `alembic/env.py` has `render_as_batch=_sync_url.startswith("sqlite")` inside `context.configure()` in `run_migrations_online()`
- SQLite ALTER operations use `with op.batch_alter_table("table_name") as batch_op:` — NOT bare `op.alter_column()`
- New `DateTime` columns: any Python code that writes to them must use `.replace(tzinfo=None)` to strip timezone
- No `sa.Enum` without an explicit `name=` parameter (causes SQLite issues)

## 4. Apply
```bash
docker compose exec backend alembic upgrade head
```

## 5. Verify
```bash
docker compose exec backend alembic current
```
Must show `(head)`. If it shows the old revision, the migration was a silent no-op.

---

## If schema didn't change (silent SQLite no-op)

This happens when `render_as_batch` was missing. Fix:
```bash
docker compose exec backend alembic history  # get previous revision ID
docker compose exec backend alembic stamp <previous-revision-id>
docker compose exec backend alembic upgrade head
```

---

## If Neon DB has an unknown revision ("Can't locate revision")

This happens when a placeholder or stale ID was stamped into `alembic_version`. Fix:

**Step 1** — Find the real head revision in the codebase:
```bash
grep "^Revision ID" backend/alembic/versions/*.py | sort
```
Note the most recent one (highest revision ID). **Never use a made-up hex string.**

**Step 2** — Update the DB directly (use sync DATABASE_URL from `.env.prod`):
```python
import psycopg2
# Use postgresql://... (NOT postgresql+asyncpg://)
conn = psycopg2.connect("postgresql://...?sslmode=require")
cur = conn.cursor()
cur.execute("SELECT version_num FROM alembic_version;")
print("Current:", cur.fetchall())            # verify what's there
cur.execute("UPDATE alembic_version SET version_num = '<real-head-id>';")
conn.commit()
conn.close()
```

**Step 3** — Verify the fix before redeploying:
```bash
cd backend && source ../.env.prod && DATABASE_URL=$DATABASE_URL .venv/bin/alembic current
# Must show: <revision-id> (head)
```

**Never use `alembic stamp` when the DB has an unknown revision** — `stamp` itself fails if the current version is unrecognised. You must update the table directly first.

---

## Pre-release Neon check

Run this before tagging any release to catch stale stamps early:
```bash
cd backend && source ../.env.prod && DATABASE_URL=$DATABASE_URL .venv/bin/alembic current
# Must show: <revision-id> (head)
```
If it fails with "Can't locate revision", follow the recovery procedure above **before tagging**.

---

## Before committing — checklist

- [ ] `alembic/` and `alembic.ini` present in `backend/Dockerfile` COPY list
- [ ] `docker-compose.yml` command starts with `alembic upgrade head &&`
- [ ] `render_as_batch=_sync_url.startswith("sqlite")` in `alembic/env.py`
- [ ] All writes to new DateTime columns use `.replace(tzinfo=None)`
- [ ] `alembic current` shows `(head)` after apply
- [ ] Neon pre-release check passes (`(head)`) before tagging
