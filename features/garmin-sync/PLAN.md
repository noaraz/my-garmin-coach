# Garmin Sync — PLAN

## Description

Two parts: (1) a pure formatter that converts resolved workout steps into
Garmin Connect's JSON format, and (2) a sync service that pushes/updates/deletes
workouts on Garmin Connect via python-garminconnect.

The formatter is pure logic (no I/O). The sync service is an I/O boundary —
always mocked in CI tests, with an optional live test gated behind env var.

Track progress in **STATUS.md**.

---

## Tasks

### Formatter (pure logic)
- [ ] Write `garmin/constants.py` — all Garmin enum mappings
- [ ] Write all tests in `test_garmin_converters.py` (see test table)
- [ ] Run tests → RED
- [ ] Implement `garmin/converters.py` — pace↔speed conversion
- [ ] Run tests → GREEN
- [ ] Write all tests in `test_garmin_formatter.py` (see test table)
- [ ] Run tests → RED
- [ ] Implement `garmin/formatter.py` — step + workout formatting
- [ ] Run tests → GREEN

### Sync Service (mocked I/O)
- [x] Write `tests/fixtures/garmin_mocks.py` — mock client factory
- [x] Write all tests in `test_garmin_sync.py` (see test table)
- [x] Run tests → RED
- [x] Implement `garmin/sync_service.py` — push, update, delete, schedule
- [x] Implement `garmin/session.py` — login, token caching, refresh
- [x] Run tests → GREEN
- [x] Implement `services/sync_orchestrator.py` — resolve → format → push pipeline
- [x] Write `test_api_sync.py` — API endpoint tests
- [x] Run tests → GREEN

---

## Garmin Workout JSON Format

```json
{
  "workoutName": "Easy 10K",
  "sportType": { "sportTypeId": 1, "sportTypeKey": "running" },
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": { "sportTypeId": 1, "sportTypeKey": "running" },
    "workoutSteps": [
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 1,
        "stepType": { "stepTypeId": 1, "stepTypeKey": "warmup" },
        "endCondition": { "conditionTypeId": 2, "conditionTypeKey": "time" },
        "endConditionValue": 600,
        "targetType": { "workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone" },
        "targetValueOne": 130,
        "targetValueTwo": 145
      }
    ]
  }]
}
```

---

## Tests

### test_garmin_converters.py

| Test | Given | Expect |
|------|-------|--------|
| `test_pace_to_speed` | 300 s/km | 3.333 m/s |
| `test_speed_to_pace` | 3.333 m/s | ~300 s/km |
| `test_roundtrip` | any pace | within 1s tolerance |
| `test_step_type_to_id` | "warmup" | 1 |
| `test_unknown_type_raises` | "invalid" | FormatterError |

### test_garmin_formatter.py

| Test | Given | Expect |
|------|-------|--------|
| `test_warmup_time_open` | warmup, 600s, open | correct JSON |
| `test_interval_time_hr` | active, 300s, HR 155-170 | correct targets |
| `test_interval_distance_pace` | active, 1000m, pace | speed conversion |
| `test_cooldown_lap_button` | cooldown, lap_button | correct |
| `test_repeat_group` | repeat(4) with children | RepeatGroupDTO |
| `test_full_workout` | name + steps | complete structure |
| `test_preserves_step_order` | 5 steps | stepOrder 1-5 |
| `test_empty_raises` | no steps | FormatterError |

### test_garmin_sync.py (all mocked)

| Test | Given | Expect |
|------|-------|--------|
| `test_login_success` | mock login | session established |
| `test_login_failure` | mock auth error | GarminAuthError |
| `test_push_new` | mock create | garmin_workout_id returned |
| `test_schedule_on_date` | mock schedule | placed on date |
| `test_update_existing` | mock update | updated |
| `test_delete` | mock delete | deleted |
| `test_bulk_resync` | 5 future workouts | all 5 updated |
| `test_rate_limiting` | mock 429 | retry with backoff |
| `test_marks_synced` | after push | sync_status="synced" |
| `test_marks_failed` | after error | sync_status="failed" |
| `test_skips_completed` | completed=True | no sync attempt |

---

## Dependency Trust

| Library | Stars | Notes |
|---------|-------|-------|
| python-garminconnect | ~1.8K | 105+ endpoints, monthly releases, powers Home Assistant |
| garth | ~757 | OAuth layer, tokens last ~1 year |

All Garmin calls isolated in `src/garmin/` — swappable if lib breaks.

### Fixie Proxy (production)
- [x] Add `fixie_url` to Settings (`FIXIE_URL` env var, empty = disabled)
- [x] Configure proxy on `garth.Client.sess.proxies` before login
- [x] Add `FIXIE_URL` to `docker-compose.prod.yml`
- Garmin rate-limits OAuth from Render's shared datacenter IPs (429). Fixie free tier (500 req/mo) provides a dedicated static IP for the login call only.

---

## Implementation Files

```
backend/src/garmin/
  __init__.py, formatter.py, converters.py, constants.py
  sync_service.py, session.py, exceptions.py

backend/src/services/
  sync_orchestrator.py

backend/tests/fixtures/
  garmin_mocks.py
```
