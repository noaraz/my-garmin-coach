# Design: Migrate to python-garminconnect 0.3.x

**Date**: 2026-04-14
**Status**: Draft
**Motivation**: garth (deprecated March 2026) SSO form flow is degrading. python-garminconnect 0.3.x replaces garth with native DI OAuth authentication. Migration needed before the old flow breaks completely.

---

## Decision Summary

| Decision | Choice |
|---|---|
| Architecture | Adapter Protocol + V1/V2 classes behind factory |
| Token storage | Keep DB-encrypted, add `garmin_auth_version` column |
| Revertibility | Feature flag (`GARMIN_AUTH_VERSION` env var) |
| Workout models | Adopt typed models via WorkoutFacade |
| MFA | Not supported (no MFA enabled) |
| Scope | Auth migration + workout facade; formatter stays |

---

## Architecture

```
Settings.garmin_auth_version ("v1" | "v2")     ← Feature flag
         │
   client_factory.py                            ← Single branching point
         │
    ┌────┴────┐
    │         │
 V1 path   V2 path
    │         │
    ▼         ▼
GarminAdapterV1         GarminAdapterV2
(garth + garminconnect   (garminconnect 0.3.x
 0.2.40)                  native DI OAuth)
    │         │
    └────┬────┘
         │
  GarminAdapterProtocol              ← Shared interface
         │
  All consumers unchanged:
  SyncOrchestrator, ActivityFetchService,
  token_persistence, auto_reconnect, etc.
```

### Key Principle

The `GarminAdapterProtocol` interface is the contract. Consumers (SyncOrchestrator, routers, etc.) never know which version they're talking to. The factory in `client_factory.py` is the **only** code that reads the feature flag (via a FastAPI dependency that queries `SystemConfig`), and injects the version into the WorkoutFacade.

---

## Components

### 1. Feature Flag (Runtime-Switchable)

**Files**: `backend/src/core/config.py`, `backend/src/db/models.py`, `backend/src/api/routers/admin.py`

The flag is stored in a `SystemConfig` DB table and exposed via an admin API endpoint. Changes take effect on the next request — no restart required.

```python
# SystemConfig table (new)
class SystemConfig(SQLModel, table=True):
    key: str = Field(primary_key=True)     # e.g. "garmin_auth_version"
    value: str                              # "v1" or "v2"
    updated_at: datetime | None = None

# Admin endpoint
@router.post("/api/v1/admin/garmin-auth-version")
async def set_garmin_auth_version(version: Literal["v1", "v2"], ...):
    """Switch Garmin auth version at runtime. Admin-only."""
    ...

# Reading the flag (cached per-request via FastAPI dependency)
async def get_garmin_auth_version(session: AsyncSession) -> str:
    row = await session.get(SystemConfig, "garmin_auth_version")
    return row.value if row else "v1"  # default v1
```

- Default `"v1"` — no behavior change until explicitly opted in
- Switch via `POST /api/v1/admin/garmin-auth-version` with `{"version": "v2"}`
- Revert: same endpoint with `{"version": "v1"}` — instant, no restart
- Fallback: `GARMIN_AUTH_VERSION` env var used as initial seed if no DB row exists

### 2. Adapter Protocol

**File**: `backend/src/garmin/adapter_protocol.py` (NEW)

```python
from typing import Any, Protocol

class GarminAdapterProtocol(Protocol):
    def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]: ...
    def schedule_workout(self, workout_id: str, workout_date: str) -> dict[str, Any]: ...
    def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None: ...
    def delete_workout(self, workout_id: str) -> None: ...
    def unschedule_workout(self, schedule_id: str) -> None: ...
    def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict[str, Any]]: ...
    def get_workouts(self) -> list[dict[str, Any]]: ...
    def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]: ...
    def dump_token(self) -> str: ...
```

Also houses the unified exception hierarchy (see section 8).

### 3. GarminAdapterV1

**File**: `backend/src/garmin/adapter_v1.py` (renamed from `adapter.py`)

Current code, unchanged except for wrapping library exceptions in the unified hierarchy. Uses:
- `client.garth.post/put/delete()` for raw API calls
- `client.garth.dumps()` for token serialization
- `client.garth.loads()` for token deserialization

Each method wraps `GarthHTTPError`, `requests.exceptions.HTTPError`, and `cffi_requests.exceptions.HTTPError` in the unified `GarminAdapterError` subclasses (see section 8).

### 4. GarminAdapterV2

**File**: `backend/src/garmin/adapter_v2.py` (NEW)

Uses garminconnect 0.3.x native methods:
- `client.connectapi(path, **kwargs)` replaces `client.garth.post/put/delete()`
- Native `client.delete_workout()`, `client.unschedule_workout()` where available
- Token serialization: `json.dumps(client.garmin_tokens)` (or equivalent new API)
- Token deserialization: `client.login(tokenstore=token_path_or_dict)`

