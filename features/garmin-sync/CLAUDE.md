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

## Auto-Sync After Zone Change

`sync_modified_workouts(session, sync_service, current_user)` in `sync.py`:
- Fetches all workouts with `sync_status in ("modified", "failed")`
- Re-pushes them with fresh zone maps
- Wrapped in `try/except` — never blocks the primary response
- Called after: PUT /zones/hr, POST /zones/hr/recalculate, POST /zones/pace/recalculate,
  and PUT /profile when `lthr` or `threshold_pace` is in the submitted fields

## Fixie Proxy for Garmin OAuth (production only)

Garmin rate-limits OAuth from datacenter IPs (429). In production, `garth.Client.login()` routes
through a Fixie static IP proxy:

```python
client = garth.Client()
if settings.fixie_url:
    client.sess.proxies = {"https": settings.fixie_url}
client.login(email, password)
```

- `FIXIE_URL` env var: set in Render, empty in dev (no proxy)
- Only affects login — sync uses stored tokens (no proxy needed)
- TLS end-to-end: credentials are encrypted in transit, Fixie only sees hostnames

## Gotchas

- **Pace format**: Garmin uses m/s, not sec/km. Always convert.
- **Repeat nesting**: One level only. No repeats inside repeats.
- **50-step limit**: Max ~50 steps including expanded repeats. Validate.
- **Session expiry**: tokens expire. Implement refresh/re-login.
- **garmin-workouts-mcp**: Reference for JSON format only, NOT a dependency.
