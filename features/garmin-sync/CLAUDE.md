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

## Akamai / curl_cffi (updated 2026-03-24)

Garmin SSO uses Akamai Bot Manager — blocks datacenter IPs AND Python `requests` TLS fingerprint.
**Fix**: `_ChromeTLSSession(impersonate="chrome120")` in `garmin_connect.py`. No proxy needed — chrome120 bypasses Akamai alone. chrome110 does not.

**Retry flow**: attempt 1 = chrome120 no proxy; attempt 2 (on 429) = chrome120 + Fixie proxy.

- `curl_cffi.requests.Session` lacks `adapters` and `hooks` that garth needs — subclass pre-populates both. Never replace `client.sess` with a bare curl_cffi session.
- `FIXIE_URL` wired as optional fallback — only consumed on 429 retry, saves proxy quota.
- Only login is affected — sync uses stored OAuth tokens, never touches SSO.
- **Re-diagnose with `test_garmin_login.py`** (repo root) if 429s return — Akamai periodically updates fingerprint detection.

## Bidirectional Sync

`POST /sync/all` now does both push and fetch:
1. Push pending/modified workouts TO Garmin (existing)
2. Fetch activities FROM Garmin (new — see `features/garmin-activity-fetch/`)

The `GarminAdapter` in `backend/src/garmin/adapter.py` is shared between push and fetch.
It provides `add_workout`, `schedule_workout`, `update_workout`, `delete_workout` (push)
and `get_activities_by_date` (fetch).

Activity fetch is best-effort — if it fails, the push results are still returned.
Response includes `activities_fetched`, `activities_matched`, `fetch_error` fields.

## Gotchas

- **Pace format**: Garmin uses m/s, not sec/km. Always convert.
- **Repeat nesting**: One level only. No repeats inside repeats.
- **50-step limit**: Max ~50 steps including expanded repeats. Validate.
- **Session expiry**: tokens expire. Implement refresh/re-login.
- **garmin-workouts-mcp**: Reference for JSON format only, NOT a dependency.
