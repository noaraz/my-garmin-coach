# Garmin Sync — CLAUDE

## Garmin Enum Mappings

```python
STEP_TYPE = {"warmup": 1, "cooldown": 2, "interval": 3, "recovery": 4, "rest": 5, "repeat": 6}
CONDITION_TYPE = {"lap_button": 1, "time": 2, "distance": 3}
TARGET_TYPE = {"no_target": 1, "heart_rate": 4, "pace": 6}
SPORT_TYPE = {"running": 1}
```

Our step type → Garmin: "active" → "interval", all others 1:1.

## Pace ↔ Speed

```
pace_to_speed: 1000.0 / sec_per_km = m/s
speed_to_pace: 1000.0 / m_per_s = sec/km
Garmin uses m/s internally. Lower m/s = slower pace.
```

## Mock Pattern

```python
from unittest.mock import MagicMock

@pytest.fixture
def mock_garmin_client():
    client = MagicMock()
    client.login.return_value = None
    client.get_workouts.return_value = []
    client.add_workout.return_value = {"workoutId": "garmin-12345"}
    client.schedule_workout.return_value = None
    client.update_workout.return_value = None
    client.delete_workout.return_value = None
    return client
```

## Optional Dependency Pattern

Use `try/except` to make Garmin optional — returns `None` instead of raising 403:

```python
async def get_optional_garmin_sync_service(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SyncOrchestrator | None:
    try:
        return await _get_garmin_sync_service(current_user=current_user, session=session)
    except HTTPException:
        return None
```

Routers check `if garmin is not None:` before any Garmin call. Use this for all endpoints
where Garmin sync is best-effort (zone recalc, profile update, delete-on-unschedule).

## Delete-on-Unschedule

When a `ScheduledWorkout` with a `garmin_workout_id` is removed from the calendar,
also delete it from Garmin Connect. Pattern:

- Router passes `garmin_deleter=garmin.delete_workout if garmin else None` to the service
- Service calls `garmin_deleter(garmin_workout_id)` in a `try/except` (best-effort)
- Local DB deletion always succeeds regardless of Garmin outcome

## Auto-Sync After Zone Change (updated 2026-03-20 — fire-and-forget)

Zone-change endpoints use **FastAPI BackgroundTasks** so the response returns immediately:

```python
background_tasks.add_task(background_sync, current_user.id)
```

`background_sync(user_id)` in `sync.py`:
- Opens its own fresh session via `async_session_factory()` (no request-scoped session)
- Calls `_get_garmin_adapter(current_user=user, session=session)` directly — bypasses DI
- Self-exits silently if Garmin is not connected (catches `HTTPException`)
- Calls `sync_modified_workouts` which uses `asyncio.gather()` for parallel per-workout Garmin calls

`_get_zone_maps` uses `asyncio.gather()` to fetch HR + pace zones concurrently (Neon optimization).

Endpoints using `background_sync`: PUT /zones/hr, POST /zones/hr/recalculate,
POST /zones/pace/recalculate, PUT /profile (only when `lthr` or `threshold_pace` changes).

**SQLite dev note**: background task + immediate next request can contend on the SQLite writer lock.
Not an issue on Neon PostgreSQL. Gaps of ≥1s between requests avoid it locally.

**`_get_garmin_adapter` is DI-bypassable** — it's a plain async function; call directly with
`current_user=user, session=session` from background tasks or scripts outside FastAPI context.

## Akamai / curl_cffi (updated 2026-03-25)

Garmin uses Akamai Bot Manager with **different configs per subdomain**:

| Subdomain | curl_cffi (chrome TLS) | Standard Python TLS |
|-----------|----------------------|---------------------|
| `sso.garmin.com` (SSO login) | ✅ Allowed | ❌ Blocked |
| `connectapi.garmin.com` (API calls) | ✅ Allowed | ❌ Blocked |
| `connectapi.garmin.com` (OAuth exchange) | ❌ **Blocked** | ✅ Allowed |

**Fix**: `ChromeTLSSession(impersonate="chrome124")` in `backend/src/garmin/client_factory.py` — single source of truth for all Garmin client creation. `CHROME_VERSION` constant controls the version.

**Factory functions** (version-aware, single branching point):
- `login_and_get_token(email, password, auth_version=)` → token JSON — V1 uses garth, V2 uses garminconnect native
- `create_adapter(token_json, auth_version=)` → `GarminAdapterProtocol` — returns V1 or V2 adapter
- `create_login_client()` → `garth.Client` — V1-only, used by garmin_connect.py retry loop
- `create_api_client(token_json)` — backward-compat alias for `create_adapter()`

