# Garmin Activity Fetch & Workout Completion Tracking

**Date:** 2026-03-19
**Status:** Draft

## Problem

GarminCoach currently only syncs *to* Garmin (pushing planned workouts). There is no way to know
whether a scheduled workout actually happened, what the results were, or to see unplanned runs.
Users must mentally track compliance themselves.

## Goal

Fetch running activity data from Garmin Connect, match activities to scheduled workouts, store
metrics, and display completion status with TrainingPeaks-style compliance colors on the calendar.

---

## 1. Data Model

### New table: `GarminActivity`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `int` PK | Auto-increment |
| `user_id` | `int` FK→User | Owner |
| `garmin_activity_id` | `str` UNIQUE | Dedup key from Garmin API |
| `activity_type` | `str` | "running", "trail_running", "treadmill_running" |
| `name` | `str` | Activity name from Garmin |
| `start_time` | `datetime` | UTC naive datetime (consistent with project convention) |
| `date` | `date` | Activity date derived from Garmin's `startTimeLocal` field (user's local date). Indexed. |
| `duration_sec` | `float` | Total elapsed time in seconds |
| `distance_m` | `float` | Total distance in meters |
| `avg_hr` | `float` nullable | Average heart rate |
| `max_hr` | `float` nullable | Max heart rate |
| `avg_pace_sec_per_km` | `float` nullable | Average pace (derived from avg speed) |
| `calories` | `int` nullable | Calories burned |
| `created_at` | `datetime` | When we fetched/stored it |
| `updated_at` | `datetime` | Last modification time |

**Index:** `(user_id, date)` for efficient range queries and matching.

