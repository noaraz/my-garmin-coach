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

**Factory functions** (both inject `ChromeTLSSession`):
- `create_login_client(proxy_url=None)` → `garth.Client` — SSO login in `garmin_connect.py`
- `create_api_client(token_json)` → `GarminAdapter` — all API calls in `sync.py` via `_get_garmin_adapter()`

**Token exchange — DO NOT override `refresh_oauth2`**: garth's native `sso.exchange()` creates a `GarminOAuth1Session(parent=ChromeTLSSession)` which uses standard Python TLS. Akamai allows this on the exchange endpoint but blocks curl_cffi. Monkey-patching `refresh_oauth2` to route through curl_cffi causes 429.

**Retry flow** (login only): attempt 1 = chrome124 no proxy; attempt 2 (on 429) = chrome124 + Fixie proxy.

- `curl_cffi.requests.Session` lacks `adapters` and `hooks` that garth needs — subclass pre-populates both. Never replace `client.sess` with a bare curl_cffi session.
- `FIXIE_URL` wired as optional fallback — only consumed on 429 retry, saves proxy quota.
- **Re-diagnose with `test_garmin_login.py`** (repo root) if 429s return — Akamai periodically updates fingerprint detection.

## Bidirectional Sync

`POST /sync/all` now does both push and fetch:
1. Push pending/modified workouts TO Garmin (existing)
2. Fetch activities FROM Garmin (new — see `features/garmin-activity-fetch/`)

The `GarminAdapter` in `backend/src/garmin/adapter.py` is shared between push and fetch.
It provides `add_workout`, `schedule_workout`, `update_workout`, `delete_workout` (push),
`get_activities_by_date` (fetch), and `get_workouts` (dedup).

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

## Gotchas

- **Pace format**: Garmin uses m/s, not sec/km. Always convert.
- **Repeat nesting**: One level only. No repeats inside repeats.
- **50-step limit**: Max ~50 steps including expanded repeats. Validate.
- **Session expiry**: tokens expire. Implement refresh/re-login.
- **garmin-workouts-mcp**: Reference for JSON format only, NOT a dependency.
