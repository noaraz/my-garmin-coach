# Calendar-Based Sync Reconciliation — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Sync All to detect workouts missing from the Garmin *calendar* (not just missing templates), and re-schedule them without recreating the template.

**Architecture:** Replace the current template-based reconciliation (`get_workouts()` → compare template IDs) with calendar-based reconciliation (`/calendar-service/year/{year}/month/{month}` → compare `(workoutId, date)` pairs). When a workout template exists but isn't scheduled, just re-schedule it. When the template is also missing, fall through to the existing full push.

**Tech Stack:** FastAPI, garminconnect (raw `connectapi`), SQLModel, pytest

---

## Context & Problem

### What exists today (PR #71)
- `sync_all` fetches Garmin workout **templates** via `get_workouts()` (96 templates returned)
- Reconciliation compares DB `garmin_workout_id` set against template IDs
- If a template is missing → marks workout as `modified` → push loop recreates template + schedules it

### The bug
- Garmin calendar entries can be **unscheduled** (removed from calendar) while the template stays in "My Workouts"
- `get_workouts()` still returns the template → reconciliation sees "all good" → does nothing
- User sees planned workouts in our app but NOT on Garmin calendar

### The fix
- Use `/calendar-service/year/{year}/month/{month}` which returns `{workoutId, date}` for each **scheduled** calendar entry
- Compare against DB's `{garmin_workout_id, scheduled_date}` pairs
- Missing from calendar but template exists → just call `schedule_workout(workoutId, date)` (no re-upload)
- Missing template entirely → existing push flow handles it

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/src/garmin/adapter.py` | Modify | Add `get_calendar_items(year, month)` method |
| `backend/src/garmin/sync_service.py` | Modify | Add `get_calendar_items(year, month)` passthrough |
| `backend/src/services/sync_orchestrator.py` | Modify | Add `get_calendar_items(year, month)` passthrough |
| `backend/src/garmin/dedup.py` | Modify | Replace `find_missing_from_garmin()` with `find_unscheduled_workouts()` |
| `backend/src/api/routers/sync.py` | Modify | Rewrite reconciliation block, add re-schedule path |
| `backend/tests/unit/test_garmin_dedup.py` | Modify | Replace `TestFindMissingFromGarmin` with `TestFindUnscheduledWorkouts` |
| `backend/tests/integration/test_api_sync.py` | Modify | Update 4 reconciliation tests for calendar-based logic |
| `backend/scripts/compare_garmin_workouts.py` | Modify | Add `--calendar` column using calendar endpoint |
| `.claude/skills/garmin-workouts-compare/SKILL.md` | Modify | Document calendar column, update "ONLY DB ✗" meaning |
| `features/garmin-sync/CLAUDE.md` | Modify | Update reconciliation docs |
| `features/garmin-sync/PLAN.md` | Modify | Update reconciliation section |
| Root `CLAUDE.md` | Modify | Update "Garmin Workout Dedup" section, remove "calendar read-back not feasible" note |
| `docs/superpowers/plans/2026-03-30-sync-all-reconciliation.md` | Modify | Add superseded note pointing to this plan |

---

## Chunk 1: Calendar API + Pure Logic

### Task 1: Add `get_calendar_items` to adapter layer

**Files:**
- Modify: `backend/src/garmin/adapter.py`
- Modify: `backend/src/garmin/sync_service.py`
- Modify: `backend/src/services/sync_orchestrator.py`

Following the three-layer propagation pattern (CLAUDE.md: "SyncOrchestrator is the public API").

- [ ] **Step 1: Add method to GarminAdapter**

Add to `backend/src/garmin/adapter.py` after `get_workouts()`:

```python
def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
    """Fetch scheduled calendar items for a given month from Garmin.

    Calls ``/calendar-service/year/{year}/month/{month}`` and returns
    the ``calendarItems`` list.  Each item has at minimum ``workoutId``,
    ``date`` (YYYY-MM-DD), and ``title``.
    """
    path = f"/calendar-service/year/{year}/month/{month}"
    result = self._client.connectapi(path)
    return result.get("calendarItems", []) if isinstance(result, dict) else []
```

- [ ] **Step 2: Add passthrough to GarminSyncService**

Add to `backend/src/garmin/sync_service.py` after `get_workouts()`:

```python
def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
    """Fetch scheduled calendar items for a given month."""
    return self._client.get_calendar_items(year, month)
