> **Superseded** by `docs/superpowers/plans/2026-03-31-calendar-based-reconciliation.md`.
> This plan implemented template-list-based reconciliation (`find_missing_from_garmin()`).
> It was replaced by calendar-based reconciliation (`find_unscheduled_workouts()`) which
> uses `GET /calendar-service/year/{year}/month/{month}` to compare `(workoutId, date)` pairs
> and supports two paths: reschedule (cheap) vs full re-push.

# Sync-All Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `sync_all` runs, detect workouts marked "synced" in our DB whose Garmin workout no longer exists on Garmin Connect, and re-queue them for push — so one Sync All fixes everything without force-syncing each workout individually.

**Architecture:** Add a pure `find_missing_from_garmin()` function in `dedup.py`. In `sync_all`, after fetching `garmin_workouts` (line 518) and before the push loop (line 548), query all synced+incomplete workouts, cross-reference against the Garmin list, mark missing ones as `modified` with cleared `garmin_workout_id`, and log the count. Zero additional Garmin API calls — the workout list is already fetched. Add `reconciled` count to `SyncAllResponse` and frontend `SyncAllResponse` type.

**Tech Stack:** Python, SQLModel, FastAPI, pytest

---

## Chunk 1: Phase 0 — Docs Update

### Task 0: Update docs before code

**Files:**
- Modify: `STATUS.md`
- Modify: `CLAUDE.md`
- Modify: `features/garmin-sync/CLAUDE.md`
- Modify: `features/garmin-sync/PLAN.md`
- Commit: `.claude/skills/garmin-workouts-compare/SKILL.md` (already updated with prod DB instructions)
- Commit: `backend/scripts/compare_garmin_workouts.py` (already updated)

- [ ] **Step 1: Update STATUS.md**

Add under "In Progress":
```
- fix: sync_all reconciliation — detect synced workouts missing from Garmin and re-push
```

- [ ] **Step 2: Update root CLAUDE.md**

In the "Garmin Workout Dedup" section, add:
```
- **sync_all reconciliation**: After fetching `garmin_workouts`, queries all `sync_status="synced"` + `garmin_workout_id IS NOT NULL` + `completed=False` workouts. Cross-references against the Garmin list via `find_missing_from_garmin()`. Missing ones get `sync_status="modified"` + `garmin_workout_id=None` — picked up by the existing push loop. Logged as `"Reconciliation: N workouts missing from Garmin — re-queuing"`.
```

- [ ] **Step 3: Update features/garmin-sync/CLAUDE.md**

