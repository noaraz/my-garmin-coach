# Neon PostgreSQL Query Optimization

**Date:** 2026-03-19
**Status:** Draft

## Problem

GarminCoach uses Neon PostgreSQL (free tier: 100 CU-hours/month, 0.5 GB storage, scale-to-zero after 5 min idle). With 2-5 users, we need to minimize DB round-trips to stay within compute limits and handle cold-start latency gracefully.

**Current issues:**
- N+1 queries in zone cascade and sync operations (up to 50-100+ queries for users with many workouts)
- Individual row deletes instead of bulk operations
- No connection pool tuning for Neon's scale-to-zero behavior
- `get_current_user` hits DB on every authenticated request
- No caching — identical data re-fetched on every page navigation

## Design

### 1. Connection Pool Tuning

**File:** `backend/src/db/database.py`

Conditionally configure the SQLAlchemy engine based on database type:

- **PostgreSQL (Neon):** `pool_size=5`, `max_overflow=5`, `pool_recycle=270`, `pool_pre_ping=True` (270s = 30s safety margin before Neon's 5-min idle timeout)
- **SQLite (dev):** Keep current defaults

`pool_pre_ping=True` is critical — it detects stale connections after Neon's scale-to-zero idle timeout, preventing connection errors on the first request after inactivity.

### 2. Fix N+1: Zone Cascade Re-Resolve

**File:** `backend/src/services/zone_service.py` — `_cascade_re_resolve()`

**Before:** Loads all incomplete workouts (1 query), then `session.get(WorkoutTemplate, id)` per workout (N queries).

**After:** Collect unique `workout_template_id` values, batch-load with `SELECT ... WHERE id IN (...)` (1 query), look up from dict in the loop.

**Reduction:** N+1 queries → 2 queries (workouts + templates).

### 3. Fix N+1: Sync Operations

**File:** `backend/src/api/routers/sync.py`

**Before:** `sync_all` and `sync_modified_workouts` call `_sync_and_persist` per workout, which does `session.get(WorkoutTemplate, id)` individually.

**After:** Add `_preload_templates()` helper that batch-loads all needed templates. Pass the dict to `_sync_and_persist`. For `sync_single` (1 workout), keep the existing single-fetch as fallback.

**Reduction:** N+1 queries → 2 queries per sync operation.

### 4. Bulk DELETE in Zone Repositories

**File:** `backend/src/repositories/zones.py`

**Before:** `delete_by_profile()` fetches all zones (1 query), then deletes each individually (N queries).

**After:** Single `DELETE FROM hrzone WHERE profile_id = :id` statement. Same for `PaceZone`.

**Reduction:** N+1 → 1 query per zone type.

### 5. Batch Auth Operations

**File:** `backend/src/auth/service.py`

**`bootstrap()`:** Currently creates 5 invite codes with 5 separate `commit()` calls. Change to batch `session.add()` all 5, single `commit()`. Skip `refresh()` since only the code strings (generated in Python) are returned.

**`reset_admins()`:** Currently fetches all rows then deletes individually. Change to bulk `DELETE FROM invitecode` + `DELETE FROM user` in a single transaction.

### 6. In-Memory TTL Cache

**New file:** `backend/src/core/cache.py`

Simple dict-based TTL cache. No external dependencies. Per-process (fine for single Render instance).

**API:**
```python
get(key: str) -> Any | None
set(key: str, value: Any, ttl: int = 60) -> None
invalidate(key: str) -> None
invalidate_prefix(prefix: str) -> None
clear() -> None
```

**Cached data:**

| Key pattern | Data | TTL | Invalidated by |
|-------------|------|-----|----------------|
| `user:{user_id}` | `User` object | 60s | User update (rare) |
| `profile:{user_id}` | `AthleteProfile` | 60s | `PUT /profile` |
| `hr_zones:{profile_id}` | `list[HRZone]` | 60s | Zone recalculate |
| `pace_zones:{profile_id}` | `list[PaceZone]` | 60s | Zone recalculate |

**Integration points:**
- `auth/dependencies.py` `get_current_user`: Check cache before `session.get(User, id)`
- `services/zone_service.py`: Cache zone reads, invalidate on writes
- `services/profile_service.py`: Cache profile reads, invalidate on writes

**Cache invalidation:** Every write operation invalidates the relevant key before returning. Same-user writes are always fresh. Cross-user staleness bounded by 60s TTL — acceptable for 2-5 users.

**Test isolation:** `cache.clear()` in an autouse pytest fixture to prevent cross-test contamination.

## Impact Summary

| Optimization | Queries saved | Affected endpoints |
|---|---|---|
| Batch template load (cascade) | N-1 per zone recalc | `PUT /profile`, `POST /zones/*/recalculate` |
| Batch template load (sync) | N-1 per sync | `POST /sync/all`, `POST /sync/{id}` |
| Bulk zone deletes | N-1 per zone type | `POST /zones/*/recalculate` |
| Batch invite creates | 4 commits | `POST /auth/bootstrap` |
| Batch admin reset | 2×N commits → 2 | `POST /auth/reset-admins` |
| Cache `get_current_user` | 1 per request (on hit) | Every protected endpoint |
| Cache zones/profile | 1-3 per page load (on hit) | `/zones`, `/profile`, `/calendar` |

**Typical browsing session (10 page loads):** ~30-40 DB queries → ~10-15.
**Zone recalculation with 20 incomplete workouts:** ~35 queries → ~12.

## Out of Scope

- Redis or external cache (overkill for 2-5 users)
- Frontend request dedup (marginal benefit)
- Neon cold-start keep-alive ping (burns CU-hours)
- Multi-worker cache coherence (single Render instance)
