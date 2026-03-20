# Garmin Activity Fetch & Workout Completion Tracking — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch running activities from Garmin Connect, match them to scheduled workouts, and display TrainingPeaks-style compliance colors on the calendar.

**Architecture:** New `GarminActivity` DB table stores fetched activities. `ScheduledWorkout` gains a `matched_activity_id` FK for pairing. A new `ActivityFetchService` handles fetch/dedup/match logic. The existing bidirectional sync button pushes workouts AND fetches activities. The calendar API returns a wrapper object with both workouts and unplanned activities. WorkoutCard shows compliance colors; a new UnplannedActivityCard renders grey unmatched runs.

**Tech Stack:** FastAPI, SQLModel, Alembic, garminconnect, React 18, TypeScript, Vitest

**Design Spec:** `docs/superpowers/specs/2026-03-19-garmin-activity-fetch-design.md`

---

## File Map

### Backend — New files
| File | Responsibility |
|------|---------------|
| `backend/src/db/models.py` | Add `GarminActivity` model |
| `backend/src/garmin/adapter.py` | Extract `GarminAdapter` from `sync.py` (public, shared) |
| `backend/src/services/activity_fetch_service.py` | Fetch, dedup, store, match logic |
| `backend/src/api/routers/activity.py` | Pair/unpair endpoints (or add to calendar router) |
| `alembic/versions/xxxx_add_garmin_activity.py` | Migration: new table + FK on ScheduledWorkout |
| `backend/tests/unit/test_activity_fetch_service.py` | Unit tests for fetch/match service |
| `backend/tests/integration/test_api_activity.py` | Integration tests for pair/unpair + calendar response |

### Backend — Modified files
| File | Change |
|------|--------|
| `backend/src/api/routers/sync.py` | Extract `_GarminAdapter` → import from `adapter.py`; extend `sync_all` with fetch+match; update `SyncAllResponse` |
| `backend/src/api/routers/calendar.py` | Return `CalendarResponse` wrapper; import activity queries |
| `backend/src/api/schemas.py` | Add `GarminActivityRead`, `CalendarResponse`; update `ScheduledWorkoutRead` |
| `backend/src/repositories/calendar.py` | Add queries for unmatched activities |

### Frontend — New files
| File | Responsibility |
|------|---------------|
| `frontend/src/utils/compliance.ts` | Pure compliance calculation utility |
| `frontend/src/utils/compliance.test.ts` | Tests for compliance utility |
| `frontend/src/components/calendar/UnplannedActivityCard.tsx` | Grey card for unmatched activities |
| `frontend/src/components/calendar/UnplannedActivityCard.test.tsx` | Tests |
| `frontend/src/components/calendar/CardMenu.tsx` | Three-dot menu with reschedule/pair/unpair actions |

### Frontend — Modified files
| File | Change |
|------|--------|
| `frontend/src/api/types.ts` | Add `GarminActivityRead`, `CalendarResponse`; update `ScheduledWorkout`, `SyncAllResponse` |
| `frontend/src/api/client.ts` | Update `fetchCalendarRange` return type; add `pairActivity`, `unpairActivity` |
| `frontend/src/hooks/useCalendar.ts` | Handle `CalendarResponse` shape; add `unplannedActivities` state; auto-sync on mount |
| `frontend/src/components/calendar/WorkoutCard.tsx` | Compliance stripe, actual metrics, menu |
| `frontend/src/pages/CalendarPage.tsx` | Render unplanned activities; pass new props to CalendarView |
| `frontend/src/index.css` | Add compliance color CSS variables |

---

## Phase 0: Documentation & Branch Setup

> **Runs in main session (not parallelizable)**

### Task 0.1: Create feature documentation

**Files:**
- Create: `features/garmin-activity-fetch/PLAN.md`
- Create: `features/garmin-activity-fetch/CLAUDE.md`
- Modify: `STATUS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create feature PLAN.md**

Create `features/garmin-activity-fetch/PLAN.md` with a summary of what this feature does and a link to the design spec:

```markdown
# Garmin Activity Fetch — Feature Plan

## Overview
Fetch running activity data from Garmin Connect, auto-match to scheduled workouts,
and display TrainingPeaks-style compliance colors on the calendar.

## Design Spec
See `docs/superpowers/specs/2026-03-19-garmin-activity-fetch-design.md`

## Implementation Plan
See `docs/superpowers/plans/2026-03-19-garmin-activity-fetch.md`

## Scope
- New `GarminActivity` DB table + alembic migration
- `ActivityFetchService` for fetch/dedup/match
- Extract `GarminAdapter` to shared module
- Bidirectional sync (push workouts + fetch activities)
- Calendar API returns `CalendarResponse` wrapper with unplanned activities
- Compliance colors on WorkoutCard (green/yellow/red/grey)
- Manual pair/unpair and reschedule actions
- Auto-sync on calendar page mount
```

- [ ] **Step 2: Create feature CLAUDE.md**

Create `features/garmin-activity-fetch/CLAUDE.md`:

```markdown
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

## Testing
- Mock `garminconnect.Garmin.get_activities_by_date` in unit tests
- Integration tests use in-memory SQLite by default
- Frontend: `mockResolvedValue` (not `Once`) due to StrictMode double-fire
```

- [ ] **Step 3: Update STATUS.md**

Add under "In Progress":
```
### Garmin Activity Fetch & Workout Completion Tracking
- Design spec: `docs/superpowers/specs/2026-03-19-garmin-activity-fetch-design.md`
- Implementation: started 2026-03-19
```

- [ ] **Step 4: Update root CLAUDE.md**

Add a row to the Features table:
```
| Activity Fetch | `features/garmin-activity-fetch/` | Fetch Garmin activities, compliance tracking |
```

- [ ] **Step 5: Merge from main and create feature branch**

```bash
git checkout main
git pull origin main
git checkout -b feature/garmin-activity-fetch
```

- [ ] **Step 6: Commit documentation**

```bash
git add features/garmin-activity-fetch/ STATUS.md CLAUDE.md
git commit -m "docs: add garmin activity fetch feature plan and design reference"
```

---

## Phase 1: Backend Core (Parallel Tasks 1-3)

> **Three independent backend-dev subagents can run in parallel.**
> Task 1 (model + migration), Task 2 (adapter extraction), Task 3 (compliance utility) touch different files.

### Task 1: GarminActivity model + Alembic migration

**Agent:** `backend-dev`
**Files:**
- Modify: `backend/src/db/models.py`
- Create: `alembic/versions/xxxx_add_garmin_activity.py` (auto-generated)
- Test: `backend/tests/unit/test_models_activity.py`

- [ ] **Step 1: Write test for GarminActivity model**

```python
# backend/tests/unit/test_models_activity.py
from __future__ import annotations

