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

## Testing
- Mock `garminconnect.Garmin.get_activities_by_date` in unit tests
- Integration tests use in-memory SQLite by default
- Frontend: `mockResolvedValue` (not `Once`) due to StrictMode double-fire
