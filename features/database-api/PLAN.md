# Database + API — PLAN

## Description

Persistence layer (SQLModel + SQLite) and REST API (FastAPI). Orchestrates
zone engine, workout resolver, and Garmin sync into a working backend.

The critical business logic here is the **zone cascade**: when a threshold
changes, zones recalculate, all future workouts re-resolve, and sync status
updates — all in one transaction.

Track progress in **STATUS.md**.

---

## Tasks

### Database
- [x] Write `db/models.py` — all SQLModel table classes (see data model below)
- [x] Write `db/database.py` — engine creation, `get_session()` dependency
- [x] Write `tests/integration/conftest.py` — test DB, test client, fixtures
- [x] Write all tests in `test_db.py` (see test table)
- [x] Run tests → RED
- [x] Implement DB operations in service layer
- [x] Run tests → GREEN

### API Endpoints
- [x] Write all tests in `test_api_profile.py`
- [x] Write all tests in `test_api_zones.py`
- [x] Write all tests in `test_api_workouts.py`
- [x] Write all tests in `test_api_calendar.py`
- [x] Write all tests in `test_api_sync.py`
- [x] Run all tests → RED
- [x] Implement `api/routers/` — profile, zones, workouts, calendar, sync
- [x] Implement `services/` — profile, zone, workout, calendar services
- [x] Run all tests → GREEN

### Zone Cascade
- [x] Implement zone change → re-resolve → mark modified flow in zone_service
- [x] Write specific test: change LTHR → verify future workouts re-resolved
- [x] Run test → GREEN

---

## Data Model

### AthleteProfile
```
id, name, max_hr, resting_hr, lthr, threshold_pace, created_at, updated_at
```

### HRZone
```
id, profile_id→AthleteProfile, zone_number(1-5), name,
lower_bpm, upper_bpm, calculation_method, pct_lower, pct_upper
```

### PaceZone
```
id, profile_id→AthleteProfile, zone_number(1-5), name,
lower_pace, upper_pace, calculation_method, pct_lower, pct_upper
```

### WorkoutTemplate
```
id, name, description, sport_type, estimated_duration_sec,
estimated_distance_m, tags(JSON), steps(JSON), created_at, updated_at
```

### ScheduledWorkout
```
id, date, workout_template_id→WorkoutTemplate, resolved_steps(JSON),
garmin_workout_id, sync_status, completed, notes, created_at, updated_at
```

---

## Tests

### test_db.py

| Test | Scenario |
|------|----------|
| `test_create_athlete_profile` | insert, verify fields |
| `test_update_athlete_lthr` | update, verify updated_at |
| `test_create_hr_zones` | 5 zones linked to profile |
| `test_create_pace_zones` | 5 zones linked to profile |
| `test_cascade_delete` | delete profile → zones deleted |
| `test_create_workout_template` | insert with JSON steps |
| `test_schedule_workout` | link template to date |
| `test_get_by_date_range` | filter start/end |
| `test_update_sync_status` | pending → synced |

### test_api_profile.py

| Test | Scenario |
|------|----------|
| `test_get_profile` | GET /api/profile → 200 |
| `test_update_profile` | PUT /api/profile → 200 |
| `test_update_lthr_triggers_recalc` | PUT with new LTHR → zones recalculated |

### test_api_zones.py

| Test | Scenario |
|------|----------|
| `test_get_hr_zones` | GET → 5 zones |
| `test_set_hr_zones_custom` | PUT with boundaries |
| `test_recalculate_hr_zones` | POST recalculate |
| `test_get_pace_zones` | GET → 5 zones |
| `test_recalculate_pace_zones` | POST recalculate |
| `test_zone_change_re_resolves` | zones change → workouts updated |

### test_api_workouts.py

| Test | Scenario |
|------|----------|
| `test_create` | POST → 201 |
| `test_list` | GET → list |
| `test_update` | PUT → 200 |
| `test_delete` | DELETE → 204 |

### test_api_calendar.py

| Test | Scenario |
|------|----------|
| `test_schedule` | POST → 201 |
| `test_get_range` | GET ?start=&end= → list |
| `test_reschedule` | PATCH → new date |
| `test_unschedule` | DELETE → 204 |
| `test_schedule_resolves_steps` | resolved_steps populated |

### test_api_sync.py

| Test | Scenario |
|------|----------|
| `test_sync_single` | POST /api/sync/:id |
| `test_sync_all_pending` | POST /api/sync/all |
| `test_sync_status` | GET /api/sync/status |

---

## Implementation Files

```
backend/src/
  db/ — models.py, database.py, migrations.py
  api/ — app.py, dependencies.py, routers/*
  services/ — profile, zone, workout, calendar, sync_orchestrator
```