Add a "Sync-All Reconciliation" section documenting:
- The reconciliation step placement (after `get_workouts()`, before push loop)
- The pure function `find_missing_from_garmin()` in `dedup.py`
- The `reconciled` count in `SyncAllResponse`
- Guard: only runs when `garmin_workouts is not None`
- Completed workouts are excluded (they don't need re-push)

- [ ] **Step 4: Update features/garmin-sync/PLAN.md**

Add after the "Auto-Reconnect + Exchange 429 Fix" section (line ~153):
```markdown
### Sync-All Reconciliation (2026-03-31)
- [ ] `find_missing_from_garmin()` in `dedup.py` — pure function, TDD
- [ ] `reconciled` field in `SyncAllResponse` + frontend `types.ts`
- [ ] Reconciliation block in `sync_all` between garmin fetch and push loop
- [ ] 4 integration tests in `test_api_sync.py`

**Plan**: `docs/superpowers/plans/2026-03-30-sync-all-reconciliation.md`
```

- [ ] **Step 5: Commit docs + skill + script**

```bash
git add STATUS.md CLAUDE.md features/garmin-sync/CLAUDE.md features/garmin-sync/PLAN.md \
  .claude/skills/garmin-workouts-compare/SKILL.md backend/scripts/compare_garmin_workouts.py
git commit -m "docs: add sync-all reconciliation to STATUS + CLAUDE.md + feature docs + update compare skill"
```

---

## Chunk 2: Pure dedup function + unit tests (TDD)

### Task 1: Write failing unit test for `find_missing_from_garmin`

**Files:**
- Modify: `backend/tests/unit/test_garmin_dedup.py` (append new test class — file already exists with `TestFindMatchingGarminWorkout` and `TestFindOrphanedGarminWorkouts`)

- [ ] **Step 1: Write the failing tests**

Add to the existing `backend/tests/unit/test_garmin_dedup.py`, updating the import and appending a new class:

Update import at line 4:
```python
from src.garmin.dedup import find_matching_garmin_workout, find_missing_from_garmin, find_orphaned_garmin_workouts
```

Append after `TestFindOrphanedGarminWorkouts` class (after line 112):

```python
class TestFindMissingFromGarmin:
    def test_returns_ids_not_on_garmin(self) -> None:
        """DB IDs not found in Garmin workout list are returned."""
        garmin_workouts = [
            {"workoutId": "aaa", "workoutName": "Run 1"},
            {"workoutId": "bbb", "workoutName": "Run 2"},
        ]
        db_garmin_ids = {"aaa", "bbb", "ccc", "ddd"}

        result = find_missing_from_garmin(db_garmin_ids, garmin_workouts)

        assert result == {"ccc", "ddd"}

    def test_returns_empty_when_all_present(self) -> None:
        """When every DB ID exists on Garmin, nothing is missing."""
        garmin_workouts = [
            {"workoutId": "aaa", "workoutName": "Run 1"},
            {"workoutId": "bbb", "workoutName": "Run 2"},
        ]
        db_garmin_ids = {"aaa", "bbb"}

        result = find_missing_from_garmin(db_garmin_ids, garmin_workouts)

        assert result == set()

    def test_returns_all_when_garmin_list_empty(self) -> None:
        """When Garmin has no workouts, all DB IDs are missing."""
        db_garmin_ids = {"aaa", "bbb"}

        result = find_missing_from_garmin(db_garmin_ids, [])

        assert result == {"aaa", "bbb"}

    def test_returns_empty_when_db_ids_empty(self) -> None:
        """When DB has no synced IDs, nothing is missing."""
        garmin_workouts = [{"workoutId": "aaa", "workoutName": "Run 1"}]

        result = find_missing_from_garmin(set(), garmin_workouts)

        assert result == set()

    def test_coerces_workout_id_to_string(self) -> None:
        """Garmin workoutId may be int — must compare as string."""
        garmin_workouts = [{"workoutId": 12345, "workoutName": "Run"}]
        db_garmin_ids = {"12345", "99999"}

        result = find_missing_from_garmin(db_garmin_ids, garmin_workouts)

        assert result == {"99999"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/unit/test_garmin_dedup.py::TestFindMissingFromGarmin -v --no-cov
```

Expected: `ImportError` — `find_missing_from_garmin` does not exist yet.

### Task 2: Implement `find_missing_from_garmin`

**Files:**
- Modify: `backend/src/garmin/dedup.py` (append after `find_orphaned_garmin_workouts`, line 59)

- [ ] **Step 3: Write minimal implementation**

Add at the end of `dedup.py`:

```python
def find_missing_from_garmin(
    db_garmin_ids: set[str],
    garmin_workouts: list[dict[str, Any]],
) -> set[str]:
    """Return DB garmin_workout_ids that no longer exist on Garmin.

    Compares the set of IDs our DB thinks are synced against the actual
    Garmin workout list.  Any DB ID not found on Garmin is returned —
    these workouts were externally deleted and need re-pushing.

    Args:
        db_garmin_ids: Set of garmin_workout_id values from ScheduledWorkouts
            with sync_status="synced".
        garmin_workouts: Raw list from Garmin ``get_workouts()`` API.

    Returns:
        Set of garmin_workout_id strings missing from Garmin.
    """
    garmin_ids = {str(gw.get("workoutId", "")) for gw in garmin_workouts}
    return db_garmin_ids - garmin_ids
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/unit/test_garmin_dedup.py -v --no-cov
```

Expected: all tests PASS (existing 12 + new 5 = 17 total).

- [ ] **Step 5: Run ruff**

```bash
ruff check backend/src/garmin/dedup.py backend/tests/unit/test_garmin_dedup.py
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/garmin/dedup.py backend/tests/unit/test_garmin_dedup.py
git commit -m "feat: add find_missing_from_garmin to dedup module (TDD)"
```

---

## Chunk 3: Add `reconciled` field to response models (backend + frontend)

### Task 3: Extend backend response model + frontend type

**Files:**
- Modify: `backend/src/api/routers/sync.py:291-296` (SyncAllResponse)
- Modify: `frontend/src/api/types.ts:120-126` (SyncAllResponse interface)

- [ ] **Step 1: Add field to backend SyncAllResponse**

In `backend/src/api/routers/sync.py`, change `SyncAllResponse` (line 291):

```python
class SyncAllResponse(BaseModel):
    synced: int
    failed: int
    reconciled: int = 0  # workouts detected missing from Garmin and re-queued
    activities_fetched: int = 0
    activities_matched: int = 0
    fetch_error: str | None = None
```

- [ ] **Step 2: Add field to frontend SyncAllResponse**

In `frontend/src/api/types.ts`, update the `SyncAllResponse` interface (line 120):

```typescript
export interface SyncAllResponse {
  synced: number
  failed: number
  reconciled: number
  activities_fetched: number
  activities_matched: number
  fetch_error: string | null
}
```

- [ ] **Step 3: Verify existing tests still pass**

```bash
pytest backend/tests/integration/test_api_sync.py -v --no-cov
```

Expected: all pass (default `reconciled=0` is backward-compatible).

- [ ] **Step 4: Commit**

```bash
git add backend/src/api/routers/sync.py frontend/src/api/types.ts
git commit -m "feat: add reconciled count to SyncAllResponse (backend + frontend)"
```

---

## Chunk 4: Wire reconciliation into `sync_all` + integration tests (TDD)

### Task 4: Write failing integration tests

**Files:**
- Modify: `backend/tests/integration/test_api_sync.py` (add tests to `TestSyncAll` class, after line 717)

- [ ] **Step 1: Write the failing tests**

Add to `TestSyncAll` class, after the existing tests (before `class TestSyncStatus` at line 724):

```python
    async def test_sync_all_reconciles_synced_workouts_missing_from_garmin(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Synced workout whose garmin_workout_id is NOT on Garmin gets re-pushed."""
        stale_id = "stale-gone-from-garmin"
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id=stale_id
        )
        # Garmin returns an empty list — stale_id is not there
        mock_sync_service.get_workouts.return_value = []

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        data = response.json()
        assert data["reconciled"] == 1
        assert data["synced"] == 1  # re-pushed after reconciliation (mock returns "garmin-abc-123")
        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_workout_id == "garmin-abc-123"

    async def test_sync_all_does_not_reconcile_when_garmin_id_exists_on_garmin(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Synced workout whose garmin_workout_id IS on Garmin is not touched.

        This is the existing test_sync_all_does_not_reset_synced_workout_when_id_exists_on_garmin
        test's complement — verifies reconciled=0 explicitly.
        """
        valid_id = "valid-garmin-456"
        sw = await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id=valid_id
        )
        mock_sync_service.get_workouts.return_value = [
            {"workoutId": valid_id, "workoutName": "My Workout"}
        ]

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        data = response.json()
        assert data["reconciled"] == 0
        assert data["synced"] == 0
        await session.refresh(sw)
        assert sw.sync_status == "synced"
        assert sw.garmin_workout_id == valid_id

    async def test_sync_all_reconciliation_skips_completed_workouts(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """Completed workouts with stale garmin_workout_id are NOT reconciled."""
        sw = await _make_scheduled_workout(
            session,
            sync_status="synced",
            garmin_workout_id="stale-completed",
            completed=True,
        )
        mock_sync_service.get_workouts.return_value = []

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        assert response.json()["reconciled"] == 0
        await session.refresh(sw)
        assert sw.garmin_workout_id == "stale-completed"  # untouched

    async def test_sync_all_reconciliation_skipped_when_get_workouts_fails(
        self,
        client: AsyncClient,
        session: AsyncSession,
        mock_sync_service: MagicMock,
    ) -> None:
        """When get_workouts() fails, reconciliation is safely skipped."""
        await _make_scheduled_workout(
            session, sync_status="synced", garmin_workout_id="stale-id"
        )
        mock_sync_service.get_workouts.side_effect = RuntimeError("429")

        response = await client.post("/api/v1/sync/all")

        assert response.status_code == 200
        assert response.json()["reconciled"] == 0
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest backend/tests/integration/test_api_sync.py::TestSyncAll::test_sync_all_reconciles_synced_workouts_missing_from_garmin -v --no-cov
```

Expected: FAIL — `reconciled` is 0 and `synced` is 0 (the stale workout isn't re-queued yet).

### Task 5: Implement reconciliation in `sync_all`

**Files:**
- Modify: `backend/src/api/routers/sync.py` (insert reconciliation block between line 547 and 548, update return at line ~664)

- [ ] **Step 3: Add reconciliation block**

Insert between line 547 (end of garmin_workouts fetch block) and line 548 (push loop). Uses inline import to match existing pattern (lines 420, 562, 636 all use inline imports):

```python
    # ── Reconciliation: detect synced workouts missing from Garmin ──────
    reconciled = 0
    if garmin_workouts is not None:
        from src.garmin.dedup import find_missing_from_garmin

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
            db_garmin_ids = {sw.garmin_workout_id for sw in synced_with_ids}
            missing_ids = find_missing_from_garmin(db_garmin_ids, garmin_workouts)

            if missing_ids:
                for sw in synced_with_ids:
                    if sw.garmin_workout_id in missing_ids:
                        sw.sync_status = "modified"
                        sw.garmin_workout_id = None
                        session.add(sw)
                        reconciled += 1

                await session.commit()
                logger.info(
                    "Reconciliation: %d workouts missing from Garmin — re-queuing for user %s",
                    reconciled,
                    current_user.id,
                )
```

- [ ] **Step 4: Update the return statement**

Change the `SyncAllResponse` return at line ~664 to include `reconciled`:

```python
    return SyncAllResponse(
        synced=synced,
        failed=failed,
        reconciled=reconciled,
        activities_fetched=activities_fetched,
        activities_matched=activities_matched,
        fetch_error=fetch_error,
    )
```

- [ ] **Step 5: Run all sync integration tests**

```bash
pytest backend/tests/integration/test_api_sync.py -v --no-cov
```

Expected: all tests PASS including:
- 4 new reconciliation tests
- Existing `test_sync_all_does_not_reset_synced_workout_when_id_exists_on_garmin` (line 678, validates happy path)
- Existing `test_sync_all_skips_when_get_workouts_fails` (line 701, validates graceful degradation)

- [ ] **Step 6: Run ruff**

```bash
ruff check backend/src/api/routers/sync.py
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/api/routers/sync.py backend/tests/integration/test_api_sync.py
git commit -m "feat: reconcile synced workouts missing from Garmin in sync_all"
```

---

## Chunk 5: Full test suite + cleanup

### Task 6: Run full test suite

- [ ] **Step 1: Run all backend tests with coverage**

```bash
pytest backend/tests/ -v --cov=src --cov-report=term-missing
```

Expected: all green, coverage ≥ 80%.

- [ ] **Step 2: Run frontend tests**

```bash
cd frontend && npm test -- --run
```

Expected: all pass.

### Task 7: Clean up compare script

**Files:**
- Modify: `backend/scripts/compare_garmin_workouts.py`

The debugging session added `import traceback` + `traceback.print_exc()` and `get_settings.cache_clear()` to the script. Keep `cache_clear()` and `ssl=require` → `sslmode=require` fix (useful for prod queries). Remove the traceback debug output.

- [ ] **Step 1: Remove `import traceback` and `traceback.print_exc()` from the except block** (revert to just the `print(f"{RED}Failed...` line)

- [ ] **Step 2: Commit**

```bash
git add backend/scripts/compare_garmin_workouts.py
git commit -m "fix: clean up compare script debug output, keep prod DB fixes"
```

### Task 8: Final docs + wrap-up

- [ ] **Step 1: Update STATUS.md** — move reconciliation from "In Progress" to "Done"

- [ ] **Step 2: Update features/garmin-sync/CLAUDE.md** — add "Sync-All Reconciliation" section documenting the new flow

- [ ] **Step 3: Run `revise-claude-md` skill** on all touched CLAUDE.md files

- [ ] **Step 4: Commit docs**

```bash
git add STATUS.md CLAUDE.md features/garmin-sync/CLAUDE.md
git commit -m "docs: mark sync-all reconciliation complete"
```
