# Design: Preserve Past Workouts on Plan Update

**Date:** 2026-04-12
**Status:** Approved

---

## Context

When a user re-imports a training plan CSV, the smart merge compares the new CSV against the active plan. Workouts in the active plan that are absent from the new CSV are classified as `removed` and deleted. This classification has no date awareness — even workouts whose date has already passed get deleted.

This causes a data loss problem: importing a shorter/revised plan (e.g. a 6-workout CSV for the next two weeks) wipes out all training history from the previous months. The diff screen shows these as red "−" removals, misleading the user into thinking 47 workouts are being destructively dropped when most are past history.

---

## Goal

Workouts with `date < today` that are absent from the new CSV must be preserved — never deleted — during a plan update. The diff UI must clearly distinguish past-preserved workouts from genuinely dropped future workouts.

---

## Solution: `past_locked` Bucket

Add a sixth diff classification: `past_locked`. Any workout in the active plan, absent from the new plan, and with `date < today` goes into `past_locked` instead of `removed`. These workouts are re-associated to the new plan and never deleted.

**Priority rule:** `completed_locked` takes precedence over `past_locked`. A workout that is both past and has a matched activity is classified as `completed_locked`. The `past_locked` check only applies when `date_str not in completed_dates`.

---

## Backend Changes

### `DiffResult` Pydantic model (`backend/src/services/plan_import_service.py`)

```python
class DiffResult(BaseModel):
    added: list[WorkoutDiff]
    removed: list[WorkoutDiff]
    changed: list[WorkoutDiff]
    unchanged: list[WorkoutDiff] = []
    completed_locked: list[WorkoutDiff] = []
    past_locked: list[WorkoutDiff] = []   # NEW
```

### `_compute_diff()` (`backend/src/services/plan_import_service.py`)

`_compute_diff` iterates `active_by_date.items()` where values are plain dicts (not ORM objects). The date comparison must parse the date string:

```python
today = datetime.now(timezone.utc).date()  # date_type already imported at module scope

# Inside the "not in incoming_dates" branch:
if date_str not in incoming_dates:
    if date_str in completed_dates:
        result.completed_locked.append(WorkoutDiff(date=date_str, name=pw["name"]))
    elif date_type.fromisoformat(date_str) < today:   # NEW — past_locked check
        result.past_locked.append(WorkoutDiff(date=date_str, name=pw["name"]))
    else:
        result.removed.append(WorkoutDiff(date=date_str, name=pw["name"]))
```

No new import needed — `date_type` is already imported at module scope (`from datetime import date as date_type, datetime, timedelta, timezone`).

### `commit_plan()` (`backend/src/services/plan_import_service.py`)

`commit_plan` does NOT receive a `diff` object — it re-derives its own classification from scratch. The `past_locked` check must be inserted into the existing "Removed" for-loop (currently around lines 421–425). `completed_dates` is already checked before this loop runs, so the priority is preserved:

```python
today = datetime.now(timezone.utc).date()

# Current "Removed" loop — becomes:
for date_str, sw in sw_by_date.items():
    if date_str not in incoming_dates and date_str not in completed_dates:
        if date_type.fromisoformat(date_str) < today:   # NEW — past_locked
            kept_sw_ids.append(sw.id)   # re-associate to new plan, never delete
        else:
            ids_to_delete.append(sw.id)
            if sw.garmin_workout_id:
                garmin_ids_to_delete.append(sw.garmin_workout_id)
```

---

## Frontend Changes

### `frontend/src/api/types.ts`

```typescript
export interface DiffResult {
  added: WorkoutDiff[]
  removed: WorkoutDiff[]
  changed: WorkoutDiff[]
  unchanged: WorkoutDiff[]
  completed_locked: WorkoutDiff[]
  past_locked?: WorkoutDiff[]   // NEW — optional for backward compat
}
```

### `frontend/src/components/plan-coach/DiffTable.tsx`

**1. Add `past_locked` to `RowKind` and `ROW_CONFIG`:**

```typescript
type RowKind = 'added' | 'removed' | 'changed' | 'unchanged' | 'completed_locked' | 'past_locked'

const ROW_CONFIG: Record<RowKind, { symbol: string; color: string; bgVar: string }> = {
  // ... existing entries ...
  past_locked: { symbol: '↩', color: 'var(--text-muted)', bgVar: 'transparent' },
}
```

**2. Update `isLocked` in `DiffRow`:**

The existing `isLocked` flag drives the `(kept)` inline label. Extend it to cover `past_locked`:

```typescript
const isLocked = kind === 'completed_locked' || kind === 'past_locked'
```

**3. Update summary header:**

```typescript
const totalPastLocked = (diff.past_locked ?? []).length
```

Show `↩N past (kept)` in muted style, separate from the red removed count:
```
−7 removed   ↩40 past (kept)
```

**4. `hasActionable` — `past_locked`-only diffs:**

`past_locked` is NOT included in `hasActionable`. However, if the only diff entries are `past_locked` (no added/removed/changed), the table would be suppressed entirely. To handle this, include `past_locked` in the render gate:

```typescript
const hasActionable = totalAdded + totalRemoved + totalChanged > 0
const hasPastLocked = totalPastLocked > 0
// Render if either has content:
if (!hasActionable && !hasPastLocked) return null
```

---

## What Is NOT Changing

- Past workouts that ARE in the new CSV behave normally (`unchanged` or `changed`)
- `completed_locked` logic is unchanged — it takes priority over `past_locked`
- Garmin sync state of past workouts is untouched
- No DB migration needed

---

## Tests

**Backend** (`backend/tests/unit/test_plan_import_service.py` — extend existing file):
- `test_compute_diff_past_workout_not_in_new_plan_goes_to_past_locked`
- `test_compute_diff_future_workout_not_in_new_plan_goes_to_removed`
- `test_compute_diff_past_and_completed_workout_goes_to_completed_locked` (priority rule)
- `test_commit_plan_preserves_past_workouts_not_in_new_plan`

**Frontend** (`frontend/src/components/plan-coach/DiffTable.test.tsx` — new file):
- Renders `past_locked` rows with `↩` symbol and muted color
- Summary header shows `↩N past (kept)` and excludes past_locked from removed count
- Table renders when only `past_locked` rows exist (no added/removed/changed)