```

- [ ] **Step 3: Add passthrough to SyncOrchestrator**

Add to `backend/src/services/sync_orchestrator.py` after `get_workouts()`:

```python
def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
    """Fetch scheduled calendar items for a given month."""
    return self._sync_service.get_calendar_items(year, month)
```

- [ ] **Step 4: Commit**

```bash
git add backend/src/garmin/adapter.py backend/src/garmin/sync_service.py backend/src/services/sync_orchestrator.py
git commit -m "feat: add get_calendar_items through adapter → sync_service → orchestrator"
```

### Task 2: Replace `find_missing_from_garmin` with `find_unscheduled_workouts`

**Files:**
- Modify: `backend/src/garmin/dedup.py`
- Modify: `backend/tests/unit/test_garmin_dedup.py`

- [ ] **Step 1: Write failing tests for `find_unscheduled_workouts`**

Replace `TestFindMissingFromGarmin` class in `backend/tests/unit/test_garmin_dedup.py` with:

```python
class TestFindUnscheduledWorkouts:
    """Tests for find_unscheduled_workouts — calendar-based reconciliation."""

    def test_all_scheduled_returns_empty(self):
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
            {"garmin_workout_id": "200", "date": "2026-04-03"},
        ]
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-01"},
            {"workoutId": 200, "date": "2026-04-03"},
        ]
        result = find_unscheduled_workouts(db_workouts, calendar_items)
        assert result == []

    def test_missing_from_calendar_returns_unscheduled(self):
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
            {"garmin_workout_id": "200", "date": "2026-04-03"},
        ]
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-01"},
            # 200 on 2026-04-03 is missing
        ]
        result = find_unscheduled_workouts(db_workouts, calendar_items)
        assert len(result) == 1
        assert result[0]["garmin_workout_id"] == "200"
        assert result[0]["date"] == "2026-04-03"

    def test_different_date_counts_as_unscheduled(self):
        """Same workoutId but different date = not a match."""
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
        ]
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-05"},  # different date
        ]
        result = find_unscheduled_workouts(db_workouts, calendar_items)
        assert len(result) == 1

    def test_empty_calendar_returns_all(self):
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
        ]
        result = find_unscheduled_workouts(db_workouts, [])
        assert len(result) == 1

    def test_empty_db_returns_empty(self):
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-01"},
        ]
        result = find_unscheduled_workouts([], calendar_items)
        assert result == []

    def test_workoutId_string_vs_int_handled(self):
        """Garmin returns workoutId as int, DB stores as string."""
        db_workouts = [
            {"garmin_workout_id": "100", "date": "2026-04-01"},
        ]
        calendar_items = [
            {"workoutId": 100, "date": "2026-04-01"},
        ]
        result = find_unscheduled_workouts(db_workouts, calendar_items)
        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/unit/test_garmin_dedup.py::TestFindUnscheduledWorkouts -v --no-cov`

Expected: FAIL with `ImportError` or `cannot import name 'find_unscheduled_workouts'`

- [ ] **Step 3: Implement `find_unscheduled_workouts` in dedup.py**

Replace `find_missing_from_garmin` with:

```python
def find_unscheduled_workouts(
    db_workouts: list[dict[str, str]],
    calendar_items: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Return DB workouts not scheduled on the Garmin calendar.

    Compares ``(garmin_workout_id, date)`` pairs from our DB against
    ``(workoutId, date)`` pairs from the Garmin calendar endpoint.
    A workout is "unscheduled" if its (ID, date) pair is not on the calendar.

    Args:
        db_workouts: List of dicts with ``garmin_workout_id`` (str) and
            ``date`` (str YYYY-MM-DD) from ScheduledWorkouts with
            sync_status="synced".
        calendar_items: Raw list from Garmin
            ``/calendar-service/year/{y}/month/{m}`` ``calendarItems``.

    Returns:
        Subset of *db_workouts* not found on the Garmin calendar.
    """
    # Build set of (workoutId_str, date) from Garmin calendar
    scheduled: set[tuple[str, str]] = set()
    for item in calendar_items:
        wid = str(item.get("workoutId", ""))
        date = item.get("date", "")
        if wid and date:
            scheduled.add((wid, date))

    return [
        w for w in db_workouts
        if (w["garmin_workout_id"], w["date"]) not in scheduled
    ]
```

Keep the old `find_missing_from_garmin` for now (other callers may use it). It will be removed in Task 5 cleanup.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/unit/test_garmin_dedup.py -v --no-cov`

Expected: All pass (both old and new tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/garmin/dedup.py backend/tests/unit/test_garmin_dedup.py
git commit -m "feat: add find_unscheduled_workouts for calendar-based reconciliation"
```

---

## Chunk 2: Rewrite sync_all Reconciliation

### Task 3: Rewrite reconciliation block in sync_all

**Files:**
- Modify: `backend/src/api/routers/sync.py` (~lines 555-601)

The new reconciliation:
1. Fetches Garmin calendar items for the months covering the sync window
2. Compares `(garmin_workout_id, date)` pairs against DB
3. For unscheduled workouts where template still exists on Garmin → call `reschedule_workout` (already exists on SyncOrchestrator)
4. For unscheduled workouts where template is also gone → mark as `modified` for full re-push

- [ ] **Step 1: Replace the reconciliation block**

In `backend/src/api/routers/sync.py`, replace the block from `# ── Reconciliation` through `reconciled,` / `current_user.id,` / `)` (the whole reconciliation section) with:

```python
    # ── Reconciliation: detect synced workouts not on Garmin calendar ─────
    reconciled = 0
    rescheduled = 0
    garmin_id_set = {str(gw.get("workoutId", "")) for gw in garmin_workouts} if garmin_workouts else set()

    # Fetch Garmin calendar entries for the months we care about.
    # Cover from today through the furthest scheduled workout date.
    calendar_items: list[dict[str, Any]] = []
    try:
        synced_with_ids = (
            await session.exec(
                select(ScheduledWorkout).where(
                    ScheduledWorkout.user_id == current_user.id,
                    ScheduledWorkout.sync_status == "synced",
                    ScheduledWorkout.completed == False,  # noqa: E712
                    ScheduledWorkout.garmin_workout_id.is_not(None),  # type: ignore[union-attr]
                )
            )
        ).all()

        if synced_with_ids:
            # Determine which months to fetch from Garmin calendar
            dates = [sw.date for sw in synced_with_ids if sw.date]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                months_to_fetch: set[tuple[int, int]] = set()
                current = min_date.replace(day=1)
                while current <= max_date:
                    months_to_fetch.add((current.year, current.month))
                    # Advance to next month
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)

                for year, month in months_to_fetch:
                    try:
                        items = sync_service.get_calendar_items(year, month)
                        calendar_items.extend(items)
                    except Exception as cal_exc:  # noqa: BLE001
                        logger.warning(
                            "Could not fetch Garmin calendar for %d-%02d: %s",
                            year, month, type(cal_exc).__name__,
                        )

                logger.info(
                    "Fetched %d Garmin calendar items across %d months for user %s",
                    len(calendar_items),
                    len(months_to_fetch),
                    current_user.id,
                )

                # Find workouts in our DB that are NOT on the Garmin calendar
                from src.garmin.dedup import find_unscheduled_workouts

                db_workouts_for_check = [
                    {"garmin_workout_id": sw.garmin_workout_id, "date": str(sw.date)}
                    for sw in synced_with_ids
                    if sw.garmin_workout_id and sw.date
                ]
                unscheduled = find_unscheduled_workouts(db_workouts_for_check, calendar_items)

                if unscheduled:
                    unscheduled_ids = {u["garmin_workout_id"] for u in unscheduled}
                    for sw in synced_with_ids:
                        if sw.garmin_workout_id in unscheduled_ids:
                            # Template still on Garmin? → Just re-schedule (cheap)
                            if sw.garmin_workout_id in garmin_id_set:
                                try:
                                    sync_service.reschedule_workout(
                                        sw.garmin_workout_id, str(sw.date)
                                    )
                                    rescheduled += 1
                                    logger.info(
                                        "Re-scheduled workout %s on %s (template existed)",
                                        sw.garmin_workout_id,
                                        sw.date,
                                    )
                                except Exception as sched_exc:  # noqa: BLE001
                                    logger.warning(
                                        "Re-schedule failed for %s: %s — falling back to full re-push",
                                        sw.garmin_workout_id,
                                        type(sched_exc).__name__,
                                    )
                                    sw.sync_status = "modified"
                                    sw.garmin_workout_id = None
                                    session.add(sw)
                                    reconciled += 1
                            else:
                                # Template also gone → full re-push
                                sw.sync_status = "modified"
                                sw.garmin_workout_id = None
                                session.add(sw)
                                reconciled += 1

                    if rescheduled or reconciled:
                        await session.commit()
                        logger.info(
                            "Reconciliation for user %s: %d re-scheduled, %d queued for re-push",
                            current_user.id,
                            rescheduled,
                            reconciled,
                        )
    except Exception as recon_exc:  # noqa: BLE001
        logger.warning("Reconciliation failed (continuing): %s", type(recon_exc).__name__)
```

- [ ] **Step 2: Update SyncAllResponse to include `rescheduled`**

In the same file, update the response model:

```python
class SyncAllResponse(BaseModel):
    synced: int = 0
    failed: int = 0
    reconciled: int = 0
    rescheduled: int = 0  # NEW: re-scheduled (template existed, just missing from calendar)
    activities_fetched: int = 0
    activities_matched: int = 0
    fetch_error: str | None = None
```

And update the return statement at the end of `sync_all` to include `rescheduled=rescheduled`.

- [ ] **Step 3: Update frontend type**

In `frontend/src/api/types.ts`, add `rescheduled: number` to `SyncAllResponse`.

- [ ] **Step 4: Commit**

```bash
git add backend/src/api/routers/sync.py frontend/src/api/types.ts
git commit -m "feat: calendar-based reconciliation with re-schedule path"
```

### Task 4: Update integration tests

**Files:**
- Modify: `backend/tests/integration/test_api_sync.py`

- [ ] **Step 1: Update reconciliation tests**

Replace the 4 existing reconciliation tests with calendar-based variants. Key changes:
- Mock `mock_sync_service.get_calendar_items.return_value` instead of relying on `get_workouts` for reconciliation
- Test the re-schedule path (template exists, just missing from calendar)
- Test the full re-push fallback (template also gone)
- Test that completed workouts are still skipped

Tests to write:

```python
class TestSyncAllCalendarReconciliation:
    """Calendar-based reconciliation tests."""

    async def test_sync_all_reschedules_when_template_exists_but_not_on_calendar(self, ...):
        """Workout template on Garmin but not scheduled → re-schedule only."""
        # Setup: synced workout with garmin_workout_id, completed=False
        # Mock: get_workouts returns the template, get_calendar_items returns empty
        # Assert: reschedule_workout called, rescheduled=1, sync_status stays "synced"

    async def test_sync_all_repushes_when_template_also_missing(self, ...):
        """Template gone + not on calendar → full re-push."""
        # Setup: synced workout with garmin_workout_id
        # Mock: get_workouts returns empty, get_calendar_items returns empty
        # Assert: reconciled=1, sync_status="modified", garmin_workout_id=None

    async def test_sync_all_no_reconciliation_when_on_calendar(self, ...):
        """Workout on Garmin calendar → no action."""
        # Mock: get_calendar_items returns matching (workoutId, date) pair
        # Assert: rescheduled=0, reconciled=0

    async def test_sync_all_reconciliation_skips_completed(self, ...):
        """Completed workouts are excluded from reconciliation."""
        # Setup: completed=True workout
        # Assert: not checked, rescheduled=0, reconciled=0
```

- [ ] **Step 2: Run integration tests**

Run: `cd backend && .venv/bin/pytest tests/integration/test_api_sync.py -v --no-cov -k reconcil`

Expected: All 4 pass

- [ ] **Step 3: Verify existing tests still pass**

Run: `cd backend && .venv/bin/pytest tests/integration/test_api_sync.py -v --no-cov`

Expected: All pass (update any existing tests that relied on old reconciliation mocks)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/test_api_sync.py
git commit -m "test: update sync_all reconciliation tests for calendar-based logic"
```

---

## Chunk 3: Update Compare Script + Cleanup

### Task 5: Update compare script to use calendar endpoint

**Files:**
- Modify: `backend/scripts/compare_garmin_workouts.py`

- [ ] **Step 1: Add calendar column to compare output**

The script currently only checks templates via `get_workouts()`. Add a "Scheduled" column that shows whether each workout is on the Garmin calendar for its date.

Changes:
- Fetch calendar items for the relevant months (same logic as sync_all)
- Build `scheduled_set: set[tuple[str, str]]` of `(workoutId, date)` pairs
- For each DB workout: check if `(garmin_workout_id, date)` is in `scheduled_set`
- New "Where" categories:
  - `BOTH ✓ + CAL ✓` — template exists AND on calendar (fully synced)
  - `BOTH ✓ + CAL ✗` — template exists but NOT on calendar (**the bug this PR fixes**)
  - `ONLY DB ✗` — template missing (existing category)
  - `ONLY DB (pending)` — not yet synced (existing)
  - `ONLY GARMIN` — orphan (existing)

- [ ] **Step 2: Update script docstring**

Add note about the calendar column and what `CAL ✗` means.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/compare_garmin_workouts.py
git commit -m "feat: add calendar column to compare script"
```

### Task 6: Remove `find_missing_from_garmin` and old tests

**Files:**
- Modify: `backend/src/garmin/dedup.py` — remove `find_missing_from_garmin()`
- Modify: `backend/tests/unit/test_garmin_dedup.py` — remove `TestFindMissingFromGarmin` class
- Modify: `backend/src/api/routers/sync.py` — remove the old import if still present

- [ ] **Step 1: Remove the function and its tests**

Delete `find_missing_from_garmin` from `dedup.py` and `TestFindMissingFromGarmin` from the test file.

- [ ] **Step 2: Grep for any remaining references**

```bash
cd backend && grep -r "find_missing_from_garmin" src/ tests/
```

Expected: No results

- [ ] **Step 3: Run all tests**

```bash
cd backend && .venv/bin/pytest tests/ -v --no-cov
```

Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add backend/src/garmin/dedup.py backend/tests/unit/test_garmin_dedup.py
git commit -m "refactor: remove find_missing_from_garmin (replaced by calendar-based reconciliation)"
```

---

## Chunk 4: Documentation Updates

### Task 7: Update all documentation

**Files:**
- Modify: Root `CLAUDE.md` — "Garmin Workout Dedup" section
- Modify: `features/garmin-sync/CLAUDE.md` — "Sync-All Reconciliation" section
- Modify: `features/garmin-sync/PLAN.md` — reconciliation subsection
- Modify: `.claude/skills/garmin-workouts-compare/SKILL.md` — output table, "ONLY DB ✗" meaning
- Modify: `docs/superpowers/plans/2026-03-30-sync-all-reconciliation.md` — add superseded note

- [ ] **Step 1: Update root CLAUDE.md**

In the "Garmin Workout Dedup" section:
- Replace the `sync_all reconciliation` bullet to mention calendar-based approach
- **Remove** the note "Garmin calendar read-back not feasible" — it referred to `GET /workout-service/schedule/{id}` which is a different endpoint. `/calendar-service/year/{y}/month/{m}` works.
- Add: `sync_all reconciliation` uses `/calendar-service/year/{y}/month/{m}` to detect workouts missing from the Garmin calendar. Templates still on Garmin → re-scheduled (cheap). Templates gone → full re-push.

- [ ] **Step 2: Update features/garmin-sync/CLAUDE.md**

Replace "Sync-All Reconciliation" section with calendar-based description. Key points:
- Endpoint: `/calendar-service/year/{year}/month/{month}`
- Returns `calendarItems` list with `{workoutId, date, title}`
- Reconciliation compares `(workoutId, date)` pairs not just template IDs
- Two paths: re-schedule (template exists) vs full re-push (template gone)
- `get_workouts()` still used for dedup before first push + orphan cleanup (unchanged)

- [ ] **Step 3: Update features/garmin-sync/PLAN.md**

Check boxes for reconciliation tasks and note the calendar-based approach.

- [ ] **Step 4: Update compare skill**

In `.claude/skills/garmin-workouts-compare/SKILL.md`:
- Update output table to include `CAL ✓` / `CAL ✗` columns
- Update "ONLY DB ✗" description
- Add `BOTH ✓ + CAL ✗` row — template exists but not scheduled

- [ ] **Step 5: Add superseded note to old plan**

In `docs/superpowers/plans/2026-03-30-sync-all-reconciliation.md`, add at the top:

```markdown
> **SUPERSEDED** by [2026-03-31-calendar-based-reconciliation.md](2026-03-31-calendar-based-reconciliation.md).
> The template-based approach was insufficient — templates can exist on Garmin without being
> scheduled on the calendar.
```

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md features/garmin-sync/CLAUDE.md features/garmin-sync/PLAN.md \
  .claude/skills/garmin-workouts-compare/SKILL.md \
  docs/superpowers/plans/2026-03-30-sync-all-reconciliation.md
git commit -m "docs: update all docs for calendar-based reconciliation"
```