Each method wraps `GarminConnectAuthenticationError`, `GarminConnectTooManyRequestsError`, and `GarminConnectConnectionError` in the unified hierarchy.

**Method mapping**:

| V1 (garth-based) | V2 (0.3.x native) |
|---|---|
| `client.upload_workout(dict)` | `client.upload_running_workout(RunningWorkout)` or `client.connectapi()` |
| `client.garth.post("connectapi", url, json=...)` | `client.connectapi(path, method="POST", json=...)` |
| `client.garth.put("connectapi", url, json=...)` | `client.connectapi(path, method="PUT", json=...)` |
| `client.garth.delete("connectapi", url)` | `client.connectapi(path, method="DELETE")` |
| `client.garth.dumps()` | Serialize `client.garmin_tokens` dict |
| `client.garth.loads(json)` | Pass token dict to constructor or `login()` |
| `client.get_activities_by_date()` | `client.get_activities_by_date()` (unchanged) |
| `client.get_workouts()` | `client.get_workouts()` (unchanged) |
| `client.connectapi(path)` | `client.connectapi(path)` (unchanged) |

### 5. Client Factory (Updated)

**File**: `backend/src/garmin/client_factory.py`

```python
def create_adapter(token_json: str) -> GarminAdapterProtocol:
    """Create the appropriate adapter based on feature flag."""
    if get_settings().garmin_auth_version == "v2":
        return GarminAdapterV2(token_json)
    return GarminAdapterV1(token_json)

def login_and_get_token(
    email: str,
    password: str,
    fingerprint: str = CHROME_VERSION,
    proxy_url: str | None = None,
) -> str:
    """Login and return serialized token JSON.
    
    V1: Creates garth.Client, applies ChromeTLSSession, calls client.login().
        Caller (garmin_connect.py) handles fingerprint rotation + retry loop.
    V2: Creates Garmin(email, password), calls client.login(). Library handles
        TLS fingerprinting and 5-strategy cascading login internally.
        fingerprint and proxy_url params are ignored.
    """
    if get_settings().garmin_auth_version == "v2":
        return _login_v2(email, password)
    return _login_v1(email, password, fingerprint, proxy_url)
```

**V2 login simplification**: The garmin_connect.py retry loop (5 fingerprints, 30-45s delays) becomes unnecessary for V2 since the library handles cascading login internally. The router will check the auth version and either use the existing retry loop (V1) or make a single `login_and_get_token()` call (V2).

`ChromeTLSSession` and `FINGERPRINT_SEQUENCE` stay for V1 but are unused by V2.

### 6. Token Storage + Auth Version Column

**Migration**: Add `garmin_auth_version` column to `AthleteProfile`

```python
# AthleteProfile
garmin_auth_version: str | None = Field(default="v1")  # "v1" or "v2"
```

**On connect**: Store the auth version used alongside the token.
**On adapter creation**: If `garmin_auth_version` in DB != feature flag setting → trigger auto-reconnect to get a compatible token.

**Rollback risk**: If the flag is reverted to V1 and stored credentials are expired (>30 days) or missing, the user must manually reconnect via Settings. Mitigation: before switching the flag to V2 in production, verify all active users have stored credentials that are within the 30-day window.

### 7. WorkoutFacade

**File**: `backend/src/garmin/workout_facade.py` (NEW)

The facade receives the auth version as a constructor parameter (injected by the factory or the dependency that creates it), not by reading the setting directly. This preserves the single-branching-point principle.

```python
class WorkoutFacade:
    """Stable interface between workout templates and Garmin API format.
    
    Isolates the rest of the codebase from garminconnect library changes.
    When the library's workout API changes, only this facade needs updating.
    """
    
    def __init__(self, auth_version: str = "v1") -> None:
        self._auth_version = auth_version
    
    def build_workout(
        self,
        workout_name: str,
        resolved_steps: list,
        description: str | None = None,
    ) -> dict | RunningWorkout:
        """Convert internal workout data to Garmin-uploadable format.
        
        Signature matches SyncOrchestrator's formatter callable contract:
        (workout_name, steps, description) -> dict[str, Any]
        """
        if self._auth_version == "v2":
            return self._build_typed(workout_name, resolved_steps, description)
        return format_workout(workout_name, resolved_steps, description)
    
    def _build_typed(self, name, steps, description) -> RunningWorkout:
        """Build garminconnect 0.3.x typed RunningWorkout."""
        garmin_steps = [self._convert_step(s) for s in steps]
        return RunningWorkout(
            workoutName=name,
            description=description or "",
            workoutSteps=garmin_steps,
        )
    
    def _convert_step(self, step):
        """Map resolved step dict to garminconnect step builder."""
        # Maps step_type to create_warmup_step / create_interval_step / etc.
        ...
```