**Timezone handling:** `start_time` is stored as UTC naive datetime (project convention for
PostgreSQL `TIMESTAMP WITHOUT TIME ZONE`). The `date` field is derived from Garmin's
`startTimeLocal` string (which is already in the user's local timezone), ensuring activities
land on the correct calendar day regardless of timezone.

### Modification to `ScheduledWorkout`

Add column:
- `matched_activity_id` — nullable `int` FK→`GarminActivity.id`

Named `matched_activity_id` (not `garmin_activity_id`) to avoid confusion with the existing
`garmin_workout_id` field which is a Garmin-side string ID for pushed workouts.

When an activity is matched, this FK is set and `completed` is set to `True`.
When unpaired, FK is cleared and `completed` is set to `False`.

---

## 2. Compliance System

### Compliance calculation

Compare planned vs actual metrics. Priority: duration first, then distance.

| Level | Color | CSS Variable | Condition |
|-------|-------|-------------|-----------|
| On target | Green | `--color-compliance-green` | Actual within ±20% of planned |
| Close | Yellow | `--color-compliance-yellow` | Actual 21–50% off planned |
| Off target | Red | `--color-compliance-red` | Actual >50% off planned |
| Unplanned | Grey | `--color-compliance-grey` | Activity with no scheduled workout |
| Completed (no plan data) | Green | `--color-compliance-green` | Paired but planned metrics are both null |
| Missed | Muted card | existing `--text-muted` | Past-date scheduled workout, no matched activity |

### Pure utility

`frontend/src/utils/compliance.ts`:

```typescript
type ComplianceLevel = 'on_target' | 'close' | 'off_target' | 'unplanned' | 'completed_no_plan' | 'missed'

interface ComplianceResult {
  level: ComplianceLevel
  color: string           // CSS variable name
  percentage: number | null  // e.g., 112 means 12% over. null when no planned metrics.
  metric: 'duration' | 'distance' | null
  direction: 'over' | 'under' | null
}

computeCompliance(
  planned: { duration_sec: number | null, distance_m: number | null } | null,
  actual: { duration_sec: number, distance_m: number } | null
): ComplianceResult
```

**Edge cases:**
- Both planned duration and distance are null → return `completed_no_plan` (green, no percentage)
- Planned value is `0` → treated as null (no target set) to avoid division by zero
- No actual data (unmatched) → return `missed` if past date, or skip compliance for future dates
- No planned data (unplanned activity) → return `unplanned` (grey)

---

## 3. Calendar Card UI

### Card states

**A. Paired card (scheduled + completed)**
- Left stripe: compliance color (green/yellow/red)
- Top: workout name + planned metrics (regular text)
- Bottom: actual metrics (duration, distance, avg pace, avg HR)
- Compliance badge: "▲12%" or "▼8%" with direction arrow
- Checkmark icon indicating completion

**B. Planned-only card (future or not yet done)**
- Current behavior: sport-type color stripe, name, planned metrics
- If past-date with no match: muted/faded styling (missed workout)
- Three-dot menu includes "Reschedule" option

**C. Unplanned activity card (no scheduled workout)**
- Grey stripe
- Activity name from Garmin
- Actual metrics (duration, distance, avg pace, avg HR)
- Three-dot menu includes "Pair with workout" option

### Reschedule action

Available on **all** scheduled workout cards that do NOT have a matched Garmin activity
(both past and future). Uses the existing `PATCH /api/v1/calendar/{id}` endpoint.

- Three-dot menu → "Reschedule" → date picker → `rescheduleWorkout(id, newDate)`

For **paired (completed) cards**: the user must "Unpair" first, then reschedule. The three-dot
menu on paired cards shows "Unpair activity" but not "Reschedule" — this prevents accidentally
moving a completed workout to a different date while it's still linked to activity data.

### Manual pair/unpair

- Three-dot menu on **unplanned activity** → "Pair with workout" → shows list of unmatched
  scheduled workouts on the same day. If no unmatched workouts exist on that day, show
  "No planned workouts to pair with" (disabled state). Pairing is same-day only.
  → `POST /api/v1/calendar/{id}/pair/{activity_id}`
- Three-dot menu on **paired card** → "Unpair activity"
  → `POST /api/v1/calendar/{id}/unpair`

---

## 4. Bidirectional Sync Flow

### Trigger points

1. **"Sync All" button** on calendar toolbar — becomes bidirectional
2. **Auto-sync on app start** — when CalendarPage mounts, if Garmin is connected

### Sync sequence

```
1. PUSH: Sync pending/modified/failed workouts TO Garmin (existing behavior)
2. FETCH: GET activities FROM Garmin for last 30 days (default, configurable)
3. DEDUP: Skip activities already in DB (by garmin_activity_id)
4. STORE: Insert new GarminActivity rows
5. MATCH: Auto-pair unmatched activities with unmatched scheduled workouts
6. RETURN: { synced, failed, activities_fetched, activities_matched, fetch_error }
```

**Fetch window**: Default 30 days. Passed as optional query param `fetch_days` (default 30).
On first connect, user could pass a larger value for initial backfill.

### Error handling

The fetch step is **best-effort** — if the Garmin activity API fails (network error, 429,
expired token), the push results are still returned. The response includes a `fetch_error`
field (nullable string) describing what went wrong. The frontend shows the push results
normally and displays a warning toast if `fetch_error` is set.

```python
# In sync router
try:
    fetch_result = await activity_service.fetch_and_store(...)
    match_count = await activity_service.match_activities(...)
except Exception as e:
    fetch_result = FetchResult(fetched=0, stored=0)
    match_count = 0
    fetch_error = str(e)
```

### Matching algorithm

For each scheduled workout without a `matched_activity_id`:
1. Find all `GarminActivity` rows on the same `date` with `activity_type` containing "running"
2. Filter to activities not already paired with another scheduled workout
3. If multiple matches, pick the one with the longest `duration_sec`
4. Set `ScheduledWorkout.matched_activity_id = activity.id` and `completed = True`

**Known limitation:** When multiple runs and multiple scheduled workouts exist on the same day,
longest-duration matching is a rough heuristic. Users can correct mismatches via manual
pair/unpair. This is the same trade-off TrainingPeaks makes (they also auto-pair with manual
override).

### Loading indicator

Auto-sync on mount shows a subtle indicator (e.g., spinner on the sync button) without blocking
the calendar render. Calendar data loads from DB immediately; activity data fills in when sync
completes and triggers a refetch.

---

## 5. Backend Services & API

### New: `ActivityFetchService` (`backend/src/services/activity_fetch_service.py`)

```python
class ActivityFetchService:
    async def fetch_and_store(
        self, garmin_adapter, session, user_id, start_date, end_date
    ) -> FetchResult:
        """Fetch activities from Garmin, dedup, store new ones."""

    async def match_activities(
        self, session, user_id, start_date, end_date
    ) -> int:
        """Auto-pair unmatched activities with scheduled workouts. Returns match count."""
```

### Extract: `GarminAdapter` → shared module

The existing `_GarminAdapter` (private class in `sync.py`) is used by both the sync router
and the new `ActivityFetchService`. Extract to `backend/src/garmin/adapter.py` as a public
class `GarminAdapter`.

Add method:
```python
def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict]:
    """Fetch activities from Garmin using get_activities_by_date (correct library method)."""
    return self.client.get_activities_by_date(start_date, end_date)
```

**Note:** The `garminconnect` library method is `get_activities_by_date(start, end)`, NOT
`get_activities(start, end)`. The latter takes offset+limit parameters.

### New API endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| (extended) `POST` | `/api/v1/sync/all` | Now includes fetch + match step |
| `POST` | `/api/v1/calendar/{id}/pair/{activity_id}` | Manual pair |
| `POST` | `/api/v1/calendar/{id}/unpair` | Manual unpair |

**Auth checks on pair/unpair:** Both endpoints verify `workout.user_id == current_user.id`
AND `activity.user_id == current_user.id` to prevent cross-user pairing.

### Modified API responses

**`POST /api/v1/sync/all`** response adds optional fields (backward-compatible):

```python
class SyncAllResponse(BaseModel):
    synced: int
    failed: int
    activities_fetched: int = 0       # New, default 0
    activities_matched: int = 0       # New, default 0
    fetch_error: str | None = None    # New, null = no error
```

**`GET /api/v1/calendar`** response changes to a wrapper object:

```typescript
// New response shape
interface CalendarResponse {
  workouts: ScheduledWorkoutRead[]        // Existing scheduled workouts
  unplanned_activities: GarminActivityRead[]  // Activities with no matched workout
}

// ScheduledWorkoutRead gains:
interface ScheduledWorkoutRead {
  // ... existing fields ...
  matched_activity_id: number | null
  activity: GarminActivityRead | null  // Joined data when paired
}

interface GarminActivityRead {
  id: number
  garmin_activity_id: string
  activity_type: string
  name: string
  start_time: string              // ISO datetime (for displaying time of day)
  date: string
  duration_sec: number
  distance_m: number
  avg_hr: number | null
  max_hr: number | null
  avg_pace_sec_per_km: number | null
  calories: number | null
}
```

**Breaking change:** The calendar endpoint changes from returning `list[ScheduledWorkoutRead]`
to `CalendarResponse`. **Deployment strategy:** Deploy backend and frontend together in the same
commit/build. Since Render builds from a single repo (monorepo with both Dockerfile.prod files),
both services rebuild on the same push. The brief window between backend and frontend restarts
is acceptable (seconds, not minutes). If needed, the backend could accept a `?format=v2` query
param during a migration period, but this is unlikely to be necessary.

---

## 6. Garmin API Integration

Using existing `garminconnect` library (`>=0.2.19`):

```python
# Correct method: get_activities_by_date (NOT get_activities)
activities = client.get_activities_by_date(start_date, end_date)
# Returns list of dicts with keys:
# activityId, activityName, startTimeLocal, duration, distance,
# averageHR, maxHR, averageSpeed, calories, activityType.typeKey
```

**Filter**: Only store activities where `activityType.typeKey` contains "running"
(covers "running", "trail_running", "treadmill_running").

**Pace conversion**: Use existing `speed_to_pace()` from `backend/src/garmin/converters.py`
to convert `averageSpeed` (m/s) → `avg_pace_sec_per_km`.

**Fixie proxy**: NOT needed for activity fetches. The proxy is only used for `garth.Client.login()`
(OAuth). Activity fetches use stored tokens via `garmin_client.garth.loads(token_json)` which
does not go through OAuth login.

---

## 7. Caching Considerations

**No new caching needed.** Activity data is fetched in bulk and written to DB. Calendar queries
are date-range-bounded and efficient. The hot read paths (User, Profile, Zones) are already cached
and unaffected by this feature.

If the activity fetch service reads profile data (e.g., to check `garmin_connected`), it goes through
the existing cached `ProfileService.get_or_create()`.

---

## 8. Frontend Changes Summary

| File | Change |
|------|--------|
| `api/types.ts` | Add `GarminActivityRead`, `CalendarResponse` interfaces; update `ScheduledWorkout`; update `SyncAllResponse` |
| `api/client.ts` | Update `fetchCalendarRange` return type; add `pairActivity()`, `unpairActivity()`; update `syncAll()` response |
| `utils/compliance.ts` | New pure utility for compliance calculation |
| `components/calendar/WorkoutCard.tsx` | Compliance stripe, actual metrics section, pair/unpair/reschedule menu items |
| `components/calendar/UnplannedActivityCard.tsx` | New component for grey unmatched activity cards |
| `pages/CalendarPage.tsx` | Render unplanned activities in day cells, auto-sync on mount |
| `hooks/useCalendar.ts` | Handle `CalendarResponse` shape, unplanned activities state, sync response changes |
| `index.css` | Add compliance color CSS variables in both `:root` and `[data-theme="light"]` |

---

## 9. Migration

Single alembic migration:
1. Create `garminactivity` table with all columns + `(user_id, date)` index
2. Add `matched_activity_id` nullable FK column to `scheduledworkout` with index
3. `render_as_batch` handled by existing `env.py` logic (True for SQLite, False for PostgreSQL)

**Datetime convention:** Use `datetime.now(timezone.utc).replace(tzinfo=None)` for `created_at`
and `updated_at` defaults (not the deprecated `datetime.utcnow`), per project CLAUDE.md.

**Date parsing from Garmin:** `date = datetime.fromisoformat(activity["startTimeLocal"]).date()`
— Garmin's `startTimeLocal` is already in user's local timezone, so `.date()` gives the correct
calendar day.

---

## 10. Testing Plan

### Backend unit tests

- `test_compliance.py` — compliance calculation edge cases (on_target, close, off_target,
  null planned metrics, zero values)
- `test_activity_fetch_service.py`:
  - Dedup: skip activities already in DB
  - Filter: only store running activities
  - Pace conversion: `speed_to_pace()` integration
  - Match: correct pairing by date, longest-duration wins
  - Match: no double-pairing (activity already matched)
  - Match: sets `completed = True` on paired workout

### Backend integration tests

- `test_api_sync.py` — extended sync/all returns activity counts
- `test_api_calendar.py`:
  - Pair endpoint: success, wrong user (403), activity already paired (409)
  - Unpair endpoint: success, not paired (400)
  - Calendar GET returns `CalendarResponse` shape with unplanned activities

### Frontend unit tests

- `compliance.test.ts` — mirror of backend compliance tests (including zero planned values)
- `WorkoutCard.test.tsx` — render with compliance colors, paired state, menu actions
  (reschedule visible when unpaired, hidden when paired)
- `UnplannedActivityCard.test.tsx` — render with grey stripe, metrics, pair menu,
  empty state when no workouts to pair with
- `useCalendar.test.ts` — handles new `CalendarResponse` shape, unplanned activities
- Pair/unpair interaction flow: select workout from list, confirm pairing, verify card updates
