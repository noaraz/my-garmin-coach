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

## Activity Fetch Gotchas (added 2026-03-20)

- **`start_time` must come from Garmin's `startTimeLocal`** — never use `datetime.now()`. Parse with `datetime.fromisoformat(activity["startTimeLocal"])`, strip tzinfo for DB storage
- **`session.add(workout)` required after matching** — async SQLAlchemy doesn't always track in-place attribute changes on existing ORM objects. Without explicit `session.add()`, `workout.completed = True` and `workout.matched_activity_id = ...` may not persist

## Testing
- Mock `garminconnect.Garmin.get_activities_by_date` in unit tests
- Integration tests use in-memory SQLite by default
- Frontend: `mockResolvedValue` (not `Once`) due to StrictMode double-fire

## Workout Detail Panel (cross-reference)

The detail panel displays activity data fetched by this feature:
- **Completed state**: Shows compliance badge + planned vs actual comparison using `computeCompliance()`
- **Unplanned state**: Shows activity metrics (duration, distance, pace, HR, calories)
- **Unpair action**: Calls existing `POST /calendar/{id}/unpair` endpoint
- **Panel design spec**: `docs/superpowers/specs/2026-03-20-workout-detail-panel-design.md`
- **Implementation lives in**: `features/calendar/` (panel is a calendar sub-feature)
