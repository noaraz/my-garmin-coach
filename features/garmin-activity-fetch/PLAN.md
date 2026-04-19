# Garmin Activity Fetch — Feature Plan

## Overview
Fetch running activity data from Garmin Connect, auto-match to scheduled workouts,
and display TrainingPeaks-style compliance colors on the calendar.

## Design Spec
See `docs/superpowers/specs/2026-03-19-garmin-activity-fetch-design.md`

## Implementation Plan
See `docs/superpowers/plans/2026-03-19-garmin-activity-fetch.md`

## Test Coverage (added 2026-03-24)

Integration tests in `backend/tests/integration/`:
- `test_activity_fetch_service_integration.py` — 7 direct tests for `fetch_and_store` and `match_activities` using in-memory SQLite (fetch/store counts, dedup, non-running skip, date matching, already-paired skip, longest-duration selection)
- `test_api_sync.py` — 8 tests via HTTP: fetch counts, match counts, fetch error passthrough, dedup semantics, `activities_fetched` = total fetched from Garmin (not stored count)
- `test_api_calendar.py` — 8 tests: pair clears garmin_workout_id, pair without Garmin connection, already-paired 409, activity-taken-by-another 409, unpair when not paired 400, unpair preserves completed, unplanned_activities in GET /calendar, paired excluded from unplanned

## Activity Refresh (added 2026-04-18)

**What was built**: Per-activity "Refresh from Garmin" button for GPS drift recovery.

**Tests**:
- `backend/tests/unit/test_adapter_get_activity.py` — 8 unit tests: V1/V2 protocol contract, 404→`GarminNotFoundError`, 429→`GarminRateLimitError`, success dict
- `backend/tests/unit/test_activity_fetch_service.py::TestFetchAndStoreUpsert` — 3 unit tests: upsert updates fields, insert still works, date field never mutated
- `backend/tests/integration/test_api_calendar.py::TestRefreshActivity` — 4 integration tests: happy path updates DB, 404 for unknown ID, 404 for `GarminNotFoundError`, 502 for `GarminRateLimitError`
- `frontend/src/components/calendar/__tests__/WorkoutDetailPanel.refresh.test.tsx` — 4 Vitest tests: button renders, loading state, success callback, error re-enables button

## Scope
- New `GarminActivity` DB table + alembic migration
- `ActivityFetchService` for fetch/dedup/match
- Extract `GarminAdapter` to shared module
- Bidirectional sync (push workouts + fetch activities)
- Calendar API returns `CalendarResponse` wrapper with unplanned activities
- Compliance colors on WorkoutCard (green/yellow/red/grey)
- Manual pair/unpair and reschedule actions
- Auto-sync on calendar page mount
- Cleanup: delete Garmin scheduled workout from Garmin's calendar after pairing (idempotent sweep in `sync_all` + best-effort in `pair_activity`)
