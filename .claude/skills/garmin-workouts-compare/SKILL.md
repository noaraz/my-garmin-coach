---
name: garmin-workouts-compare
description: >
  Use when workouts show in the app but not on Garmin, Sync All has no effect
  but force-sync works, or for morning sync debugging. Also trigger when user
  says "workouts aren't on Garmin", "sync not working", or "missing from watch".
---

# Garmin Workouts Compare

Diagnostic script comparing Garmin Connect workouts against our DB.

## Run

```bash
# Docker — local DB (default)
docker compose exec backend python scripts/compare_garmin_workouts.py

# Docker — production DB (source .env.prod first)
source .env.prod && PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" \
  docker compose exec \
  -e DATABASE_URL="$DATABASE_URL" \
  -e GARMINCOACH_SECRET_KEY="$GARMINCOACH_SECRET_KEY" \
  -e GARMIN_CREDENTIAL_KEY="${GARMIN_CREDENTIAL_KEY:-}" \
  backend python scripts/compare_garmin_workouts.py --user-id 3 --future-only

# Local venv
cd backend && .venv/bin/python scripts/compare_garmin_workouts.py

# Options: --user-id N (default 1), --future-only
```

### Production DB prerequisites

- `.env.prod` must have current values from Render dashboard (it's gitignored)
- Script calls `get_settings.cache_clear()` so container-cached settings don't override env vars
- Script converts `ssl=require` → `sslmode=require` for psycopg2 sync driver (Neon URLs use asyncpg's `ssl=` param)
- If token decryption fails (`InvalidToken`), the `GARMINCOACH_SECRET_KEY` in `.env.prod` is stale — update from Render dashboard

## Reading Output

| Where | Meaning | Action |
|-------|---------|--------|
| **BOTH ✓** | In DB and on Garmin | None |
| **ONLY DB ✗** | DB says "synced" but gone from Garmin | **The bug** — needs re-push |
| **ONLY DB (pending/…)** | Not yet synced | Expected — run Sync All |
| **ONLY GARMIN** | On Garmin, not tracked in DB | Orphan — cleaned by sweep |

### Calendar Column (CAL)

The script also shows a `CAL` column indicating whether the workout is scheduled on the Garmin calendar:

| Value | Meaning |
|-------|---------|
| **CAL ✓** | Workout is scheduled on the Garmin calendar (appears in `/calendar-service/year/{year}/month/{month}` response) |
| **CAL ✗** | Workout template exists on Garmin but is NOT scheduled on the calendar — reconciliation will reschedule it |

This column helps diagnose cases where a workout template exists on Garmin (`BOTH ✓`) but is missing from the Garmin calendar — the user won't see it on their watch until it's rescheduled.

## If You See ONLY DB ✗

Root cause: `sync_all` only queries `sync_status in ("pending", "modified", "failed")`. Once "synced", never re-checked. Fix: reconciliation in `sync_all` via `find_missing_from_garmin()` in `dedup.py`.

**Manual fix** — force-sync each workout via UI, or:
```sql
UPDATE scheduled_workout SET sync_status = 'modified', garmin_workout_id = NULL
WHERE id IN (...);
```
