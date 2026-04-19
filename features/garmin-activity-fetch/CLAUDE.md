# Garmin Activity Fetch — Developer Guide

## Key Patterns
- **Garmin API method**: `client.get_activities_by_date(start, end)` — NOT `get_activities()`
- **Pace conversion**: Use `speed_to_pace()` from `backend/src/garmin/converters.py`
- **Date parsing**: `date = datetime.fromisoformat(activity["startTimeLocal"]).date()`
- **Datetime convention**: `datetime.now(timezone.utc).replace(tzinfo=None)` (naive UTC)
- **FK name**: `matched_activity_id` (not `garmin_activity_id` — avoids collision with existing `garmin_workout_id`)
- **Compliance thresholds**: ±20% = green, 21-50% = yellow, >50% = red
- **Zero planned values**: Treat as null (no target) to avoid division by zero
- **Fixie proxy**: NOT needed for activity fetches (only for OAuth login)

## Data Model
- `GarminActivity` table: stores fetched running activities with dedup key `garmin_activity_id`
- `ScheduledWorkout.matched_activity_id` FK: links to paired activity
- `date` field derived from Garmin's `startTimeLocal` (user's local timezone)

## Matching Algorithm
1. Find activities on same date with `activity_type` containing "running"
2. Filter out already-paired activities
3. Pick longest `duration_sec` when multiple matches
4. Set `completed = True` on paired workout

## Garmin Calendar Cleanup After Pairing (added 2026-03-22)

**Problem**: Garmin's own calendar shows both the scheduled planned workout AND the completed activity after a run. Our app correctly shows the paired view, but Garmin's app shows two entries.

**Pattern**: In `sync_all` (`backend/src/api/routers/sync.py`), after `match_activities()` commits, run an idempotent cleanup sweep:
- Query `completed=True, garmin_workout_id IS NOT NULL` within the sync date window
- For each: call `sync_service.delete_workout(garmin_id)` (best-effort, swallowed on failure)
- Clear `garmin_workout_id = None` and `session.add(workout)`
- Commit once at the end
- Handles both newly-paired workouts from this sync AND retroactive past paired workouts

**Manual pair** (`calendar.py:pair_activity`): same best-effort delete inline before `session.commit()`, using `get_optional_garmin_sync_service` dependency (already imported).

**Why idempotent**: `garmin_workout_id` is cleared to `None` after deletion. On the next sync, the query finds no rows and is a no-op.

## Activity Fetch Gotchas (added 2026-03-20)

- **`start_time` must come from Garmin's `startTimeLocal`** — never use `datetime.now()`. Parse with `datetime.fromisoformat(activity["startTimeLocal"])`, strip tzinfo for DB storage
- **`session.add(workout)` required after matching** — async SQLAlchemy doesn't always track in-place attribute changes on existing ORM objects. Without explicit `session.add()`, `workout.completed = True` and `workout.matched_activity_id = ...` may not persist

## `activities_fetched` Semantics (added 2026-03-24)

`SyncAllResponse.activities_fetched` = `fetch_result.fetched` (total returned by Garmin API), NOT `fetch_result.stored` (new rows written to DB). This lets the UI show "Garmin returned N activities" regardless of how many were already stored. The dedup test for the sync router must reflect this: on a second call with the same activity, `activities_fetched == 1` (still fetched from Garmin) while `stored == 0` (dedup prevented insertion).

## Testing
- Mock `garminconnect.Garmin.get_activities_by_date` in unit tests
- Integration tests use in-memory SQLite by default — see `tests/integration/test_activity_fetch_service_integration.py`
- `expire_on_commit=False` in the integration test conftest — `session.refresh()` after `commit()` in test setup is a wasted round-trip; object `.id` is already populated in-memory
- Frontend: `mockResolvedValue` (not `Once`) due to StrictMode double-fire

## Activity Refresh (added 2026-04-18)

**Purpose**: Re-fetch a single activity from Garmin to fix GPS drift or missing sensor data.

**Endpoint**: `POST /api/v1/calendar/activities/{id}/refresh` → returns `GarminActivityRead`

**Error contract**:
- `GarminNotFoundError` → 404 `"Activity no longer exists on Garmin Connect"`
- Any other `GarminAdapterError` (rate limit, connection) → 502 `"Garmin is temporarily unavailable"`

**`summaryDTO` unwrap**: Single-activity Garmin responses (V1) wrap fields in a `summaryDTO` key; V2 may return them at the root. Always unwrap: `summary = raw.get("summaryDTO", raw)`.

**Date field policy**: `_update_activity()` in `ActivityFetchService` intentionally does NOT mutate the `date` field. `date` drives `match_activities` pairing — changing it would silently detach paired `ScheduledWorkout` records. Mutable fields: `distance_m`, `duration_sec`, `avg_pace_sec_per_km`, `avg_hr`, `max_hr`, `calories`, `name`, `start_time`.

**Layer chain**: `refresh_activity endpoint` → `SyncOrchestrator.get_activity()` → `GarminSyncService.get_activity()` → `adapter.get_activity(activity_id)`

**Frontend**:
- `refreshActivity(id)` in `frontend/src/api/client.ts`
- `refreshOneActivity(id)` in `frontend/src/hooks/useCalendar.ts` — calls API, refetches calendar range, returns updated activity
- `RefreshButton` in `WorkoutDetailPanel.tsx` — loading state (`refreshing`), disabled while in flight, re-enables in `finally`
- Wired via `onRefreshActivity={refreshOneActivity}` prop in `CalendarPage.tsx`

**Upsert**: `fetch_and_store` now upserts within the `start_date`/`end_date` window (bounded query). `FetchResult.updated` tracks the count of updated rows. Previous behavior was insert-only; new behavior updates existing activity fields on re-sync.

## Workout Detail Panel (cross-reference)

The detail panel displays activity data fetched by this feature:
- **Completed state**: Shows compliance badge + planned vs actual comparison using `computeCompliance()`
- **Unplanned state**: Shows activity metrics (duration, distance, pace, HR, calories)
- **Unpair action**: Calls existing `POST /calendar/{id}/unpair` endpoint
- **Panel design spec**: `docs/superpowers/specs/2026-03-20-workout-detail-panel-design.md`
- **Implementation lives in**: `features/calendar/` (panel is a calendar sub-feature)