from datetime import date, datetime, timezone

from src.db.models import GarminActivity, ScheduledWorkout


class TestGarminActivityModel:
    def test_create_garmin_activity(self):
        activity = GarminActivity(
            user_id=1,
            garmin_activity_id="12345678",
            activity_type="running",
            name="Morning Run",
            start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            date=date(2026, 3, 19),
            duration_sec=1800.0,
            distance_m=5000.0,
            avg_hr=145.0,
            max_hr=165.0,
            avg_pace_sec_per_km=360.0,
            calories=350,
        )
        assert activity.garmin_activity_id == "12345678"
        assert activity.activity_type == "running"
        assert activity.duration_sec == 1800.0

    def test_garmin_activity_nullable_fields(self):
        activity = GarminActivity(
            user_id=1,
            garmin_activity_id="99999",
            activity_type="treadmill_running",
            name="Treadmill",
            start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            date=date(2026, 3, 19),
            duration_sec=600.0,
            distance_m=2000.0,
        )
        assert activity.avg_hr is None
        assert activity.max_hr is None
        assert activity.avg_pace_sec_per_km is None
        assert activity.calories is None

    def test_scheduled_workout_matched_activity_id(self):
        sw = ScheduledWorkout(
            user_id=1,
            date=date(2026, 3, 19),
            matched_activity_id=42,
        )
        assert sw.matched_activity_id == 42
        assert sw.completed is False  # Default

    def test_scheduled_workout_matched_activity_id_default_none(self):
        sw = ScheduledWorkout(user_id=1, date=date(2026, 3, 19))
        assert sw.matched_activity_id is None
```

- [ ] **Step 2: Run test — expect RED (ImportError)**

```bash
cd backend && python -m pytest tests/unit/test_models_activity.py -v
```
Expected: FAIL — `GarminActivity` not defined, `matched_activity_id` not on ScheduledWorkout.

- [ ] **Step 3: Implement GarminActivity model + modify ScheduledWorkout**

Add to `backend/src/db/models.py`:

```python
class GarminActivity(SQLModel, table=True):
    """A running activity fetched from Garmin Connect."""

    __tablename__ = "garminactivity"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    garmin_activity_id: str = Field(unique=True)  # Dedup key
    activity_type: str  # "running", "trail_running", etc.
    name: str
    start_time: datetime  # UTC naive
    date: date  # Derived from Garmin startTimeLocal
    duration_sec: float
    distance_m: float
    avg_hr: Optional[float] = Field(default=None)
    max_hr: Optional[float] = Field(default=None)
    avg_pace_sec_per_km: Optional[float] = Field(default=None)
    calories: Optional[int] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
```

Add import at top: `from datetime import date, datetime, timezone`

Add to `ScheduledWorkout`:
```python
    matched_activity_id: Optional[int] = Field(
        default=None, foreign_key="garminactivity.id"
    )
```

- [ ] **Step 4: Run test — expect GREEN**

```bash
cd backend && python -m pytest tests/unit/test_models_activity.py -v
```

- [ ] **Step 5: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add garmin activity table and matched_activity_id FK"
```

Verify the generated migration creates the `garminactivity` table and adds `matched_activity_id` to `scheduledworkout`. Manually add the index:

```python
op.create_index("ix_garminactivity_user_date", "garminactivity", ["user_id", "date"])
op.create_index("ix_scheduledworkout_matched_activity", "scheduledworkout", ["matched_activity_id"])
```

- [ ] **Step 6: Run migration**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/db/models.py backend/tests/unit/test_models_activity.py alembic/
git commit -m "feat: add GarminActivity model and matched_activity_id FK on ScheduledWorkout"
```

---

### Task 2: Extract GarminAdapter to shared module

**Agent:** `backend-dev`
**Files:**
- Create: `backend/src/garmin/adapter.py`
- Modify: `backend/src/api/routers/sync.py`
- Test: `backend/tests/unit/test_garmin_adapter.py`

- [ ] **Step 1: Write test for GarminAdapter**

```python
# backend/tests/unit/test_garmin_adapter.py
from __future__ import annotations

from unittest.mock import MagicMock

from src.garmin.adapter import GarminAdapter


class TestGarminAdapter:
    def test_add_workout_delegates(self):
        mock_client = MagicMock()
        mock_client.upload_workout.return_value = {"workoutId": "123"}
        adapter = GarminAdapter(mock_client)
        result = adapter.add_workout({"workoutName": "Test"})
        mock_client.upload_workout.assert_called_once_with({"workoutName": "Test"})
        assert result == {"workoutId": "123"}

    def test_get_activities_by_date_delegates(self):
        mock_client = MagicMock()
        mock_client.get_activities_by_date.return_value = [
            {"activityId": "1", "activityType": {"typeKey": "running"}},
        ]
        adapter = GarminAdapter(mock_client)
        result = adapter.get_activities_by_date("2026-03-01", "2026-03-19")
        mock_client.get_activities_by_date.assert_called_once_with("2026-03-01", "2026-03-19")
        assert len(result) == 1

    def test_delete_workout_delegates(self):
        mock_client = MagicMock()
        adapter = GarminAdapter(mock_client)
        adapter.delete_workout("456")
        mock_client.garth.delete.assert_called_once()
```

- [ ] **Step 2: Run test — expect RED**

```bash
cd backend && python -m pytest tests/unit/test_garmin_adapter.py -v
```

- [ ] **Step 3: Create `backend/src/garmin/adapter.py`**

```python
"""Shared Garmin client adapter.

Bridges the garminconnect library interface to the interface expected by
GarminSyncService and ActivityFetchService.
"""
from __future__ import annotations

from typing import Any

import garminconnect


