# Smart Plan Merge — Design Spec

**Date:** 2026-03-20
**Feature:** Plan Coach — Smart Update (consider current plan on re-import)
**Status:** Approved

---

## Problem

`commit_plan` currently does a full replacement: delete all scheduled workouts from the old plan, recreate all from the new CSV. This causes:

- Unchanged workouts get deleted and re-pushed to Garmin unnecessarily (wasted API calls, visible churn on the watch).
- Completed workouts (paired with a Garmin activity) get deleted, losing the link.
- The diff shown at validate time is informational only — commit ignores it.

---

## Goal

When re-importing a plan over an existing one, commit should:

1. **Keep unchanged workouts** — same date, name, and steps; preserve DB row and Garmin sync state.
2. **Replace changed workouts** — delete old row (with Garmin cleanup), create new row.
3. **Lock completed workouts** — workouts with `matched_activity_id IS NOT NULL` are never touched, regardless of whether they appear in the new plan or are changed.
4. **Add new workouts** — dates in incoming but not in the active plan.
5. **Remove gone workouts** — dates in active plan but not in incoming, skipping completed ones.

The validate response shows all 5 statuses so the user can preview the exact effect before committing.

---

## API Schema Changes

### `WorkoutDiff`

```python
class WorkoutDiff(BaseModel):
    date: str
    name: str            # new name; for removed/unchanged/locked = current name
    old_name: str | None = None        # populated for "changed" only
    old_steps_spec: str | None = None  # populated for "changed" only
    new_steps_spec: str | None = None  # populated for "changed" only
```

### `DiffResult`

```python
class DiffResult(BaseModel):
    added: list[WorkoutDiff]
    removed: list[WorkoutDiff]
    changed: list[WorkoutDiff]
    unchanged: list[WorkoutDiff]        # kept as-is
    completed_locked: list[WorkoutDiff] # not touched (activity already paired)
```

---

## Backend Changes

### `plan_import_service.py` — `_compute_diff`

New signature:

```python
def _compute_diff(
    incoming: list[ParsedWorkout],
    active_parsed: list[dict],
    completed_dates: set[str],
) -> DiffResult
```

Logic:

- For each incoming workout by date:
  - If date in `completed_dates` → `completed_locked`
  - Else if date in active and same name + steps_spec → `unchanged`
  - Else if date in active but different → `changed` (populate `old_name`, `old_steps_spec`, `new_steps_spec`)
  - Else → `added`
- For each active date not in incoming:
  - If in `completed_dates` → omit (stays in DB, not in diff)
  - Else → `removed`

### `plan_import_service.py` — `validate_plan`

After fetching the active plan, one extra query to get completed dates (batch, no N+1):

```python
completed_result = await session.exec(
    select(ScheduledWorkout.date).where(
        ScheduledWorkout.training_plan_id == active.id,
        ScheduledWorkout.matched_activity_id.isnot(None),
    )
)
completed_dates = {str(row) for row in completed_result.all()}
diff = _compute_diff(parsed_list, active_parsed, completed_dates)
```

### `plans.py` — `post_commit` (smart merge, replaces `commit_plan` delete-all logic)

The smart merge runs **in the router** before calling `commit_plan`, because it needs access to the Garmin service. `commit_plan` in the service layer is updated to accept an `ids_to_skip` set so it does not delete rows that should be kept.

**Alternative (preferred):** move the smart merge fully into `commit_plan` with an optional `garmin` parameter passed in — keeps router thin. The router passes `garmin` to `commit_plan`; service does the full merge.

Steps in `commit_plan`:

1. **Batch-load existing SWs** — one query: `SELECT * FROM scheduledworkout WHERE training_plan_id = active.id`
2. **Batch-load their templates** — one query: `SELECT * FROM workouttemplate WHERE id IN (...)`
3. **Batch-load active plan's parsed_workouts** — already in `active.parsed_workouts` JSON
4. **Classify** each incoming workout using `completed_dates` + name/steps comparison:
   - `completed_locked` or `unchanged` → skip (keep existing SW row)
   - `changed` → add to `ids_to_delete`, add to `sws_to_create`
   - `added` → add to `sws_to_create`