**SyncOrchestrator integration**: The facade's `build_workout()` matches the existing `formatter: Callable[..., dict[str, Any]]` signature that `SyncOrchestrator.__init__` expects. It can be injected directly as the formatter:
```python
facade = WorkoutFacade(auth_version=settings.garmin_auth_version)
orchestrator = SyncOrchestrator(sync_service, facade.build_workout, resolver)
```

**Existing `formatter.py` stays untouched** — the facade delegates to it for V1.

### 8. Exception Handling

**Unified exception hierarchy** in `adapter_protocol.py`:

```python
class GarminAdapterError(Exception): ...
class GarminAuthError(GarminAdapterError): ...
class GarminRateLimitError(GarminAdapterError): ...
class GarminConnectionError(GarminAdapterError): ...
class GarminNotFoundError(GarminAdapterError): ...
```

Note: `GarminAuthError` already exists in `backend/src/garmin/exceptions.py`. We'll extend or move it into the adapter protocol module.

Each adapter translates its library-specific exceptions internally:

| V1 catches | V2 catches | Raises |
|---|---|---|
| `GarthHTTPError` (401) | `GarminConnectAuthenticationError` | `GarminAuthError` |
| `GarthHTTPError` (429) | `GarminConnectTooManyRequestsError` | `GarminRateLimitError` |
| `requests.exceptions.HTTPError` | `GarminConnectConnectionError` | `GarminConnectionError` |
| `cffi_requests.exceptions.HTTPError` | `GarminConnectConnectionError` | `GarminConnectionError` |
| `GarthHTTPError` (404) | any (404 status) | `GarminNotFoundError` |

**Consumer migration**: Replace all `GarthHTTPError` / `cffi_requests.HTTPError` / `requests.HTTPError` catches in routers/services with `GarminAdapterError` subtypes. Specifically:
- `_is_garmin_404()` in `sync.py` → replaced by `except GarminNotFoundError`
- `_is_exchange_429()` in `sync.py` → replaced by `except GarminRateLimitError` (rate limit errors from the adapter already indicate Garmin-side throttling; the exchange-specific detection moves inside V1 adapter)

### 9. Auto-Reconnect Changes

`auto_reconnect.py` changes:
1. Import `login_and_get_token()` instead of `create_login_client()` — encapsulates the three-step login (create client → login → serialize token) into one call
2. Import `create_adapter()` instead of `create_api_client()` — returns `GarminAdapterProtocol`
3. Catch `GarminAuthError` / `GarminConnectionError` instead of `GarthHTTPError` / `cffi_requests.HTTPError`
4. On version mismatch (DB `garmin_auth_version` != flag): perform reconnect
5. Update `client_cache.put()` call — cache accepts `GarminAdapterProtocol` (see section 11)

### 10. What Gets Simpler with V2

| Component | V1 (current) | V2 |
|---|---|---|
| TLS fingerprinting | Manual `ChromeTLSSession` + 5-fingerprint rotation | Library handles internally |
| Login retry logic | 5 attempts with 30-45s delays in `garmin_connect.py` | Library's 5-strategy cascading login |
| Token refresh | garth refreshes in-memory, we persist after sync | Library auto-refreshes, we still persist |
| `delete_workout` | Raw `garth.delete()` call | Native `client.delete_workout()` |
| `unschedule_workout` | Raw `garth.delete()` call | Native `client.unschedule_workout()` |

### 11. Supporting Changes

**`client_cache.py`**: Update type hints from `GarminAdapter` to `GarminAdapterProtocol`. Currently hardcoded to the concrete class.

**`_get_garmin_adapter` in `sync.py`**: Update return type from `GarminAdapter` to `GarminAdapterProtocol`. Call `create_adapter()` instead of `create_api_client()`.

**`SyncOrchestrator.adapter` property**: Update type annotation to `GarminAdapterProtocol` (currently `Any`).

**`session.py`**: Dead code — not imported anywhere in the active codebase. Remove during this migration.

**`backend/src/garmin/__init__.py`**: Update re-exports if any exist after rename.

**`garmin_connect.py` login flow**: V2 path collapses the 5-attempt retry loop to a single `login_and_get_token()` call (library handles retries internally). V1 path keeps existing loop unchanged.

---

## Files Changed