class GarminAdapter:
    """Wraps garminconnect.Garmin to provide a clean interface."""

    def __init__(self, client: garminconnect.Garmin) -> None:
        self._client = client

    def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]:
        return self._client.upload_workout(formatted_workout)

    def schedule_workout(self, workout_id: str, workout_date: str) -> None:
        url = f"{self._client.garmin_workouts_schedule_url}/{workout_id}"
        self._client.garth.post("connectapi", url, json={"date": workout_date}, api=True)

    def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None:
        url = f"/workout-service/workout/{workout_id}"
        self._client.garth.put("connectapi", url, json=formatted_workout, api=True)

    def delete_workout(self, workout_id: str) -> None:
        url = f"/workout-service/workout/{workout_id}"
        self._client.garth.delete("connectapi", url, api=True)

    def get_activities_by_date(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Fetch activities from Garmin within a date range."""
        return self._client.get_activities_by_date(start_date, end_date)
```

- [ ] **Step 4: Update `sync.py` to import from adapter**

In `backend/src/api/routers/sync.py`:
- Remove the `_GarminAdapter` class (lines 43-72)
- Add import: `from src.garmin.adapter import GarminAdapter`
- Replace `_GarminAdapter(garmin_client)` with `GarminAdapter(garmin_client)` in `_get_garmin_sync_service`

- [ ] **Step 5: Run all tests — expect GREEN**

```bash
cd backend && python -m pytest tests/unit/test_garmin_adapter.py tests/ -v --timeout=30
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/garmin/adapter.py backend/src/api/routers/sync.py backend/tests/unit/test_garmin_adapter.py
git commit -m "refactor: extract GarminAdapter to shared module with get_activities_by_date"
```

---

### Task 3: Frontend compliance utility (pure, no deps)

**Agent:** `frontend-dev`
**Files:**
- Create: `frontend/src/utils/compliance.ts`
- Create: `frontend/src/utils/compliance.test.ts`

- [ ] **Step 1: Write tests**

```typescript
// frontend/src/utils/compliance.test.ts
import { describe, it, expect } from 'vitest'
import { computeCompliance } from './compliance'

describe('computeCompliance', () => {
  it('returns on_target when actual within 20% of planned duration', () => {
    const result = computeCompliance(
      { duration_sec: 1800, distance_m: null },
      { duration_sec: 1900, distance_m: 5000 }
    )
    expect(result.level).toBe('on_target')
    expect(result.metric).toBe('duration')
  })

  it('returns close when actual 30% over planned', () => {
    const result = computeCompliance(
      { duration_sec: 1000, distance_m: null },
      { duration_sec: 1350, distance_m: 4000 }
    )
    expect(result.level).toBe('close')
    expect(result.direction).toBe('over')
  })

  it('returns off_target when actual >50% under planned', () => {
    const result = computeCompliance(
      { duration_sec: 3600, distance_m: null },
      { duration_sec: 1000, distance_m: 3000 }
    )
    expect(result.level).toBe('off_target')
    expect(result.direction).toBe('under')
  })

  it('falls back to distance when duration is null', () => {
    const result = computeCompliance(
      { duration_sec: null, distance_m: 10000 },
      { duration_sec: 2000, distance_m: 9500 }
    )
    expect(result.level).toBe('on_target')
    expect(result.metric).toBe('distance')
  })

  it('returns completed_no_plan when both planned metrics null', () => {
    const result = computeCompliance(
      { duration_sec: null, distance_m: null },
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.level).toBe('completed_no_plan')
    expect(result.percentage).toBeNull()
  })

  it('treats zero planned values as null', () => {
    const result = computeCompliance(
      { duration_sec: 0, distance_m: 0 },
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.level).toBe('completed_no_plan')
  })

  it('returns unplanned when planned is null', () => {
    const result = computeCompliance(
      null,
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.level).toBe('unplanned')
  })

  it('returns missed when actual is null', () => {
    const result = computeCompliance(
      { duration_sec: 1800, distance_m: null },
      null
    )
    expect(result.level).toBe('missed')
  })

  it('percentage is 100 for exact match', () => {
    const result = computeCompliance(
      { duration_sec: 1800, distance_m: null },
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.percentage).toBe(100)
    expect(result.direction).toBeNull()
  })
})
```

- [ ] **Step 2: Run test — expect RED**

```bash
cd frontend && npx vitest run src/utils/compliance.test.ts
```

- [ ] **Step 3: Implement compliance utility**

```typescript
// frontend/src/utils/compliance.ts
export type ComplianceLevel =
  | 'on_target'
  | 'close'
  | 'off_target'
  | 'unplanned'
  | 'completed_no_plan'
  | 'missed'

export interface ComplianceResult {
  level: ComplianceLevel
  color: string
  percentage: number | null
  metric: 'duration' | 'distance' | null
  direction: 'over' | 'under' | null
}

interface PlannedMetrics {
  duration_sec: number | null
  distance_m: number | null
}

interface ActualMetrics {
  duration_sec: number
  distance_m: number
}

const COLORS: Record<ComplianceLevel, string> = {
  on_target: 'var(--color-compliance-green)',
  close: 'var(--color-compliance-yellow)',
  off_target: 'var(--color-compliance-red)',
  unplanned: 'var(--color-compliance-grey)',
  completed_no_plan: 'var(--color-compliance-green)',
  missed: 'var(--text-muted)',
}

function isUsable(val: number | null): val is number {
  return val != null && val > 0
}

export function computeCompliance(
  planned: PlannedMetrics | null,
  actual: ActualMetrics | null
): ComplianceResult {
  if (planned == null) {
    return { level: 'unplanned', color: COLORS.unplanned, percentage: null, metric: null, direction: null }
  }
  if (actual == null) {
    return { level: 'missed', color: COLORS.missed, percentage: null, metric: null, direction: null }
  }

  // Pick comparison metric: duration first, then distance
  let plannedVal: number | null = null
  let actualVal: number | null = null
  let metric: 'duration' | 'distance' | null = null

  if (isUsable(planned.duration_sec)) {
    plannedVal = planned.duration_sec
    actualVal = actual.duration_sec
    metric = 'duration'
  } else if (isUsable(planned.distance_m)) {
    plannedVal = planned.distance_m
    actualVal = actual.distance_m
    metric = 'distance'
  }

  if (plannedVal == null || actualVal == null || metric == null) {
    return { level: 'completed_no_plan', color: COLORS.completed_no_plan, percentage: null, metric: null, direction: null }
  }

  const pct = Math.round((actualVal / plannedVal) * 100)
  const diff = Math.abs(pct - 100)
  const direction: 'over' | 'under' | null = pct > 100 ? 'over' : pct < 100 ? 'under' : null

  let level: ComplianceLevel
  if (diff <= 20) level = 'on_target'
  else if (diff <= 50) level = 'close'
  else level = 'off_target'

  return { level, color: COLORS[level], percentage: pct, metric, direction }
}
```

- [ ] **Step 4: Run test — expect GREEN**

```bash
cd frontend && npx vitest run src/utils/compliance.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/compliance.ts frontend/src/utils/compliance.test.ts
git commit -m "feat: add compliance calculation utility for workout completion tracking"
```

---

## Phase 2: Backend Services & API (Parallel Tasks 4-5)

> **Two backend-dev subagents can run in parallel.**
> Task 4 (ActivityFetchService) and Task 5 (API schemas + endpoints) are closely related but can be split: Task 4 is pure service logic (no router), Task 5 is API layer.

### Task 4: ActivityFetchService

**Agent:** `backend-dev`
**Files:**
- Create: `backend/src/services/activity_fetch_service.py`
- Test: `backend/tests/unit/test_activity_fetch_service.py`

- [ ] **Step 1: Write tests for fetch_and_store**

```python
# backend/tests/unit/test_activity_fetch_service.py
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.services.activity_fetch_service import ActivityFetchService
from src.db.models import GarminActivity


def _make_garmin_activity(
    activity_id: str = "111",
    type_key: str = "running",
    name: str = "Morning Run",
    start_time_local: str = "2026-03-19 07:30:00",
    duration: float = 1800.0,
    distance: float = 5000.0,
    avg_speed: float = 2.78,  # ~6:00/km
    avg_hr: float = 145.0,
    max_hr: float = 165.0,
    calories: int = 350,
) -> dict:
    return {
        "activityId": activity_id,
        "activityType": {"typeKey": type_key},
        "activityName": name,
        "startTimeLocal": start_time_local,
        "duration": duration,
        "distance": distance,
        "averageSpeed": avg_speed,
        "averageHR": avg_hr,
        "maxHR": max_hr,
        "calories": calories,
    }


class TestActivityFetchService:
    @pytest.fixture()
    def service(self):
        return ActivityFetchService()

    def test_parse_activity_extracts_fields(self, service):
        raw = _make_garmin_activity()
        parsed = service._parse_activity(raw, user_id=1)
        assert parsed.garmin_activity_id == "111"
        assert parsed.activity_type == "running"
        assert parsed.name == "Morning Run"
        assert parsed.date == date(2026, 3, 19)
        assert parsed.duration_sec == 1800.0
        assert parsed.distance_m == 5000.0
        assert parsed.avg_hr == 145.0
        assert parsed.max_hr == 165.0
        assert parsed.calories == 350
        # Pace conversion: 1000 / 2.78 ≈ 359.7
        assert parsed.avg_pace_sec_per_km is not None
        assert abs(parsed.avg_pace_sec_per_km - 359.7) < 1.0

    def test_parse_activity_filters_non_running(self, service):
        raw = _make_garmin_activity(type_key="cycling")
        result = service._parse_activity(raw, user_id=1)
        assert result is None

    def test_parse_activity_accepts_trail_running(self, service):
        raw = _make_garmin_activity(type_key="trail_running")
        result = service._parse_activity(raw, user_id=1)
        assert result is not None
        assert result.activity_type == "trail_running"

    def test_parse_activity_handles_zero_speed(self, service):
        raw = _make_garmin_activity(avg_speed=0.0)
        parsed = service._parse_activity(raw, user_id=1)
        assert parsed is not None
        assert parsed.avg_pace_sec_per_km is None


class TestMatchActivities:
    """Test the matching algorithm logic."""

    def test_match_picks_longest_when_multiple(self):
        """When two activities exist on the same day, match the longest."""
        service = ActivityFetchService()
        activities = [
            GarminActivity(
                id=1, user_id=1, garmin_activity_id="a",
                activity_type="running", name="Short",
                start_time=datetime.now(timezone.utc).replace(tzinfo=None),
                date=date(2026, 3, 19), duration_sec=600, distance_m=2000,
            ),
            GarminActivity(
                id=2, user_id=1, garmin_activity_id="b",
                activity_type="running", name="Long",
                start_time=datetime.now(timezone.utc).replace(tzinfo=None),
                date=date(2026, 3, 19), duration_sec=3600, distance_m=10000,
            ),
        ]
        best = service._pick_best_match(activities)
        assert best is not None
        assert best.id == 2

    def test_match_returns_none_for_empty(self):
        service = ActivityFetchService()
        assert service._pick_best_match([]) is None
```

- [ ] **Step 2: Run test — expect RED**

```bash
cd backend && python -m pytest tests/unit/test_activity_fetch_service.py -v
```

- [ ] **Step 3: Implement ActivityFetchService**

```python
# backend/src/services/activity_fetch_service.py
"""Service for fetching Garmin activities and matching them to scheduled workouts."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import GarminActivity, ScheduledWorkout
from src.garmin.converters import speed_to_pace

logger = logging.getLogger(__name__)

_RUNNING_TYPES = ("running", "trail_running", "treadmill_running", "track_running")


@dataclass
class FetchResult:
    fetched: int = 0
    stored: int = 0


class ActivityFetchService:
    def _parse_activity(
        self, raw: dict[str, Any], user_id: int
    ) -> GarminActivity | None:
        """Parse a raw Garmin activity dict into a GarminActivity model.

        Returns None if the activity is not a running type.
        """
        type_key = raw.get("activityType", {}).get("typeKey", "")
        if type_key not in _RUNNING_TYPES:
            return None

        avg_speed = raw.get("averageSpeed", 0.0) or 0.0
        avg_pace = speed_to_pace(avg_speed) if avg_speed > 0 else None

        start_time_local = raw.get("startTimeLocal", "")
        try:
            local_dt = datetime.fromisoformat(start_time_local)
            activity_date = local_dt.date()
        except (ValueError, TypeError):
            activity_date = date.today()

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        return GarminActivity(
            user_id=user_id,
            garmin_activity_id=str(raw["activityId"]),
            activity_type=type_key,
            name=raw.get("activityName", "Activity"),
            start_time=now,  # UTC approximate
            date=activity_date,
            duration_sec=float(raw.get("duration", 0)),
            distance_m=float(raw.get("distance", 0)),
            avg_hr=raw.get("averageHR"),
            max_hr=raw.get("maxHR"),
            avg_pace_sec_per_km=avg_pace,
            calories=raw.get("calories"),
        )

    def _pick_best_match(
        self, candidates: list[GarminActivity]
    ) -> GarminActivity | None:
        """Pick the longest-duration activity from candidates."""
        if not candidates:
            return None
        return max(candidates, key=lambda a: a.duration_sec)

    async def fetch_and_store(
        self,
        garmin_adapter: Any,
        session: AsyncSession,
        user_id: int,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """Fetch activities from Garmin, dedup, store new ones."""
        raw_activities = garmin_adapter.get_activities_by_date(start_date, end_date)
        result = FetchResult(fetched=len(raw_activities))

        # Get existing garmin_activity_ids for dedup
        existing = await session.exec(
            select(GarminActivity.garmin_activity_id).where(
                GarminActivity.user_id == user_id
            )
        )
        existing_ids = set(existing.all())

        for raw in raw_activities:
            parsed = self._parse_activity(raw, user_id)
            if parsed is None:
                continue
            if parsed.garmin_activity_id in existing_ids:
                continue
            session.add(parsed)
            existing_ids.add(parsed.garmin_activity_id)
            result.stored += 1

        if result.stored > 0:
            await session.flush()  # Assign IDs but don't commit yet

        return result

    async def match_activities(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> int:
        """Auto-pair unmatched activities with scheduled workouts.

        Returns the number of matches made.
        """
        # Get unmatched scheduled workouts in range
        unmatched_workouts = (
            await session.exec(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.user_id == user_id,
                    ScheduledWorkout.date >= start_date,
                    ScheduledWorkout.date <= end_date,
                    ScheduledWorkout.matched_activity_id.is_(None),  # type: ignore[union-attr]
                )
            )
        ).all()

        if not unmatched_workouts:
            return 0

        # Get all activities in range that are not yet paired
        paired_ids_result = await session.exec(
            select(ScheduledWorkout.matched_activity_id).where(
                ScheduledWorkout.matched_activity_id.is_not(None),  # type: ignore[union-attr]
                ScheduledWorkout.user_id == user_id,
            )
        )
        paired_ids = set(paired_ids_result.all())

        all_activities = (
            await session.exec(
                select(GarminActivity).where(
                    GarminActivity.user_id == user_id,
                    GarminActivity.date >= start_date,
                    GarminActivity.date <= end_date,
                )
            )
        ).all()

        # Group activities by date
        activities_by_date: dict[date, list[GarminActivity]] = {}
        for a in all_activities:
            if a.id in paired_ids:
                continue
            activities_by_date.setdefault(a.date, []).append(a)

        match_count = 0
        for workout in unmatched_workouts:
            candidates = activities_by_date.get(workout.date, [])
            best = self._pick_best_match(candidates)
            if best is not None:
                workout.matched_activity_id = best.id
                workout.completed = True
                workout.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                # Remove from candidates so it can't be double-matched
                candidates.remove(best)
                paired_ids.add(best.id)
                match_count += 1

        return match_count


activity_fetch_service = ActivityFetchService()
```

- [ ] **Step 4: Run test — expect GREEN**

```bash
cd backend && python -m pytest tests/unit/test_activity_fetch_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/activity_fetch_service.py backend/tests/unit/test_activity_fetch_service.py
git commit -m "feat: add ActivityFetchService for Garmin activity fetch, dedup, and matching"
```

---

### Task 5: API schemas, calendar response, sync extension, pair/unpair endpoints

**Agent:** `backend-dev`
**Files:**
- Modify: `backend/src/api/schemas.py`
- Modify: `backend/src/api/routers/calendar.py`
- Modify: `backend/src/api/routers/sync.py`
- Test: `backend/tests/integration/test_api_activity.py`

- [ ] **Step 1: Add schemas**

In `backend/src/api/schemas.py`, add:

```python
class GarminActivityRead(BaseModel):
    id: int
    garmin_activity_id: str
    activity_type: str
    name: str
    start_time: datetime
    date: date
    duration_sec: float
    distance_m: float
    avg_hr: Optional[float] = None
    max_hr: Optional[float] = None
    avg_pace_sec_per_km: Optional[float] = None
    calories: Optional[int] = None

    model_config = {"from_attributes": True}


class ScheduledWorkoutWithActivity(ScheduledWorkoutRead):
    """ScheduledWorkoutRead extended with matched activity data."""
    matched_activity_id: Optional[int] = None
    activity: Optional[GarminActivityRead] = None


class CalendarResponse(BaseModel):
    workouts: list[ScheduledWorkoutWithActivity]
    unplanned_activities: list[GarminActivityRead]
```

- [ ] **Step 2: Update calendar router to return CalendarResponse**

In `backend/src/api/routers/calendar.py`, update `get_calendar_range`:

```python
from src.api.schemas import CalendarResponse, GarminActivityRead, ScheduledWorkoutWithActivity
from src.db.models import GarminActivity

@router.get("", response_model=CalendarResponse)
async def get_calendar_range(
    start: date,
    end: date,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CalendarResponse:
    """Return scheduled workouts and unplanned activities within the date range."""
    workouts = await get_range(session, start, end, current_user.id)

    # Batch-load matched activities
    activity_ids = [w.matched_activity_id for w in workouts if w.matched_activity_id]
    activities_map: dict[int, GarminActivity] = {}
    if activity_ids:
        from sqlmodel import select
        result = await session.exec(
            select(GarminActivity).where(GarminActivity.id.in_(activity_ids))
        )
        activities_map = {a.id: a for a in result.all()}

    workout_reads = []
    for w in workouts:
        activity = activities_map.get(w.matched_activity_id) if w.matched_activity_id else None
        wr = ScheduledWorkoutWithActivity(
            **ScheduledWorkoutRead.model_validate(w).model_dump(),
            matched_activity_id=w.matched_activity_id,
            activity=GarminActivityRead.model_validate(activity) if activity else None,
        )
        workout_reads.append(wr)

    # Get unplanned activities (not matched to any workout)
    paired_activity_ids = {w.matched_activity_id for w in workouts if w.matched_activity_id}
    from sqlmodel import select
    all_activities_result = await session.exec(
        select(GarminActivity).where(
            GarminActivity.user_id == current_user.id,
            GarminActivity.date >= start,
            GarminActivity.date <= end,
        )
    )
    all_activities = all_activities_result.all()
    unplanned = [
        GarminActivityRead.model_validate(a)
        for a in all_activities
        if a.id not in paired_activity_ids
    ]

    return CalendarResponse(workouts=workout_reads, unplanned_activities=unplanned)
```

- [ ] **Step 3: Add pair/unpair endpoints to calendar router**

```python
@router.post("/{scheduled_id}/pair/{activity_id}", response_model=ScheduledWorkoutWithActivity)
async def pair_activity(
    scheduled_id: int,
    activity_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScheduledWorkoutWithActivity:
    """Manually pair a scheduled workout with a Garmin activity."""
    workout = await session.get(ScheduledWorkout, scheduled_id)
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workout not found")

    activity = await session.get(GarminActivity, activity_id)
    if activity is None or activity.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Activity not found")

    if workout.matched_activity_id is not None:
        raise HTTPException(status_code=409, detail="Workout already paired")

    workout.matched_activity_id = activity.id
    workout.completed = True
    workout.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(workout)
    await session.commit()
    await session.refresh(workout)

    return ScheduledWorkoutWithActivity(
        **ScheduledWorkoutRead.model_validate(workout).model_dump(),
        matched_activity_id=workout.matched_activity_id,
        activity=GarminActivityRead.model_validate(activity),
    )


@router.post("/{scheduled_id}/unpair", response_model=ScheduledWorkoutWithActivity)
async def unpair_activity(
    scheduled_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScheduledWorkoutWithActivity:
    """Remove the pairing between a scheduled workout and its matched activity."""
    workout = await session.get(ScheduledWorkout, scheduled_id)
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Workout not found")

    if workout.matched_activity_id is None:
        raise HTTPException(status_code=400, detail="Workout is not paired")

    workout.matched_activity_id = None
    workout.completed = False
    workout.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(workout)
    await session.commit()
    await session.refresh(workout)

    return ScheduledWorkoutWithActivity(
        **ScheduledWorkoutRead.model_validate(workout).model_dump(),
        matched_activity_id=None,
        activity=None,
    )
```

- [ ] **Step 4: Extend sync_all with activity fetch**

In `backend/src/api/routers/sync.py`, update `SyncAllResponse` and `sync_all`:

```python
class SyncAllResponse(BaseModel):
    synced: int
    failed: int
    activities_fetched: int = 0
    activities_matched: int = 0
    fetch_error: str | None = None
```

Update `sync_all` to add fetch+match after push:

```python
from src.services.activity_fetch_service import activity_fetch_service

@router.post("/all", response_model=SyncAllResponse)
async def sync_all(
    fetch_days: int = 30,
    session: AsyncSession = Depends(get_session),
    sync_service: SyncOrchestrator = Depends(_get_garmin_sync_service),
    current_user: User = Depends(get_current_user),
) -> SyncAllResponse:
    # ... existing push logic (unchanged) ...
    hr_zone_map, pace_zone_map = await _get_zone_maps(session, current_user)
    workouts = await scheduled_workout_repository.get_by_status(session, _PENDING_STATUSES, current_user.id)
    templates = await _preload_templates(session, workouts)
    results = [
        await _sync_and_persist(session, sync_service, w, hr_zone_map, pace_zone_map, templates)
        for w in workouts
    ]
    await session.commit()
    synced = sum(1 for r in results if r is not None)
    failed = len(results) - synced

    # Fetch activities (best-effort)
    activities_fetched = 0
    activities_matched = 0
    fetch_error = None
    try:
        from datetime import date as date_type, timedelta
        end_date = date_type.today()
        start_date = end_date - timedelta(days=fetch_days)

        # Get the garmin adapter from the sync service
        garmin_adapter = GarminAdapter(sync_service._sync_service._client)

        fetch_result = await activity_fetch_service.fetch_and_store(
            garmin_adapter, session, current_user.id,
            str(start_date), str(end_date),
        )
        activities_fetched = fetch_result.stored
        activities_matched = await activity_fetch_service.match_activities(
            session, current_user.id, start_date, end_date,
        )
        await session.commit()
    except Exception as exc:
        fetch_error = str(exc)
        logger.warning("Activity fetch failed (continuing): %s", exc)

    return SyncAllResponse(
        synced=synced, failed=failed,
        activities_fetched=activities_fetched,
        activities_matched=activities_matched,
        fetch_error=fetch_error,
    )
```

Note: The `garmin_adapter` access pattern here needs refinement — the `SyncOrchestrator` currently wraps the adapter. We need to expose the underlying client. Add a property to `SyncOrchestrator` or pass the adapter separately. The implementer should check the actual `SyncOrchestrator` interface and adjust accordingly. The key point is: reuse the same authenticated garminconnect.Garmin client that was already created for push.

- [ ] **Step 5: Write integration tests**

```python
# backend/tests/integration/test_api_activity.py
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone
from httpx import AsyncClient

from src.db.models import GarminActivity, ScheduledWorkout


@pytest.mark.asyncio
class TestCalendarWithActivities:
    async def test_calendar_returns_wrapper_response(self, client: AsyncClient, session):
        res = await client.get("/api/v1/calendar?start=2026-03-01&end=2026-03-31")
        assert res.status_code == 200
        body = res.json()
        assert "workouts" in body
        assert "unplanned_activities" in body

    async def test_paired_workout_includes_activity(self, client: AsyncClient, session):
        # Create activity
        activity = GarminActivity(
            user_id=1, garmin_activity_id="test-1", activity_type="running",
            name="Test Run", start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            date=date(2026, 3, 15), duration_sec=1800, distance_m=5000,
        )
        session.add(activity)
        await session.flush()

        # Create workout paired to activity
        workout = ScheduledWorkout(
            user_id=1, date=date(2026, 3, 15),
            matched_activity_id=activity.id, completed=True,
        )
        session.add(workout)
        await session.commit()

        res = await client.get("/api/v1/calendar?start=2026-03-01&end=2026-03-31")
        body = res.json()
        assert len(body["workouts"]) == 1
        assert body["workouts"][0]["activity"] is not None
        assert body["workouts"][0]["activity"]["name"] == "Test Run"


@pytest.mark.asyncio
class TestPairUnpair:
    async def test_pair_success(self, client: AsyncClient, session):
        activity = GarminActivity(
            user_id=1, garmin_activity_id="pair-1", activity_type="running",
            name="Run", start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            date=date(2026, 3, 15), duration_sec=1800, distance_m=5000,
        )
        session.add(activity)
        await session.flush()

        workout = ScheduledWorkout(user_id=1, date=date(2026, 3, 15))
        session.add(workout)
        await session.commit()

        res = await client.post(f"/api/v1/calendar/{workout.id}/pair/{activity.id}")
        assert res.status_code == 200
        assert res.json()["completed"] is True
        assert res.json()["matched_activity_id"] == activity.id

    async def test_unpair_success(self, client: AsyncClient, session):
        activity = GarminActivity(
            user_id=1, garmin_activity_id="unpair-1", activity_type="running",
            name="Run", start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            date=date(2026, 3, 15), duration_sec=1800, distance_m=5000,
        )
        session.add(activity)
        await session.flush()

        workout = ScheduledWorkout(
            user_id=1, date=date(2026, 3, 15),
            matched_activity_id=activity.id, completed=True,
        )
        session.add(workout)
        await session.commit()

        res = await client.post(f"/api/v1/calendar/{workout.id}/unpair")
        assert res.status_code == 200
        assert res.json()["completed"] is False
        assert res.json()["matched_activity_id"] is None

    async def test_unpair_not_paired_returns_400(self, client: AsyncClient, session):
        workout = ScheduledWorkout(user_id=1, date=date(2026, 3, 15))
        session.add(workout)
        await session.commit()

        res = await client.post(f"/api/v1/calendar/{workout.id}/unpair")
        assert res.status_code == 400
```

- [ ] **Step 6: Run tests — expect GREEN**

```bash
cd backend && python -m pytest tests/integration/test_api_activity.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/api/schemas.py backend/src/api/routers/calendar.py backend/src/api/routers/sync.py backend/tests/integration/test_api_activity.py
git commit -m "feat: add CalendarResponse, pair/unpair endpoints, bidirectional sync"
```

---

## Phase 3: Frontend Integration (Parallel Tasks 6-7)

> **Two frontend-dev subagents can run in parallel.**
> Task 6 (types + client + hook) and Task 7 (UI components) can be split.

### Task 6: Frontend types, API client, and calendar hook updates

**Agent:** `frontend-dev`
**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/hooks/useCalendar.ts`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Update types.ts**

Add to `frontend/src/api/types.ts`:

```typescript
export interface GarminActivityRead {
  id: number
  garmin_activity_id: string
  activity_type: string
  name: string
  start_time: string
  date: string
  duration_sec: number
  distance_m: number
  avg_hr: number | null
  max_hr: number | null
  avg_pace_sec_per_km: number | null
  calories: number | null
}

export interface ScheduledWorkoutWithActivity extends ScheduledWorkout {
  matched_activity_id: number | null
  activity: GarminActivityRead | null
}

export interface CalendarResponse {
  workouts: ScheduledWorkoutWithActivity[]
  unplanned_activities: GarminActivityRead[]
}
```

Update `SyncAllResponse`:
```typescript
export interface SyncAllResponse {
  synced: number
  failed: number
  activities_fetched: number
  activities_matched: number
  fetch_error: string | null
}
```

- [ ] **Step 2: Update client.ts**

```typescript
import type { CalendarResponse, GarminActivityRead, ScheduledWorkoutWithActivity } from './types'

export const fetchCalendarRange = (start: string, end: string) =>
  request<CalendarResponse>(`/calendar?start=${start}&end=${end}`)

export const pairActivity = (workoutId: number, activityId: number) =>
  request<ScheduledWorkoutWithActivity>(`/calendar/${workoutId}/pair/${activityId}`, { method: 'POST' })

export const unpairActivity = (workoutId: number) =>
  request<ScheduledWorkoutWithActivity>(`/calendar/${workoutId}/unpair`, { method: 'POST' })
```

- [ ] **Step 3: Update useCalendar hook**

```typescript
import type { ScheduledWorkoutWithActivity, GarminActivityRead } from '../api/types'

export function useCalendar(initialStart: Date, initialEnd: Date) {
  const [workouts, setWorkouts] = useState<ScheduledWorkoutWithActivity[]>([])
  const [unplannedActivities, setUnplannedActivities] = useState<GarminActivityRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState({ start: initialStart, end: initialEnd })

  // ... loadRange unchanged ...

  useEffect(() => {
    setLoading(true)
    fetchCalendarRange(toDateString(range.start), toDateString(range.end))
      .then((response) => {
        setWorkouts(response.workouts)
        setUnplannedActivities(response.unplanned_activities)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [range.start, range.end])

  // ... schedule, reschedule, remove unchanged (but setWorkouts needs to handle new shape) ...

  const syncAllWorkouts = async () => {
    const result = await syncAll()
    // Refetch calendar after sync
    const updated = await fetchCalendarRange(toDateString(range.start), toDateString(range.end))
    setWorkouts(updated.workouts)
    setUnplannedActivities(updated.unplanned_activities)
    return result
  }

  const pair = async (workoutId: number, activityId: number) => {
    const updated = await pairActivity(workoutId, activityId)
    setWorkouts(prev => prev.map(w => w.id === workoutId ? updated : w))
    setUnplannedActivities(prev => prev.filter(a => a.id !== activityId))
  }

  const unpair = async (workoutId: number) => {
    const updated = await unpairActivity(workoutId)
    setWorkouts(prev => prev.map(w => w.id === workoutId ? updated : w))
    // Activity returns to unplanned — refetch is simplest
    const cal = await fetchCalendarRange(toDateString(range.start), toDateString(range.end))
    setUnplannedActivities(cal.unplanned_activities)
  }

  return {
    workouts, unplannedActivities, loading, error,
    schedule, reschedule, remove, syncAllWorkouts, loadRange,
    pair, unpair,
  }
}
```

- [ ] **Step 4: Add CSS variables to index.css**

In `:root` section:
```css
--color-compliance-green: #10b981;
--color-compliance-yellow: #fbbf24;
--color-compliance-red: #ef4444;
--color-compliance-grey: #6b7280;
```

In `[data-theme="light"]`:
```css
--color-compliance-green: #059669;
--color-compliance-yellow: #d97706;
--color-compliance-red: #dc2626;
--color-compliance-grey: #9ca3af;
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/hooks/useCalendar.ts frontend/src/index.css
git commit -m "feat: update frontend types, API client, and calendar hook for activity fetch"
```

---

### Task 7: WorkoutCard compliance UI + UnplannedActivityCard + CalendarPage

**Agent:** `frontend-dev`
**Files:**
- Modify: `frontend/src/components/calendar/WorkoutCard.tsx`
- Create: `frontend/src/components/calendar/UnplannedActivityCard.tsx`
- Modify: `frontend/src/pages/CalendarPage.tsx`
- Modify: `frontend/src/components/calendar/CalendarView.tsx`

This task depends on Task 6 (types must exist). Run sequentially after Task 6, or merge Task 6 first.

- [ ] **Step 1: Update WorkoutCard with compliance stripe and actual metrics**

Modify `WorkoutCard.tsx` to:
- Accept `ScheduledWorkoutWithActivity` instead of plain `ScheduledWorkout`
- Import and use `computeCompliance`
- Change left stripe to compliance color when activity is matched
- Show actual metrics section below planned metrics when paired
- Add three-dot menu with Reschedule (when not paired) and Unpair (when paired)

Key changes to the component:
- New props: `onReschedule?: (id: number) => void`, `onUnpair?: (id: number) => void`
- Compliance calculation using template's planned duration/distance vs activity actuals
- Muted styling for past-date unmatched cards

- [ ] **Step 2: Create UnplannedActivityCard**

```typescript
// frontend/src/components/calendar/UnplannedActivityCard.tsx
import type { GarminActivityRead } from '../../api/types'
import { formatClock, formatKm } from '../../utils/workoutStats'

interface UnplannedActivityCardProps {
  activity: GarminActivityRead
  onPair?: (activityId: number) => void
}

export function UnplannedActivityCard({ activity, onPair }: UnplannedActivityCardProps) {
  const hasDuration = activity.duration_sec > 0
  const hasDistance = activity.distance_m > 0

  return (
    <div style={{
      display: 'flex', alignItems: 'stretch',
      background: 'var(--card-bg)', borderRadius: '5px',
      border: '1px solid var(--border)', overflow: 'hidden',
      boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
    }} data-testid="unplanned-activity-card">
      {/* Grey stripe */}
      <div style={{ width: '4px', background: 'var(--color-compliance-grey)', flexShrink: 0 }} />

      <div style={{ flex: 1, minWidth: 0, padding: '8px 0 8px 8px' }}>
        <div style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontSize: '14px', fontWeight: 600, letterSpacing: '0.02em',
          color: 'var(--text-primary)', whiteSpace: 'nowrap',
          overflow: 'hidden', textOverflow: 'ellipsis', lineHeight: 1.2,
        }}>
          {activity.name}
        </div>

        {(hasDuration || hasDistance) && (
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px', flexWrap: 'wrap' }}>
            {hasDuration && (
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1,
              }}>
                {formatClock(activity.duration_sec)}
              </span>
            )}
            {hasDistance && (
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', lineHeight: 1,
              }}>
                {formatKm(activity.distance_m)}
              </span>
            )}
          </div>
        )}

        {/* Avg HR + Pace */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '3px' }}>
          {activity.avg_hr != null && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--text-muted)' }}>
              {Math.round(activity.avg_hr)} bpm
            </span>
          )}
          {activity.avg_pace_sec_per_km != null && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--text-muted)' }}>
              {formatClock(Math.round(activity.avg_pace_sec_per_km))}/km
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Update CalendarPage to pass unplanned activities**

Update `CalendarPage.tsx` to destructure `unplannedActivities` from `useCalendar` and pass to `CalendarView`.

Update `CalendarView.tsx` to render `UnplannedActivityCard` components in the appropriate day cells after the scheduled workout cards.

- [ ] **Step 4: Add auto-sync on mount**

In `CalendarPage.tsx`, add a `useEffect` that triggers sync on first mount if Garmin is connected:

```typescript
const [autoSynced, setAutoSynced] = useState(false)

useEffect(() => {
  if (autoSynced) return
  getGarminStatus().then(status => {
    if (status.connected) {
      syncAllWorkouts().catch(() => {})
    }
  }).catch(() => {})
  setAutoSynced(true)
}, [autoSynced])
```

- [ ] **Step 5: Run all frontend tests**

```bash
cd frontend && npx vitest run
```

Fix any TypeScript errors from the `ScheduledWorkout` → `ScheduledWorkoutWithActivity` migration in existing tests.

- [ ] **Step 6: Run build**

```bash
cd frontend && npm run build
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/calendar/ frontend/src/pages/CalendarPage.tsx
git commit -m "feat: add compliance colors, unplanned activity cards, and auto-sync on calendar"
```

---

## Phase 4: Integration & Verification

> **Runs in main session**

### Task 8: End-to-end verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest -v --timeout=30
```

- [ ] **Step 2: Run all frontend tests**

```bash
cd frontend && npx vitest run
```

- [ ] **Step 3: Run frontend build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Verify with Docker Compose (if available)**

```bash
PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" docker compose up --build -d
# Test calendar API returns CalendarResponse shape
curl -s http://localhost:8000/api/v1/calendar?start=2026-03-01\&end=2026-03-31 -H "Authorization: Bearer <token>" | python -m json.tool
```

- [ ] **Step 5: Update STATUS.md**

Move "Garmin Activity Fetch" from "In Progress" to "Completed" section.

- [ ] **Step 6: Final commit**

```bash
git add STATUS.md
git commit -m "docs: mark garmin activity fetch as completed"
```

---

## Parallelism Summary

```
Phase 0: [main session] Documentation + branch setup
  │
Phase 1: ┌─ Task 1: Model + Migration (backend-dev)
          ├─ Task 2: Adapter extraction (backend-dev)
          └─ Task 3: Compliance utility (frontend-dev)
  │
Phase 2: ┌─ Task 4: ActivityFetchService (backend-dev)
          └─ Task 5: API schemas + endpoints (backend-dev) [depends on Task 1]
  │
Phase 3: ┌─ Task 6: Types + client + hook (frontend-dev) [depends on Task 5]
          └─ Task 7: UI components (frontend-dev) [depends on Task 6]
  │
Phase 4: [main session] Integration testing + docs update
```

**Parallel execution windows:**
- Phase 1: 3 agents in parallel (Tasks 1, 2, 3)
- Phase 2: 2 agents in parallel (Tasks 4, 5 — but Task 5 needs Task 1's model)
- Phase 3: Task 6 then Task 7 (sequential — Task 7 needs Task 6's types)