**Token exchange — DO NOT override `refresh_oauth2`**: garth's native `sso.exchange()` creates a `GarminOAuth1Session(parent=ChromeTLSSession)` which uses standard Python TLS. Akamai allows this on the exchange endpoint but blocks curl_cffi. Monkey-patching `refresh_oauth2` to route through curl_cffi causes 429.

**Retry flow** (login only): attempt 1 = chrome124 no proxy; attempt 2 (on 429) = chrome124 + Fixie proxy.

**Fingerprint rotation + timing delay (added 2026-04-10)**: `FINGERPRINT_SEQUENCE` in
`client_factory.py` tries `chrome136 → safari15_5 → edge101 → chrome120 → chrome99`.
Attempt 2+ waits `random.uniform(30, 45)` s before calling `client.login()` — a
preventative delay borrowed from
[garmin-health-data](https://github.com/diegoscarabelli/garmin-health-data) that mimics
human form-fill time and avoids Akamai's rapid-submission detection. Proxy (Fixie)
applied only on the last attempt. `auto_reconnect.py` uses only the default fingerprint
(best-effort, no rotation — acceptable since auto-reconnect failure falls back to manual
reconnect).

- `curl_cffi.requests.Session` lacks `adapters` and `hooks` that garth needs — subclass pre-populates both. Never replace `client.sess` with a bare curl_cffi session.
- `FIXIE_URL` wired as optional fallback — only consumed on last-attempt retry, saves proxy quota.
- **Re-diagnose with `test_garmin_login.py`** (repo root) if 429s return — Akamai periodically updates fingerprint detection.
- **`FINGERPRINT_SEQUENCE` bumps**: When changing fingerprints in `client_factory.py`, grep all docs for stale references: `grep -r "chrome1[0-9][0-9]\|safari15\|edge101" features/ .claude/skills/ CLAUDE.md`. Update every stale reference.

## Bidirectional Sync

`POST /sync/all` now does both push and fetch:
1. Push pending/modified workouts TO Garmin (existing)
2. Fetch activities FROM Garmin (new — see `features/garmin-activity-fetch/`)

The adapter (V1: `adapter_v1.py`, V2: `adapter_v2.py`) is shared between push and fetch.
Both implement `GarminAdapterProtocol` with `add_workout`, `schedule_workout`,
`update_workout`, `delete_workout` (push), `get_activities_by_date` (fetch), and
`get_workouts` (dedup). `adapter.py` is a backward-compat shim re-exporting from V1.

Activity fetch is best-effort — if it fails, the push results are still returned.
Response includes `activities_fetched`, `activities_matched`, `fetch_error` fields.

## Garmin Workout Dedup (added 2026-03-25)

**Problem**: Workouts can be duplicated on Garmin when:
1. `_sync_and_persist` fails to delete an old Garmin workout but clears `garmin_workout_id` anyway — orphaning the old one
2. `commit_plan` re-creates SWs (losing `garmin_workout_id`) and Garmin cleanup fails or `garmin` is `None`

**Fix — three layers:**

### Layer 1: Orphan prevention (`_sync_and_persist`)
If delete fails, skip the push and mark `sync_status="failed"`. The `garmin_workout_id` is preserved so the next sync can retry. This prevents creating a new Garmin workout when the old one couldn't be removed. **Exception**: 404 means the Garmin workout is already gone — clears the stale ID and proceeds with push (avoids infinite retry loop on stale IDs).

### Layer 2: Name-based dedup (`garmin/dedup.py`)
Pure functions for matching local workouts against Garmin by name (case-insensitive):
- `find_matching_garmin_workout(name, garmin_workouts)` → garmin_workout_id or None
- `find_orphaned_garmin_workouts(garmin_workouts, known_ids, template_names)` → list of orphan IDs safe to delete

### Layer 3: Dedup wiring
- **`sync_all`**: Fetches `sync_service.get_workouts()` once, passes to `_sync_and_persist`. Before pushing a workout with no `garmin_workout_id`, checks for name match. If found, deletes the match first, then pushes. Also runs orphan cleanup sweep at the end.
- **`commit_plan`**: When creating new SWs, checks `garmin_workout_by_name` index (via `garmin.get_workouts()`). If a match is found, pre-links `garmin_workout_id` and sets `sync_status="modified"` (so next sync does delete+push with correct ID).

### Safety: user-created Garmin workouts
Orphan cleanup only deletes Garmin workouts whose name matches a `WorkoutTemplate.name` in our DB. User-created Garmin workouts (different names) are never deleted.

## SyncOrchestrator Layering

All Garmin API calls from routers/services must go through `SyncOrchestrator` methods, not `sync_service.adapter.*`. When adding a new Garmin API method, add it to all three layers: `GarminAdapter` → `GarminSyncService` → `SyncOrchestrator`.

## Unified Exception Handling (updated 2026-04-14)

Adapters (V1 and V2) translate library-specific exceptions into unified types in `adapter_protocol.py`:
- `GarminNotFoundError` (404) — stale workout, already deleted
- `GarminRateLimitError` (429) — exchange or API rate limit
- `GarminAuthError` (401) — bad credentials or expired token
- `GarminConnectionError` — network/other errors

Consumers (sync.py, auto_reconnect.py) catch these types — never `GarthHTTPError` or library-specific errors.

**Test factory:**
```python
from src.garmin.adapter_protocol import GarminNotFoundError
def _garmin_404() -> GarminNotFoundError:
    return GarminNotFoundError("404 Not Found")
```

## Stale `garmin_workout_id` Recovery

When a workout has a `garmin_workout_id` that no longer exists on Garmin (e.g. manually deleted from Garmin Connect), `_sync_and_persist` will receive a `GarminNotFoundError` on the delete attempt, clears the stale ID, and proceeds with a fresh push — self-healing on retry with no manual intervention needed.

**If a workout is stuck as `sync_status="failed"` with a stale ID and self-heal isn't working** (e.g. `_is_garmin_404` not detecting the error variant), clear it manually:

```bash
docker compose exec backend python3 -c "
import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from src.db.models import ScheduledWorkout
from src.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url)

async def fix(workout_id: int):
    async with AsyncSession(engine) as session:
        sw = await session.get(ScheduledWorkout, workout_id)
        sw.garmin_workout_id = None
        sw.sync_status = 'modified'
        session.add(sw)
        await session.commit()
        print(f'Fixed workout {workout_id}')

asyncio.run(fix(252))  # replace 252 with actual ID
"
```

Then retry `POST /api/v1/sync/{id}`.

## Sync-From-Panel

`POST /api/v1/sync/{id}` (`sync_single`) re-syncs a single workout and returns `SyncStatusItem`:
`{ id, date, sync_status, garmin_workout_id }`.

In the frontend, `useCalendar` exposes `syncOneWorkout(id)` which calls `syncOne(id)` and refetches
the calendar range to update the workouts array. `WorkoutDetailPanel` receives `onSync?: (id) => Promise<void>`.
The button always renders — no `garminConnected` guard. If Garmin is not connected the API returns an error
which the panel silently swallows (button re-enables via `finally`).

## Unsynced Workouts Script

`backend/scripts/unsynced_workouts.py` lists all non-completed workouts with `sync_status != 'synced'`.
Run against production:

```bash
DATABASE_URL="postgresql+asyncpg://user:pass@host/db?ssl=require" \
  PYTHONPATH=backend .venv/bin/python backend/scripts/unsynced_workouts.py --future-only
```

Or inside Docker: `docker compose exec backend python scripts/unsynced_workouts.py --future-only`.

## Dedup 404 Path — Fall-Through to Push

When the dedup block in `_sync_and_persist` tries to delete a name-matched Garmin workout
and gets a 404, the intent is "already gone — proceed with push". The `session.add` and
`return None` that abort the function must be **inside the `else` branch only**:

```python
except Exception as exc:
    if _is_garmin_404(exc):
        workout.garmin_workout_id = None  # clear stale ID, fall through to push
    else:
        workout.sync_status = "failed"
        session.add(workout)
        return None           # ← only on real errors, never on 404
```

If `return None` sits outside the `if/else` at the `except` level, it runs on the 404 path
and silently aborts the push — the workout is never synced and stays unsynced forever.

## Auto-Reconnect (added 2026-03-29)

When the OAuth2 exchange endpoint returns 429 and blocks all syncs, the auto-reconnect system re-logins using stored encrypted credentials to obtain fresh tokens.

**Design spec**: `docs/superpowers/specs/2026-03-28-garmin-auto-reconnect-design.md`

### Exchange Storm Prevention (3 layers)

1. **Early-exit**: `_is_exchange_429(exc)` detects exchange 429. On first detection in `sync_all`, return immediately — don't continue to activity fetch, paired cleanup, orphan cleanup.
2. **Module-level cooldown**: After a 429, skip sync for 30 min. Prevents repeated exchange attempts.
3. **Client cache**: `backend/src/garmin/client_cache.py` — caches `GarminAdapter` per `user_id` in process memory. Avoids loading expired token from DB when in-memory adapter has a valid token.

### Auto-Reconnect Flow

```
Exchange 429 detected
  → attempt_auto_reconnect(user_id, session)
  → Check garmin_credential_encrypted exists + not expired (30 days)
  → Per-user reconnect cooldown (15 min network errors, 1 hour auth failures)
  → Decrypt credentials → create_login_client().login(email, password)
  → On success: encrypt & persist fresh tokens, invalidate caches, return fresh adapter
  → On GarthHTTPError: clear credentials immediately (bad password never retries)
  → On other error: keep credentials, set cooldown, return None
```

### Credential Encryption

- Separate key: `GARMIN_CREDENTIAL_KEY` env var (not `GARMINCOACH_SECRET_KEY`)
- Algorithm: Fernet + HKDF-SHA256 with `salt=user_id`, domain `b"garmincoach-credential-v1"`
- 30-day auto-expiry: credentials cleared on read if `garmin_credential_stored_at` > 30 days ago
- Stored on `POST /api/v1/garmin/connect`, cleared on disconnect
- **NEVER log `exc` objects from garth** — `PreparedRequest` in the traceback contains plaintext credentials in form body. Log `type(exc).__name__` only.

### Token Persistence Helper

`backend/src/garmin/token_persistence.py` — extracted `persist_refreshed_token()`. Called after every successful sync in `sync_all`, `sync_single`, `background_sync`, `pair_activity`, `delete_schedule`, `commit_plan`, `delete_plan`.

**Important**: Token persistence is only useful when exchange SUCCEEDS. When exchange FAILS (429), garth still has the OLD expired token — persisting it saves stale data. Auto-reconnect is the fix for the failed-exchange case.

## Garth Deprecation + garminconnect 0.3.x Migration (updated 2026-04-14)

### Background (March 2026)

- March 17: Garmin deployed Cloudflare protection blocking `/mobile/api/login` globally
- March 27: garth maintainer (matin) officially deprecated garth
- April 2: python-garminconnect 0.3.0 released — replaces garth with native DI OAuth

### Migration: Feature-Flagged Dual Adapter

Design spec: `docs/superpowers/specs/2026-04-14-garminconnect-03x-migration-design.md`

- **Runtime feature flag**: `SystemConfig` table + `POST /api/v1/admin/garmin-auth-version` (v1 or v2)
- **GarminAdapterProtocol**: Shared interface in `adapter_protocol.py`
- **GarminAdapterV1** (`adapter_v1.py`): Current garth-based code, exception wrapping added
- **GarminAdapterV2** (`adapter_v2.py`): garminconnect 0.3.x native — `client.connectapi()` replaces `client.garth.post/put/delete()`
- **Unified exceptions**: `GarminAdapterError` hierarchy in `adapter_protocol.py`. Consumers catch these, not `GarthHTTPError`.
- **WorkoutFacade** (`workout_facade.py`): Version-aware formatter bridge injected into SyncOrchestrator
- **Token format**: V1 (garth.dumps) and V2 (json.dumps of garmin_tokens) are incompatible. `garmin_auth_version` column on AthleteProfile tracks format.
- **Version mismatch → disconnect**: When `profile.garmin_auth_version` ≠ global `SystemConfig` flag, `_get_garmin_adapter` disconnects the user (clears token, sets `garmin_connected=False`) and returns 403 "Please reconnect in Settings." Auto-reconnect handles migration for users with stored credentials.
- **Global flag = new logins only**: `SystemConfig.garmin_auth_version` controls `login_and_get_token` and `WorkoutFacade`. Stored token deserialization uses `profile.garmin_auth_version`.
- **Rollback**: Switch flag to v1 via admin endpoint — instant, no restart needed. Existing V2 users will be disconnected and need to reconnect.

### V1 path (garth 0.5.21) — retained as fallback

- Uses old SSO form flow (`/sso/embed` + `/sso/signin`)
- `ChromeTLSSession` + fingerprint rotation for Akamai bypass
- **DO NOT upgrade garth** past 0.5.x
- Will be removed in a follow-up PR after V2 is stable

## Reconnect Prompt for Existing Users (added 2026-03-29)

Existing users who connected to Garmin before the auto-reconnect feature was deployed have `garmin_credential_encrypted = NULL` — auto-reconnect won't work for them until they disconnect and reconnect.

**Detection**: `GarminStatusResponse` includes `credentials_stored: bool` (true when `garmin_credential_encrypted IS NOT NULL`). Frontend uses `connected=true && credentials_stored=false` to identify users who need to reconnect.

**CalendarPage banner**: One-time-per-session prompt (dismissable via `sessionStorage('reconnect_prompt_dismissed')`). Shows "Go to Settings" button and dismiss X. Not shown after dismiss until next browser session.

**SettingsPage card**: Persistent warning card in the connected state when `credentialsStored=false`. Shows "Disconnect & Reconnect" button. Disappears after user reconnects (connect sets `credentials_stored=true`).

**GarminStatusContext**: Extended with `credentialsStored: boolean | null` alongside `garminConnected`.

## Sync-All Reconciliation — Calendar-Based (updated 2026-04-01)

**Problem**: Workouts marked `sync_status="synced"` are never re-checked. If a Garmin workout is externally deleted or unscheduled (e.g. Garmin Connect UI, app glitch, API failure), Sync All has no effect — the workout is stuck as "synced" forever.

**Fix**: Calendar-based reconciliation using `GET /calendar-service/year/{year}/month/{month}`, which returns `calendarItems` with `{workoutId, date, title}`. Compares `(workoutId, date)` pairs from DB vs Garmin calendar.

**Two reconciliation paths**:
1. **Template exists on Garmin but not scheduled on correct date** → `reschedule_workout()` (cheap API call, no full re-push needed)
2. **Template also gone from Garmin** → mark as `sync_status="modified"` for full re-push by the existing push loop

**Implementation**:
- Pure function: `find_unscheduled_workouts()` in `dedup.py` — compares DB `(garmin_workout_id, date)` pairs against calendar items
- `find_missing_from_garmin()` was removed (superseded by calendar-based approach)
- Placement: between `garmin_workouts` fetch and `get_by_status` push loop in `sync_all`
- Guard: only runs when calendar fetch succeeds (skip on API failure)
- Completed workouts excluded — they don't need re-push (already paired with activity)
- `rescheduled: int` field added to `SyncAllResponse`
- Log: `"Reconciliation: %d workouts rescheduled, %d re-queued for user %s"`

**Calendar endpoint**: `/calendar-service/year/{year}/month/{month}` works reliably. **Garmin uses 0-indexed months** (Jan=0, Dec=11) — the adapter converts from Python's 1-indexed `date.month` internally. The old `/workout-service/schedule/{id}` GET always returns 404 — do not use for reads.

**Duplicate calendar cleanup**: `sync_all` detects duplicate `(workoutId, date)` pairs on the Garmin calendar (caused by double-scheduling) and removes extras via `DELETE /workout-service/schedule/{schedule_id}`. Each calendar item has a unique `id` (the schedule entry ID). Pure function: `find_duplicate_calendar_entries()` in `dedup.py`. Runs before the unscheduled check.

**`unschedule_workout(schedule_id)`**: Propagated through all 3 layers (adapter → sync_service → orchestrator). Calls `DELETE /workout-service/schedule/{id}` to remove a single calendar entry without deleting the workout template.

## Gotchas

- **New facade methods need explicit integration test mocks**: When adding a method to the 3-layer facade (adapter → sync_service → orchestrator), `MagicMock` auto-creates it as a new `MagicMock` (truthy, iterable as empty). Tests that don't explicitly mock the new method silently pass with wrong behavior. Grep for `mock_sync_service` and add `.return_value` for every test that exercises `sync_all`.
- **OAuth2 token refresh not persisted → 429 storm**: garth's `refresh_oauth2()` stores the new
  OAuth2 token in memory only (`_garth_home` unset). Without persisting it, every sync loads the
  same expired token from DB and triggers a new exchange at
  `connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0`. Frequent syncs exhaust Garmin's
  exchange rate limit → repeated 429s. **Fix**: `_persist_refreshed_token(adapter, user_id,
  session)` in `sync.py` — called at the end of `sync_all` and `sync_single`. Uses
  `adapter.dump_token()` (= `garth.dumps()`), re-encrypts, saves back to
  `AthleteProfile.garmin_oauth_token_encrypted`. **Note**: this only helps when exchange succeeds.
  When exchange FAILS (429), auto-reconnect is needed — see above.
- `GarminAdapter.dump_token() -> str` — returns `garth.dumps()` JSON. Use after any sync to
  capture the in-memory (potentially refreshed) token state for DB persistence.
- **Calendar read-back via calendar-service**: `GET /calendar-service/year/{year}/month/{month}` returns
  `calendarItems` with `{workoutId, date, title}` — used for reconciliation. The old
  `GET /workout-service/schedule/{id}` always returns 404 — do not use that endpoint.
- **Pace format**: Garmin uses m/s, not sec/km. Always convert.
- **Repeat nesting**: One level only. No repeats inside repeats.
- **50-step limit**: Max ~50 steps including expanded repeats. Validate.
- **garmin-workouts-mcp**: Reference for JSON format only, NOT a dependency.