5. **Classify removed** — active dates not in incoming, not completed → add to `ids_to_delete`
6. **Garmin cleanup** — loop `garmin_ids_to_delete` (one API call per, unavoidable)
7. **Bulk delete** — `DELETE WHERE id IN (ids_to_delete)` — single statement
8. **Batch add** — `session.add()` for each new SW, single `session.commit()`

### Neon Optimisation Notes

- No N+1 queries: all SWs and templates loaded in two queries, looked up from dicts.
- Bulk delete via `sqlalchemy.delete(...).where(id.in_(...))` — not fetch-then-delete.
- Single `session.commit()` after all mutations.
- No `session.get()` inside loops.
- `completed_dates` loaded in a single filtered query (not loaded as full ORM objects — only the `date` column).

---

## Frontend Changes

### `types.ts`

```typescript
export interface WorkoutDiff {
  date: string
  name: string
  old_name?: string
  old_steps_spec?: string
  new_steps_spec?: string
}

export interface DiffResult {
  added: WorkoutDiff[]
  removed: WorkoutDiff[]
  changed: WorkoutDiff[]
  unchanged: WorkoutDiff[]        // new
  completed_locked: WorkoutDiff[] // new
}
```

### `DiffTable.tsx`

Add two new row variants:

| Status | Symbol | Color | Description |
|--------|--------|-------|-------------|
| `added` | `+` | green | New workout |
| `removed` | `−` | red | Removed |
| `changed` | `~` | amber | Before→after (expand row to show old/new steps_spec) |
| `unchanged` | `=` | gray/muted | Kept as-is, no action |
| `completed_locked` | `⊘` | gray/muted | Already done, not touched |

**Changed row** renders two lines:
```
~  2026-04-07   Easy Run  →  Long Easy Run
                15m@Z1 + 30m@Z2 → 20m@Z1 + 40m@Z2
```

**Header summary** shows all counts:
```
+2 added  −1 removed  ~3 changed  =12 unchanged  ⊘2 locked
```
Only adds badges for non-zero counts.

### `CsvImportTab.tsx`

`hasDiff` check is unchanged — only `added + removed + changed > 0` drives the "Apply Changes" label. `unchanged` and `completed_locked` are informational.

---

## What Does NOT Change

- `delete_plan` endpoint — already handles Garmin cleanup correctly.
- `validate_plan` return shape — `ValidateResult` is unchanged; only `DiffResult` is extended.
- `ValidationTable` — no changes.
- Template reuse logic in `commit_plan` — templates are still reused/created by name.
- Sync/re-sync flow — unchanged workouts keep their `garmin_workout_id` and `sync_status`.

---

## Testing

### Backend (pytest)

| Test | Description |
|------|-------------|
| `test_compute_diff_unchanged_when_same` | Same name + steps → `unchanged` bucket |
| `test_compute_diff_completed_locked` | Completed date → `completed_locked` regardless of steps change |
| `test_compute_diff_changed_populates_before_after` | Changed row has `old_name`, `old_steps_spec`, `new_steps_spec` |
| `test_commit_plan_keeps_unchanged_sw_row` | Unchanged SW row is not deleted or recreated |
| `test_commit_plan_skips_completed_sw` | Completed SW is not touched even if "changed" |
| `test_commit_plan_bulk_delete_changed` | Changed SW is deleted and new one created |
| `test_commit_plan_no_n_plus_one` | Assert query count ≤ N (use `sqlalchemy` event listener) |

### Frontend (Vitest)

| Test | Description |
|------|-------------|
| `DiffTable renders unchanged rows` | Gray `=` rows appear for `unchanged` |
| `DiffTable renders completed_locked rows` | Gray `⊘` rows appear for `completed_locked` |
| `DiffTable shows before/after for changed` | Old and new steps_spec both visible |
| `DiffTable header shows all counts` | All 5 counts shown when non-zero |
| `hasDiff ignores unchanged and completed_locked` | Import button label unaffected |