| File | Change |
|---|---|
| `backend/src/core/config.py` | Add `garmin_auth_version` env var (seed value) |
| `backend/src/db/models.py` (SystemConfig) | NEW table for runtime feature flags |
| `backend/src/api/routers/admin.py` | NEW — admin endpoint to switch auth version at runtime |
| `backend/src/garmin/adapter_protocol.py` | NEW — Protocol + exception hierarchy |
| `backend/src/garmin/adapter.py` → `adapter_v1.py` | Rename, add exception translation wrapping |
| `backend/src/garmin/adapter_v2.py` | NEW — 0.3.x native adapter |
| `backend/src/garmin/client_factory.py` | Add V2 factory functions, keep V1 |
| `backend/src/garmin/workout_facade.py` | NEW — workout format abstraction |
| `backend/src/garmin/client_cache.py` | Update type hints to `GarminAdapterProtocol` |
| `backend/src/garmin/auto_reconnect.py` | Use unified exceptions, version-aware reconnect, `create_adapter()` |
| `backend/src/garmin/token_persistence.py` | Use adapter protocol type |
| `backend/src/garmin/session.py` | DELETE — dead code |
| `backend/src/api/routers/garmin_connect.py` | Use `login_and_get_token()`, V2 path skips retry loop, unified exceptions |
| `backend/src/api/routers/sync.py` | Use `GarminAdapterError` subtypes, update `_get_garmin_adapter` return type, remove `_is_garmin_404` / `_is_exchange_429` |
| `backend/src/services/sync_orchestrator.py` | Update `.adapter` property type to protocol |
| `backend/src/db/models.py` | Add `garmin_auth_version` column |
| `backend/alembic/versions/` | NEW migration for column |
| `backend/pyproject.toml` | Add `garminconnect>=0.3.2,<0.4`, keep `garth>=0.5.21,<0.6` |
| Tests: unit + integration | New V2 adapter tests, WorkoutFacade tests, update mocks |

---

## Migration Path

### Phase 1: Infrastructure
- Add `SystemConfig` table + Alembic migration
- Add admin endpoint `POST /api/v1/admin/garmin-auth-version`
- Add feature flag seed to Settings (env var fallback)
- Create adapter protocol + exception hierarchy
- Rename adapter.py → adapter_v1.py, add exception wrapping
- Update client_cache.py type hints
- Add DB migration for `garmin_auth_version` column
- Delete dead `session.py`

### Phase 2: V2 Adapter + Facade
- Create GarminAdapterV2
- Create WorkoutFacade
- Update client_factory with `create_adapter()` and `login_and_get_token()`

### Phase 3: Consumer Migration
- Replace all `GarthHTTPError` / `cffi_requests.HTTPError` catches with `GarminAdapterError` subtypes
- Remove `_is_garmin_404` and `_is_exchange_429` helpers (replaced by typed exceptions)
- Update auto_reconnect for version-aware reconnect
- Update garmin_connect.py login flow (V2 path: single call, no retry loop)
- Update sync.py `_get_garmin_adapter` return type
- Update SyncOrchestrator `.adapter` property type

### Phase 4: Testing
- Unit tests for V2 adapter (mock garminconnect 0.3.x client)
- Unit tests for WorkoutFacade (both V1 and V2 paths)
- Integration tests with feature flag toggling
- Manual end-to-end test with real Garmin account

### Phase 5: Rollout
- Deploy with `GARMIN_AUTH_VERSION=v1` (no change)
- Switch to `v2` in staging/dev
- Monitor for issues
- Switch production to `v2`
- After stable period: remove V1 code + garth dependency (separate PR)

---

## Rollback Plan

1. **Instant**: `POST /api/v1/admin/garmin-auth-version` with `{"version": "v1"}`. Takes effect on next request — no restart needed.
2. **Token mismatch**: Users with V2 tokens will auto-reconnect via stored credentials (transparent).
3. **If credentials expired/missing**: Users see "Garmin disconnected" and manually reconnect via Settings. **Pre-rollout check**: verify all active users have fresh (<30 day) stored credentials before switching to V2.
4. **Nuclear**: `git revert` the PR, redeploy. All V1 code is untouched.

---

## Risks

| Risk | Mitigation |
|---|---|
| garminconnect 0.3.x `connectapi()` signature doesn't match our needs | Investigate before implementation; fall back to raw HTTP if needed |
| Token format changes in future 0.3.x patches | Pin `garminconnect>=0.3.2,<0.4`; facade isolates changes |
| garth SSO breaks before migration is complete | V1 code is untouched; can ship V2 quickly since it's additive |
| Dual dependencies increase bundle size | Temporary; garth removed after V1 sunset |
| Rollback with expired credentials | Pre-rollout credential freshness check; manual reconnect fallback |

---

## Out of Scope

- MFA support (not enabled, can add later to V2 path)
- Removing V1 code / garth dependency (separate follow-up PR after V2 is stable)
- Migrating existing formatter.py internals (facade wraps it, doesn't replace it)
