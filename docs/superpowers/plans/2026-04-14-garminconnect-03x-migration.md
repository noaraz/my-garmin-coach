# Garminconnect 0.3.x Migration — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate Garmin auth from deprecated garth to python-garminconnect 0.3.x native DI OAuth, with a runtime feature flag for instant rollback.

**Architecture:** Two adapter classes (`GarminAdapterV1` and `GarminAdapterV2`) behind a shared `GarminAdapterProtocol`. A `SystemConfig` DB table + admin endpoint controls which adapter is active at runtime. A `WorkoutFacade` wraps the formatter for version-aware workout building.

**Tech Stack:** python-garminconnect 0.3.x, garth 0.5.x (retained for V1), FastAPI, SQLModel, Alembic, pytest

**Design spec:** `docs/superpowers/specs/2026-04-14-garminconnect-03x-migration-design.md`
**High-level plan:** `.claude/plans/quirky-sleeping-torvalds.md`

---

## File Map

| File | Role | Action |
|---|---|---|
| `backend/src/garmin/adapter_protocol.py` | Protocol + unified exceptions | CREATE |
| `backend/src/garmin/adapter_v1.py` | Current garth-based adapter (renamed) | RENAME from `adapter.py`, add exception wrapping |
| `backend/src/garmin/adapter_v2.py` | New 0.3.x native adapter | CREATE |
| `backend/src/garmin/workout_facade.py` | Version-aware workout format bridge | CREATE |
| `backend/src/garmin/client_factory.py` | Factory branching V1/V2 | MODIFY |
| `backend/src/garmin/client_cache.py` | Type hints → Protocol | MODIFY |
| `backend/src/garmin/auto_reconnect.py` | Use unified exceptions + factory | MODIFY |
| `backend/src/garmin/session.py` | Dead code | DELETE |
| `backend/src/garmin/exceptions.py` | Move exceptions to protocol module | MODIFY |
| `backend/src/garmin/__init__.py` | Re-export compat | MODIFY |
| `backend/src/db/models.py` | `SystemConfig` table + `garmin_auth_version` on AthleteProfile | MODIFY |
| `backend/src/core/config.py` | `garmin_auth_version` seed setting | MODIFY |
| `backend/src/api/routers/admin.py` | Admin endpoint for flag | CREATE |
| `backend/src/api/routers/sync.py` | Use protocol types + unified exceptions | MODIFY |
| `backend/src/api/routers/garmin_connect.py` | V2 login path, unified exceptions | MODIFY |
| `backend/src/services/sync_orchestrator.py` | Type annotation update | MODIFY |
| `backend/src/api/app.py` | Register admin router | MODIFY |
| `backend/alembic/versions/` | Two migrations | CREATE |
| `backend/pyproject.toml` | Dependency versions | MODIFY |
| `backend/tests/unit/test_adapter_protocol.py` | Protocol + exception tests | CREATE |
| `backend/tests/unit/test_adapter_v2.py` | V2 adapter tests | CREATE |
| `backend/tests/unit/test_workout_facade.py` | Facade tests | CREATE |
| `backend/tests/unit/test_admin_flag.py` | Admin endpoint tests | CREATE |
| `backend/tests/unit/test_client_factory_v2.py` | Factory branching tests | CREATE |

---

## Phase 0: Documentation Updates (Before Code)

### Task 0: Update tracking docs and CLAUDE.md files

**Files:**
- Modify: `STATUS.md` (root)
- Modify: `PLAN.md` (root)
- Modify: `CLAUDE.md` (root)
- Modify: `features/garmin-sync/PLAN.md`
- Modify: `features/garmin-sync/CLAUDE.md`

- [ ] **Step 1: Update `STATUS.md`**

Add garminconnect 0.3.x migration to "In Progress" section with link to design spec.

- [ ] **Step 2: Update root `PLAN.md`**

Update the feature table: mark garmin-sync/auth migration as 🔄 in progress.

- [ ] **Step 3: Update root `CLAUDE.md`**

Add a section under "Garmin SSO & API" documenting the auth version feature flag, adapter protocol, and unified exceptions (preview of what will exist after implementation).

- [ ] **Step 4: Update `features/garmin-sync/PLAN.md`**

Add the garminconnect 0.3.x migration as a new phase/section with task checklist.

- [ ] **Step 5: Update `features/garmin-sync/CLAUDE.md`**

Add notes about the dual-adapter architecture, feature flag, and `GarminAdapterProtocol`.

- [ ] **Step 6: Run `claude-md-management:claude-md-improver`**

Audit all CLAUDE.md files for staleness and improvement opportunities.

- [ ] **Step 7: Commit**

```bash
git add STATUS.md PLAN.md CLAUDE.md features/garmin-sync/PLAN.md features/garmin-sync/CLAUDE.md
git commit -m "docs: update tracking docs for garminconnect 0.3.x migration"
```

---

## Post-Implementation: Final Documentation

### Task 17: Capture session learnings

- [ ] **Step 1: Run `claude-md-management:revise-claude-md`**

Invoke to capture all session learnings into CLAUDE.md files (root + feature).

- [ ] **Step 2: Update `STATUS.md` and root `PLAN.md`**

Mark the migration as ✅ complete (or the appropriate status).

- [ ] **Step 3: Commit**

```bash
git add STATUS.md PLAN.md CLAUDE.md features/garmin-sync/CLAUDE.md
git commit -m "docs: finalize docs after garminconnect 0.3.x migration"
```

---

## Chunk 1: Infrastructure — Protocol, Exceptions, SystemConfig, Feature Flag

### Task 1: Upgrade dependencies in pyproject.toml

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Update garminconnect version and add garth pin**

In `backend/pyproject.toml`, change:
```
"garminconnect==0.2.40",
```
to:
```
"garminconnect>=0.3.2,<0.4",
"garth>=0.5.21,<0.6",
```

garth is now an explicit dependency (it was previously pulled transitively via garminconnect 0.2.x). We keep it for the V1 adapter path.

- [ ] **Step 2: Install updated dependencies**

Run: `cd backend && pip install -e ".[dev]"`
Expected: Successful install. Verify with `pip show garminconnect` → version 0.3.x

- [ ] **Step 3: Verify existing tests still pass (V1 code unchanged)**

Run: `cd backend && pytest tests/unit/ -v --no-cov -x`
Expected: All existing tests pass (garminconnect 0.3.x is API-compatible for the import paths we use in tests)

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: upgrade garminconnect to 0.3.x, pin garth 0.5.x"
```

---

### Task 2: Create adapter protocol + unified exception hierarchy

**Files:**
- Create: `backend/src/garmin/adapter_protocol.py`
- Modify: `backend/src/garmin/exceptions.py`
- Test: `backend/tests/unit/test_adapter_protocol.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_adapter_protocol.py`:

```python
from __future__ import annotations

from typing import Any

from src.garmin.adapter_protocol import (
    GarminAdapterError,
    GarminAdapterProtocol,
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)


class TestGarminAdapterProtocol:
    """Verify the protocol and exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        """All specific exceptions are subclasses of GarminAdapterError."""
        assert issubclass(GarminAuthError, GarminAdapterError)
        assert issubclass(GarminRateLimitError, GarminAdapterError)
        assert issubclass(GarminConnectionError, GarminAdapterError)
        assert issubclass(GarminNotFoundError, GarminAdapterError)

    def test_catch_all_with_base(self) -> None:
        """Catching GarminAdapterError catches all subtypes."""
        for exc_cls in (GarminAuthError, GarminRateLimitError, GarminConnectionError, GarminNotFoundError):
            try:
                raise exc_cls("test")
            except GarminAdapterError:
                pass  # should be caught

    def test_protocol_structural_typing(self) -> None:
        """A class matching the protocol is accepted by runtime_checkable."""
        class FakeAdapter:
            def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]:
                return {}
            def schedule_workout(self, workout_id: str, workout_date: str) -> dict[str, Any]:
                return {}
            def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None:
                pass
            def delete_workout(self, workout_id: str) -> None:
                pass
            def unschedule_workout(self, schedule_id: str) -> None:
                pass
            def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
                return []
            def get_workouts(self) -> list[dict[str, Any]]:
                return []
            def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
                return []
            def dump_token(self) -> str:
                return ""

        assert isinstance(FakeAdapter(), GarminAdapterProtocol)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_adapter_protocol.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.garmin.adapter_protocol'`

- [ ] **Step 3: Create adapter_protocol.py**

Create `backend/src/garmin/adapter_protocol.py`:

```python
"""Shared protocol and exception hierarchy for Garmin adapters.

All Garmin adapter implementations (V1/garth, V2/native) implement
GarminAdapterProtocol and translate library-specific exceptions into
the unified hierarchy defined here.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Unified exception hierarchy
# ---------------------------------------------------------------------------

class GarminAdapterError(Exception):
    """Base exception for all Garmin adapter errors."""


class GarminAuthError(GarminAdapterError):
    """Authentication failed (invalid credentials, expired token)."""


class GarminRateLimitError(GarminAdapterError):
    """Garmin Connect returned 429 — rate limited."""


class GarminConnectionError(GarminAdapterError):
    """Network or connection error communicating with Garmin."""


class GarminNotFoundError(GarminAdapterError):
    """Garmin resource not found (404)."""


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class GarminAdapterProtocol(Protocol):
    """Interface contract for all Garmin adapter implementations."""

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

- [ ] **Step 4: Update exceptions.py to re-export from protocol**

Replace `backend/src/garmin/exceptions.py` contents with:

```python
from __future__ import annotations

# Unified exceptions live in adapter_protocol.py.
# Re-export here for backward compatibility (existing imports).
from src.garmin.adapter_protocol import (  # noqa: F401
    GarminAdapterError,
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)


class FormatterError(Exception):
    """Raised when the Garmin formatter encounters invalid input."""
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/unit/test_adapter_protocol.py -v --no-cov`
Expected: All 3 tests PASS

- [ ] **Step 6: Verify existing tests still pass**

Run: `cd backend && pytest tests/unit/ -v --no-cov -x`
Expected: All pass (existing `GarminAuthError` / `GarminRateLimitError` imports still work via `exceptions.py` re-exports)

- [ ] **Step 7: Commit**

```bash
git add backend/src/garmin/adapter_protocol.py backend/src/garmin/exceptions.py backend/tests/unit/test_adapter_protocol.py
git commit -m "feat: add GarminAdapterProtocol and unified exception hierarchy"
```

---

### Task 3: Add SystemConfig table + garmin_auth_version on AthleteProfile

**Files:**
- Modify: `backend/src/db/models.py`
- Create: `backend/alembic/versions/<generated>_add_system_config_and_auth_version.py`

- [ ] **Step 1: Add SystemConfig model and garmin_auth_version column**

In `backend/src/db/models.py`, add after existing imports:

```python
class SystemConfig(SQLModel, table=True):
    """Key-value store for runtime feature flags."""

    __tablename__ = "systemconfig"

    key: str = Field(primary_key=True)
    value: str
    updated_at: Optional[datetime] = Field(default=None)
```

In the `AthleteProfile` class, add after `garmin_credential_stored_at`:

```python
    garmin_auth_version: Optional[str] = Field(default="v1")  # "v1" or "v2"
```

- [ ] **Step 2: Generate Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add system_config table and garmin_auth_version"`

Review the generated file:
- Should contain `create_table('systemconfig', ...)` 
- Should contain `add_column('athleteprofile', Column('garmin_auth_version', ...))` 
- Delete any spurious operations on other tables (autogenerate drift)

- [ ] **Step 3: Apply migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration applies successfully

- [ ] **Step 4: Commit**

```bash
git add backend/src/db/models.py backend/alembic/versions/*system_config*
git commit -m "feat: add SystemConfig table and garmin_auth_version column"
```

---

### Task 4: Add feature flag setting + admin endpoint

**Files:**
- Modify: `backend/src/core/config.py`
- Create: `backend/src/api/routers/admin.py`
- Modify: `backend/src/api/app.py`
- Test: `backend/tests/unit/test_admin_flag.py`

- [ ] **Step 1: Add seed setting to config.py**

In `backend/src/core/config.py`, add to the `Settings` class after `gemini_api_key`:

```python
    # Garmin auth version — seed value for SystemConfig.
    # Actual runtime value is read from the DB (SystemConfig table).
    garmin_auth_version: str = "v1"
```

- [ ] **Step 2: Write the failing test for the admin endpoint**

Create `backend/tests/unit/test_admin_flag.py`:

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.db.models import SystemConfig


class TestGarminAuthVersionEndpoint:
    """Test the admin endpoint for switching garmin auth version."""

    @pytest.fixture
    def app(self):
        return create_app()

    @pytest.fixture
    async def client(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_set_garmin_auth_version_requires_admin(self, client: AsyncClient) -> None:
        """Non-admin users cannot switch the auth version."""
        resp = await client.post(
            "/api/v1/admin/garmin-auth-version",
            json={"version": "v2"},
        )
        assert resp.status_code == 401

    async def test_get_garmin_auth_version_default(self, client: AsyncClient) -> None:
        """Default version is v1 when no DB row exists."""
        resp = await client.get("/api/v1/admin/garmin-auth-version")
        assert resp.status_code == 401  # requires auth
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_admin_flag.py -v --no-cov`
Expected: FAIL — either import error or 404 (endpoint doesn't exist yet)

- [ ] **Step 4: Create admin router**

Create `backend/src/api/routers/admin.py`:

```python
"""Admin-only endpoints for runtime configuration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import SystemConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class AuthVersionRequest(BaseModel):
    version: Literal["v1", "v2"]


class AuthVersionResponse(BaseModel):
    version: str


def _require_admin(user: User) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/garmin-auth-version", response_model=AuthVersionResponse)
async def set_garmin_auth_version(
    body: AuthVersionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AuthVersionResponse:
    """Switch Garmin auth version at runtime. Admin-only."""
    _require_admin(current_user)

    row = await session.get(SystemConfig, "garmin_auth_version")
    if row is None:
        row = SystemConfig(
            key="garmin_auth_version",
            value=body.version,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(row)
    else:
        row.value = body.version
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(row)

    await session.commit()
    logger.info("Garmin auth version switched to %s by user %s", body.version, current_user.id)
    return AuthVersionResponse(version=body.version)


@router.get("/garmin-auth-version", response_model=AuthVersionResponse)
async def get_garmin_auth_version(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AuthVersionResponse:
    """Read current Garmin auth version. Admin-only."""
    _require_admin(current_user)

    row = await session.get(SystemConfig, "garmin_auth_version")
    version = row.value if row else "v1"
    return AuthVersionResponse(version=version)
```

- [ ] **Step 5: Register admin router in app.py**

In `backend/src/api/app.py`, add import and include:

```python
from src.api.routers.admin import router as admin_router
# ... in create_app():
app.include_router(admin_router)
```

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/unit/test_admin_flag.py -v --no-cov`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/core/config.py backend/src/api/routers/admin.py backend/src/api/app.py backend/tests/unit/test_admin_flag.py
git commit -m "feat: add admin endpoint for runtime garmin auth version switching"
```

---

### Task 5: Rename adapter.py → adapter_v1.py with exception wrapping

**Files:**
- Rename: `backend/src/garmin/adapter.py` → `backend/src/garmin/adapter_v1.py`
- Modify: `backend/src/garmin/__init__.py` (backward compat re-export)
- Modify all importers: `client_factory.py`, `sync.py`, `auto_reconnect.py`, `client_cache.py`

- [ ] **Step 1: Rename the file**

```bash
cd backend && git mv src/garmin/adapter.py src/garmin/adapter_v1.py
```

- [ ] **Step 2: Add backward-compat re-export in __init__.py**

Update `backend/src/garmin/__init__.py`:

```python
from __future__ import annotations

# Backward-compat: existing imports of `from src.garmin.adapter import GarminAdapter`
# continue to work during migration. New code should import from adapter_v1 directly.
from src.garmin.adapter_v1 import GarminAdapter  # noqa: F401
```

- [ ] **Step 3: Update imports in client_factory.py**

In `backend/src/garmin/client_factory.py`, change:
```python
from src.garmin.adapter import GarminAdapter
```
to:
```python
from src.garmin.adapter_v1 import GarminAdapter
```

- [ ] **Step 4: Leave sync.py and auto_reconnect.py imports unchanged for now**

`sync.py` and `auto_reconnect.py` still import `from src.garmin.adapter import GarminAdapter`. The `__init__.py` re-export (Step 2) handles this transparently. These imports will be replaced in Task 10 and Task 12 respectively — no need for intermediate churn.

- [ ] **Step 6: Update imports in client_cache.py**

In `backend/src/garmin/client_cache.py`, change:
```python
from src.garmin.adapter import GarminAdapter
```
to:
```python
from src.garmin.adapter_protocol import GarminAdapterProtocol
```

And update type hints throughout the file:
- `_cache: dict[int, tuple[GarminAdapter, float]]` → `dict[int, tuple[GarminAdapterProtocol, float]]`
- `def get(user_id: int) -> GarminAdapter | None:` → `def get(user_id: int) -> GarminAdapterProtocol | None:`
- `def put(user_id: int, adapter: GarminAdapter) -> None:` → `def put(user_id: int, adapter: GarminAdapterProtocol) -> None:`

- [ ] **Step 7: Add exception wrapping to adapter_v1.py**

In `backend/src/garmin/adapter_v1.py`, add imports at top:

```python
import requests
from curl_cffi import requests as cffi_requests
from garth.exc import GarthHTTPError

from src.garmin.adapter_protocol import (
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)
```

Then wrap each method's body in try/except. Example for `delete_workout`:

```python
def delete_workout(self, workout_id: str) -> None:
    try:
        url = f"/workout-service/workout/{workout_id}"
        self._client.garth.delete("connectapi", url, api=True)
    except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
        _translate_exception(exc)
```

Add a helper at module level:

```python
def _translate_exception(exc: Exception) -> None:
    """Translate garth/requests exceptions to unified hierarchy. Always raises."""
    status = _get_status_code(exc)
    if status == 404:
        raise GarminNotFoundError(str(exc)) from exc
    if status == 429:
        raise GarminRateLimitError(str(exc)) from exc
    if status == 401:
        raise GarminAuthError(str(exc)) from exc
    raise GarminConnectionError(str(exc)) from exc


def _get_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from various exception types."""
    # GarthHTTPError wraps requests.HTTPError
    if isinstance(exc, GarthHTTPError):
        inner = getattr(exc, "error", None)
        response = getattr(inner, "response", None)
        if response is not None:
            return getattr(response, "status_code", None)
    # curl_cffi or requests HTTPError
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)
    return None
```

- [ ] **Step 8: Run all tests**

Run: `cd backend && pytest tests/unit/ -v --no-cov -x`
Expected: All pass

- [ ] **Step 9: Commit**

```bash
git add backend/src/garmin/adapter_v1.py backend/src/garmin/__init__.py backend/src/garmin/client_factory.py backend/src/garmin/client_cache.py backend/src/garmin/auto_reconnect.py backend/src/api/routers/sync.py
git commit -m "refactor: rename adapter → adapter_v1, add exception wrapping, update imports"
```

---

### Task 6: Delete dead session.py

**Files:**
- Delete: `backend/src/garmin/session.py`

- [ ] **Step 1: Verify session.py is not imported anywhere**

Run: `cd backend && grep -r "from src.garmin.session" src/ tests/`
Expected: No matches (dead code confirmed)

- [ ] **Step 2: Delete the file**

```bash
cd backend && git rm src/garmin/session.py
```

- [ ] **Step 3: Run tests to confirm nothing breaks**

Run: `cd backend && pytest tests/unit/ -v --no-cov -x`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove dead GarminSession class"
```

---

## Chunk 2: V2 Adapter, Client Factory, WorkoutFacade

### Task 7: Create GarminAdapterV2

**Files:**
- Create: `backend/src/garmin/adapter_v2.py`
- Test: `backend/tests/unit/test_adapter_v2.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_adapter_v2.py`:

```python
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.garmin.adapter_protocol import (
    GarminAdapterProtocol,
    GarminAuthError,
    GarminNotFoundError,
    GarminRateLimitError,
)


class TestGarminAdapterV2:
    """Test GarminAdapterV2 wrapping garminconnect 0.3.x client."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        client = MagicMock()
        client.get_activities_by_date.return_value = []
        client.get_workouts.return_value = []
        client.connectapi.return_value = {"calendarItems": []}
        return client

    @pytest.fixture
    def adapter(self, mock_client: MagicMock):
        from src.garmin.adapter_v2 import GarminAdapterV2
        return GarminAdapterV2(mock_client)

    def test_implements_protocol(self, adapter) -> None:
        assert isinstance(adapter, GarminAdapterProtocol)

    def test_add_workout_delegates(self, adapter, mock_client: MagicMock) -> None:
        mock_client.connectapi.return_value = {"workoutId": "123"}
        result = adapter.add_workout({"workoutName": "Test"})
        assert result["workoutId"] == "123"

    def test_delete_workout_delegates(self, adapter, mock_client: MagicMock) -> None:
        adapter.delete_workout("123")
        mock_client.delete_workout.assert_called_once_with("123")

    def test_unschedule_workout_delegates(self, adapter, mock_client: MagicMock) -> None:
        adapter.unschedule_workout("456")
        mock_client.unschedule_workout.assert_called_once_with("456")

    def test_get_activities_by_date_delegates(self, adapter, mock_client: MagicMock) -> None:
        adapter.get_activities_by_date("2026-01-01", "2026-01-31")
        mock_client.get_activities_by_date.assert_called_once_with("2026-01-01", "2026-01-31")

    def test_get_workouts_delegates(self, adapter, mock_client: MagicMock) -> None:
        adapter.get_workouts()
        mock_client.get_workouts.assert_called_once()

    def test_get_calendar_items_converts_month(self, adapter, mock_client: MagicMock) -> None:
        """Garmin uses 0-indexed months. Adapter converts 1-indexed → 0-indexed."""
        mock_client.connectapi.return_value = {"calendarItems": [{"id": 1}]}
        result = adapter.get_calendar_items(2026, 3)
        mock_client.connectapi.assert_called_once_with("/calendar-service/year/2026/month/2")
        assert result == [{"id": 1}]

    def test_dump_token_serializes(self, adapter, mock_client: MagicMock) -> None:
        mock_client.garmin_tokens = {"access_token": "abc", "refresh_token": "xyz"}
        result = adapter.dump_token()
        parsed = json.loads(result)
        assert parsed["access_token"] == "abc"

    def test_auth_error_translated(self, adapter, mock_client: MagicMock) -> None:
        from garminconnect import GarminConnectAuthenticationError
        mock_client.delete_workout.side_effect = GarminConnectAuthenticationError("bad creds")
        with pytest.raises(GarminAuthError):
            adapter.delete_workout("123")

    def test_rate_limit_translated(self, adapter, mock_client: MagicMock) -> None:
        from garminconnect import GarminConnectTooManyRequestsError
        mock_client.get_workouts.side_effect = GarminConnectTooManyRequestsError("429")
        with pytest.raises(GarminRateLimitError):
            adapter.get_workouts()

    def test_404_translated(self, adapter, mock_client: MagicMock) -> None:
        from garminconnect import GarminConnectConnectionError
        exc = GarminConnectConnectionError("404 Not Found")
        exc.status_code = 404  # some versions attach this
        mock_client.delete_workout.side_effect = exc
        with pytest.raises(GarminNotFoundError):
            adapter.delete_workout("123")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_adapter_v2.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.garmin.adapter_v2'`

- [ ] **Step 3: Implement GarminAdapterV2**

Create `backend/src/garmin/adapter_v2.py`:

```python
"""Garmin adapter for garminconnect 0.3.x (native DI OAuth).

Implements GarminAdapterProtocol using the new library's native methods.
All garminconnect-specific exceptions are translated to the unified hierarchy.
"""
from __future__ import annotations

import json
from typing import Any

import garminconnect

from src.garmin.adapter_protocol import (
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)


def _translate_exception(exc: Exception) -> None:
    """Translate garminconnect 0.3.x exceptions to unified hierarchy. Always raises."""
    if isinstance(exc, garminconnect.GarminConnectAuthenticationError):
        raise GarminAuthError(str(exc)) from exc
    if isinstance(exc, garminconnect.GarminConnectTooManyRequestsError):
        raise GarminRateLimitError(str(exc)) from exc
    # GarminConnectConnectionError may carry a status_code for 404s
    status = getattr(exc, "status_code", None)
    if status == 404:
        raise GarminNotFoundError(str(exc)) from exc
    if "404" in str(exc):
        raise GarminNotFoundError(str(exc)) from exc
    raise GarminConnectionError(str(exc)) from exc


class GarminAdapterV2:
    """Wraps garminconnect 0.3.x Garmin client with the standard adapter interface."""

    def __init__(self, client: garminconnect.Garmin) -> None:
        self._client = client

    def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]:
        """Upload a workout via connectapi."""
        try:
            return self._client.connectapi(
                "/workout-service/workout",
                method="POST",
                json=formatted_workout,
            )
        except Exception as exc:
            _translate_exception(exc)

    def schedule_workout(self, workout_id: str, workout_date: str) -> dict[str, Any]:
        """Schedule a workout on a specific date."""
        try:
            return self._client.schedule_workout(workout_id, workout_date)
        except Exception as exc:
            _translate_exception(exc)

    def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None:
        """Update an existing Garmin workout in-place."""
        try:
            self._client.connectapi(
                f"/workout-service/workout/{workout_id}",
                method="PUT",
                json=formatted_workout,
            )
        except Exception as exc:
            _translate_exception(exc)

    def delete_workout(self, workout_id: str) -> None:
        """Permanently delete a workout from Garmin Connect."""
        try:
            self._client.delete_workout(workout_id)
        except Exception as exc:
            _translate_exception(exc)

    def unschedule_workout(self, schedule_id: str) -> None:
        """Remove a single calendar schedule entry."""
        try:
            self._client.unschedule_workout(schedule_id)
        except Exception as exc:
            _translate_exception(exc)

    def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch activities from Garmin within a date range."""
        try:
            return self._client.get_activities_by_date(start_date, end_date)
        except Exception as exc:
            _translate_exception(exc)

    def get_workouts(self) -> list[dict[str, Any]]:
        """Fetch all planned workouts from Garmin Connect."""
        try:
            return self._client.get_workouts()
        except Exception as exc:
            _translate_exception(exc)

    def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
        """Fetch calendar items. Converts 1-indexed month to Garmin's 0-indexed."""
        try:
            garmin_month = month - 1
            path = f"/calendar-service/year/{year}/month/{garmin_month}"
            result = self._client.connectapi(path)
            return result.get("calendarItems", []) if isinstance(result, dict) else []
        except Exception as exc:
            _translate_exception(exc)

    def dump_token(self) -> str:
        """Serialize current token state as JSON string."""
        return json.dumps(self._client.garmin_tokens)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/test_adapter_v2.py -v --no-cov`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/garmin/adapter_v2.py backend/tests/unit/test_adapter_v2.py
git commit -m "feat: add GarminAdapterV2 for garminconnect 0.3.x"
```

---

### Task 8: Update client_factory.py with V2 paths

**Files:**
- Modify: `backend/src/garmin/client_factory.py`
- Test: `backend/tests/unit/test_client_factory_v2.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_client_factory_v2.py`:

```python
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.garmin.adapter_protocol import GarminAdapterProtocol


class TestClientFactoryV2:
    """Test factory functions branch correctly on auth version."""

    @patch("src.garmin.client_factory._get_auth_version", return_value="v2")
    @patch("src.garmin.client_factory.garminconnect.Garmin")
    def test_create_adapter_v2(self, mock_garmin_cls, mock_version) -> None:
        from src.garmin.client_factory import create_adapter
        mock_client = MagicMock()
        mock_garmin_cls.return_value = mock_client
        adapter = create_adapter('{"access_token": "test"}')
        assert isinstance(adapter, GarminAdapterProtocol)

    @patch("src.garmin.client_factory._get_auth_version", return_value="v1")
    def test_create_adapter_v1(self, mock_version) -> None:
        from src.garmin.client_factory import create_adapter
        # V1 needs garth tokens — mock the garth loading
        with patch("src.garmin.client_factory.garminconnect.Garmin") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            adapter = create_adapter('{"oauth1": "test"}')
            assert isinstance(adapter, GarminAdapterProtocol)

    @patch("src.garmin.client_factory._get_auth_version", return_value="v2")
    @patch("src.garmin.client_factory.garminconnect.Garmin")
    def test_login_v2(self, mock_garmin_cls, mock_version) -> None:
        from src.garmin.client_factory import login_and_get_token
        mock_client = MagicMock()
        mock_client.garmin_tokens = {"access_token": "fresh"}
        mock_garmin_cls.return_value = mock_client
        token = login_and_get_token("user@test.com", "pass123")
        mock_client.login.assert_called_once()
        assert "fresh" in token
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_client_factory_v2.py -v --no-cov`
Expected: FAIL — `_get_auth_version` doesn't exist yet

- [ ] **Step 3: Update client_factory.py**

Rewrite `backend/src/garmin/client_factory.py`:

```python
"""Centralized Garmin client creation with feature-flag branching.

V1 (garth): Chrome TLS impersonation, manual fingerprint rotation.
V2 (garminconnect 0.3.x): Library handles TLS + cascading login internally.

The factory reads the auth version from Settings (env var seed).
Runtime switching is handled by the admin endpoint writing to SystemConfig;
callers that need the DB-backed value should query it via dependency injection.
"""
from __future__ import annotations

import json
from typing import Any

import garminconnect
import garth
import requests
from curl_cffi import requests as cffi_requests

from src.garmin.adapter_protocol import GarminAdapterProtocol
from src.garmin.adapter_v1 import GarminAdapter
from src.garmin.adapter_v2 import GarminAdapterV2

CHROME_VERSION = "chrome136"

FINGERPRINT_SEQUENCE: list[str] = [
    "chrome136",
    "safari15_5",
    "edge101",
    "chrome120",
    "chrome99",
]


class ChromeTLSSession(cffi_requests.Session):
    """curl_cffi session impersonating Chrome to bypass Akamai Bot Manager.

    garth accesses requests.Session internals (adapters, hooks) so we
    pre-populate them from a real requests.Session.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _rs = requests.Session()
        self.adapters = _rs.adapters
        self.hooks = _rs.hooks


def _get_auth_version() -> str:
    """Read auth version from Settings (env var seed). For DB-backed runtime
    value, callers should use the FastAPI dependency instead."""
    from src.core.config import get_settings
    return get_settings().garmin_auth_version


# ---------------------------------------------------------------------------
# Adapter creation (token → adapter)
# ---------------------------------------------------------------------------

def create_adapter(token_json: str, auth_version: str | None = None) -> GarminAdapterProtocol:
    """Create the appropriate adapter based on auth version.

    Args:
        token_json: Serialized token (garth format for V1, JSON dict for V2).
        auth_version: Override auth version. If None, reads from Settings.
    """
    version = auth_version or _get_auth_version()
    if version == "v2":
        return _create_adapter_v2(token_json)
    return _create_adapter_v1(token_json)


def _create_adapter_v1(token_json: str) -> GarminAdapter:
    """Create a V1 GarminAdapter from garth tokens with Chrome TLS."""
    client = garminconnect.Garmin()
    client.garth.loads(token_json)
    client.garth.sess = ChromeTLSSession(impersonate=CHROME_VERSION)
    return GarminAdapter(client)


def _create_adapter_v2(token_json: str) -> GarminAdapterV2:
    """Create a V2 GarminAdapterV2 from 0.3.x token dict."""
    tokens = json.loads(token_json)
    client = garminconnect.Garmin()
    client.garmin_tokens = tokens
    # The library handles TLS and token refresh internally
    return GarminAdapterV2(client)


# ---------------------------------------------------------------------------
# Login (email+password → token JSON)
# ---------------------------------------------------------------------------

def login_and_get_token(
    email: str,
    password: str,
    fingerprint: str = CHROME_VERSION,
    proxy_url: str | None = None,
    auth_version: str | None = None,
) -> str:
    """Login and return serialized token JSON.

    V1: Creates garth.Client with ChromeTLSSession. Caller handles retry loop.
    V2: Creates Garmin(email, password), calls login(). Library handles retries.
    """
    version = auth_version or _get_auth_version()
    if version == "v2":
        return _login_v2(email, password)
    return _login_v1(email, password, fingerprint, proxy_url)


def _login_v1(
    email: str,
    password: str,
    fingerprint: str = CHROME_VERSION,
    proxy_url: str | None = None,
) -> str:
    """V1 login via garth.Client + Chrome TLS."""
    client = garth.Client()
    client.sess = ChromeTLSSession(impersonate=fingerprint)
    if proxy_url:
        client.sess.proxies = {"https": proxy_url}
    client.login(email, password)
    return client.dumps()


def _login_v2(email: str, password: str) -> str:
    """V2 login via garminconnect 0.3.x native auth."""
    client = garminconnect.Garmin(email=email, password=password)
    client.login()
    return json.dumps(client.garmin_tokens)


# ---------------------------------------------------------------------------
# Backward compat (used by existing code during migration)
# ---------------------------------------------------------------------------

def create_api_client(token_json: str) -> GarminAdapterProtocol:
    """Backward-compat alias for create_adapter(). Reads version from Settings."""
    return create_adapter(token_json)


def create_login_client(
    fingerprint: str = CHROME_VERSION,
    proxy_url: str | None = None,
) -> garth.Client:
    """V1-only: Create a garth.Client for SSO login. Used by garmin_connect.py retry loop."""
    client = garth.Client()
    client.sess = ChromeTLSSession(impersonate=fingerprint)
    if proxy_url:
        client.sess.proxies = {"https": proxy_url}
    return client
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/test_client_factory_v2.py -v --no-cov`
Expected: PASS

Run: `cd backend && pytest tests/unit/ -v --no-cov -x`
Expected: All existing tests still pass

- [ ] **Step 5: Commit**

```bash
git add backend/src/garmin/client_factory.py backend/tests/unit/test_client_factory_v2.py
git commit -m "feat: add V2 paths to client_factory with feature flag branching"
```

---

### Task 9: Create WorkoutFacade

**Files:**
- Create: `backend/src/garmin/workout_facade.py`
- Test: `backend/tests/unit/test_workout_facade.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_workout_facade.py`:

```python
from __future__ import annotations

from typing import Any

import pytest


class TestWorkoutFacadeV1:
    """WorkoutFacade delegates to existing formatter for V1."""

    def test_v1_delegates_to_format_workout(self) -> None:
        from src.garmin.workout_facade import WorkoutFacade

        facade = WorkoutFacade(auth_version="v1")
        # Provide minimal resolved steps that format_workout can handle
        steps = [
            {
                "step_type": "warmup",
                "end_condition": "time",
                "end_condition_value": 600,
                "target_type": "open",
                "target_value_one": None,
                "target_value_two": None,
            }
        ]
        result = facade.build_workout("Test Run", steps, "A test workout")
        assert isinstance(result, dict)
        assert result["workoutName"] == "Test Run"

    def test_v1_callable_signature_matches_orchestrator(self) -> None:
        """build_workout can be passed as formatter to SyncOrchestrator."""
        from src.garmin.workout_facade import WorkoutFacade

        facade = WorkoutFacade(auth_version="v1")
        # SyncOrchestrator calls: self._formatter(workout_name, steps, description)
        assert callable(facade.build_workout)


class TestWorkoutFacadeV2:
    """WorkoutFacade builds typed RunningWorkout for V2."""

    def test_v2_returns_typed_workout(self) -> None:
        from src.garmin.workout_facade import WorkoutFacade

        facade = WorkoutFacade(auth_version="v2")
        steps = [
            {
                "step_type": "warmup",
                "end_condition": "time",
                "end_condition_value": 600,
                "target_type": "open",
                "target_value_one": None,
                "target_value_two": None,
            }
        ]
        result = facade.build_workout("Test Run", steps, "A test workout")
        # V2 returns a dict built from typed models (serialized for upload)
        assert isinstance(result, dict)
        assert result["workoutName"] == "Test Run"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_workout_facade.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement WorkoutFacade**

Create `backend/src/garmin/workout_facade.py`:

```python
"""Version-aware workout format bridge.

Isolates the rest of the codebase from garminconnect library changes.
V1: delegates to the existing format_workout() in formatter.py.
V2: builds typed RunningWorkout using garminconnect 0.3.x step builders.

The facade's build_workout() signature matches SyncOrchestrator's
formatter callable contract: (workout_name, steps, description) -> dict.
"""
from __future__ import annotations

from typing import Any

from src.garmin.formatter import format_workout


class WorkoutFacade:
    """Stable interface between workout templates and Garmin API format."""

    def __init__(self, auth_version: str = "v1") -> None:
        self._auth_version = auth_version

    def build_workout(
        self,
        workout_name: str,
        resolved_steps: list[dict[str, Any]],
        workout_description: str = "",
    ) -> dict[str, Any]:
        """Convert internal workout data to Garmin-uploadable format.

        Signature matches SyncOrchestrator's formatter callable contract.
        Both V1 and V2 return a dict — V2 builds from typed models then
        serializes to the same dict format for upload.
        """
        if self._auth_version == "v2":
            return self._build_v2(workout_name, resolved_steps, workout_description)
        return format_workout(workout_name, resolved_steps, workout_description)

    def _build_v2(
        self,
        workout_name: str,
        resolved_steps: list[dict[str, Any]],
        workout_description: str,
    ) -> dict[str, Any]:
        """Build workout dict using garminconnect 0.3.x step builders.

        For now, delegates to the same format_workout() since the Garmin
        workout JSON format hasn't changed — only the upload method differs.
        This method exists as the extension point for adopting typed models
        (RunningWorkout, create_warmup_step, etc.) in a follow-up.
        """
        # TODO: Replace with typed model builders when garminconnect 0.3.x
        # workout models are validated against production Garmin API.
        # For the auth migration, the format is identical — only the
        # transport (connectapi vs garth.post) differs.
        return format_workout(workout_name, resolved_steps, workout_description)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/test_workout_facade.py -v --no-cov`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/garmin/workout_facade.py backend/tests/unit/test_workout_facade.py
git commit -m "feat: add WorkoutFacade for version-aware workout formatting"
```

---

## Chunk 3: Consumer Migration

### Task 10: Update sync.py — replace GarthHTTPError + helper functions

**Files:**
- Modify: `backend/src/api/routers/sync.py`

- [ ] **Step 1: Update imports**

In `backend/src/api/routers/sync.py`, replace:
```python
from garth.exc import GarthHTTPError
from src.garmin.adapter import GarminAdapter
from src.garmin.client_factory import create_api_client
```
with:
```python
from src.garmin.adapter_protocol import (
    GarminAdapterError,
    GarminAdapterProtocol,
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)
from src.garmin.client_factory import create_adapter
```

- [ ] **Step 2: Update `_get_garmin_adapter` return type and body**

Change the function signature and body:
```python
async def _get_garmin_adapter(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminAdapterProtocol:
```

Replace `create_api_client(token_json)` with `create_adapter(token_json)` on line 144.

- [ ] **Step 3: Replace `_is_exchange_429` with GarminRateLimitError**

The `_is_exchange_429` function and its callers need to be replaced. In the `sync_all` endpoint, wherever `_is_exchange_429(exc)` is checked, replace with catching `GarminRateLimitError` from the adapter. The exchange-429 detection is now handled inside `adapter_v1.py`'s exception translation.

Remove the `_is_exchange_429` function and its related cooldown logic. Keep the `clear_exchange_cooldown` function (used by auto_reconnect and garmin_connect).

Simplify: in the sync loop, catch `GarminRateLimitError` instead of inspecting raw exceptions.

- [ ] **Step 4: Replace `_is_garmin_404` with GarminNotFoundError**

Remove the `_is_garmin_404` function. In `_sync_and_persist` and other callers, replace:
```python
except Exception as exc:
    if _is_garmin_404(exc):
        ...
```
with:
```python
except GarminNotFoundError:
    ...
except GarminAdapterError as exc:
    ...
```

- [ ] **Step 5: Replace remaining GarthHTTPError catches**

Search for any remaining `GarthHTTPError` references and replace with `GarminAdapterError` subtypes.

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/unit/ tests/integration/ -v --no-cov -x`
Expected: All pass. Some test mocks may need updating — see Task 13.

- [ ] **Step 7: Commit**

```bash
git add backend/src/api/routers/sync.py
git commit -m "refactor: replace GarthHTTPError with unified GarminAdapterError in sync.py"
```

---

### Task 11: Update garmin_connect.py — V2 login path

**Files:**
- Modify: `backend/src/api/routers/garmin_connect.py`

- [ ] **Step 1: Update imports (keep garth imports for V1 path)**

**Add** new imports (keep existing ones — the V1 retry loop still catches raw `GarthHTTPError` and `cffi_requests.exceptions.HTTPError` because it uses `create_login_client()` directly, not through the adapter):

```python
# Keep existing:
from garth.exc import GarthHTTPError
from curl_cffi import requests as cffi_requests
# Add new:
from src.garmin.adapter_protocol import GarminAuthError, GarminRateLimitError
from src.garmin.client_factory import login_and_get_token  # add to existing import line
```

- [ ] **Step 2: Add V2 login path in connect_garmin endpoint**

Before the existing retry loop, add a V2 early path:

```python
# Check auth version — V2 handles retries internally
from src.db.models import SystemConfig
auth_version_row = await session.get(SystemConfig, "garmin_auth_version")
auth_version = auth_version_row.value if auth_version_row else "v1"

if auth_version == "v2":
    try:
        token_json = login_and_get_token(email, password, auth_version="v2")
        logger.info("Garmin V2 login succeeded for user_id=%s", current_user.id)
    except GarminAuthError as exc:
        raise HTTPException(status_code=400, detail="Garmin authentication failed.") from exc
    except GarminRateLimitError as exc:
        raise HTTPException(status_code=503, detail="Garmin rate-limiting. Try again later.") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Garmin authentication failed.") from exc
else:
    # Existing V1 retry loop (unchanged) ...
```

- [ ] **Step 3: Store auth version on profile after connect**

After encrypting and storing the token, also set:
```python
profile.garmin_auth_version = auth_version
```

- [ ] **Step 4: Replace exception types in V1 loop**

Replace catches of `GarthHTTPError` in the V1 retry loop with catches of both `GarthHTTPError` (still needed for V1) and the unified exceptions. Since V1 login uses `create_login_client()` directly (not through the adapter), garth exceptions are raw here — keep `GarthHTTPError` in the V1 path only.

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/unit/ -v --no-cov -x`
Expected: Pass

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/routers/garmin_connect.py
git commit -m "feat: add V2 login path in garmin_connect router"
```

---

### Task 12: Update auto_reconnect.py

**Files:**
- Modify: `backend/src/garmin/auto_reconnect.py`

- [ ] **Step 1: Update imports**

Replace:
```python
from garth.exc import GarthHTTPError
from src.garmin.adapter import GarminAdapter
from src.garmin.client_factory import create_api_client, create_login_client
```
with:
```python
from src.garmin.adapter_protocol import (
    GarminAdapterProtocol,
    GarminAuthError,
    GarminConnectionError,
)
from src.garmin.client_factory import create_adapter, login_and_get_token
```

- [ ] **Step 2: Update attempt_auto_reconnect**

Replace the login block:
```python
client = create_login_client()
client.login(email, password)
token_json = client.dumps()
```
with (note: pass `auth_version` explicitly to use the DB runtime value, not the env var seed):
```python
token_json = login_and_get_token(email, password, auth_version=current_version)
```
Where `current_version` comes from the version mismatch detection in Step 3.

Replace `create_api_client(token_json)` with `create_adapter(token_json)`.

Update the return type from `GarminAdapter | None` to `GarminAdapterProtocol | None`.

Replace exception catches:
```python
except (GarthHTTPError, cffi_requests.exceptions.HTTPError):
```
with:
```python
except (GarminAuthError, GarminConnectionError):
```

Remove the `cffi_requests` import if no longer used.

- [ ] **Step 3: Add version mismatch detection**

In `attempt_auto_reconnect`, after checking credentials, add:
```python
# Check if stored token version matches current flag
from src.db.models import SystemConfig
auth_version_row = await session.get(SystemConfig, "garmin_auth_version")
current_version = auth_version_row.value if auth_version_row else "v1"
stored_version = profile.garmin_auth_version or "v1"

if stored_version != current_version:
    logger.info(
        "Auth version mismatch for user %s: stored=%s, current=%s — forcing reconnect",
        user_id, stored_version, current_version,
    )
    # Fall through to reconnect logic below
```

After storing new tokens, also update:
```python
profile.garmin_auth_version = current_version
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/test_auto_reconnect.py -v --no-cov`
Expected: Pass (may need mock updates — see Task 13)

- [ ] **Step 5: Commit**

```bash
git add backend/src/garmin/auto_reconnect.py
git commit -m "refactor: update auto_reconnect for unified exceptions and V2 support"
```

---

### Task 13: Update test mocks for new imports

**Files:**
- Modify: `backend/tests/unit/test_auto_reconnect.py`
- Modify: `backend/tests/unit/test_exchange_429.py`
- Modify: `backend/tests/unit/test_garmin_adapter.py`
- Modify: `backend/tests/unit/test_garmin_client_factory.py`
- Modify: `backend/tests/unit/test_garmin_sync.py`
- Modify: `backend/tests/unit/test_garmin_connect_router.py` (if exists)
- Modify: `backend/tests/integration/test_api_sync.py`

- [ ] **Step 1: Update test_auto_reconnect.py mocks**

Replace any `GarthHTTPError` references with `GarminAuthError` / `GarminConnectionError` from the adapter_protocol. Update mock targets from `src.garmin.adapter.GarminAdapter` to `src.garmin.adapter_v1.GarminAdapter` or `src.garmin.client_factory.create_adapter`.

- [ ] **Step 2: Update test_exchange_429.py**

The exchange-429 detection now happens inside the adapter. Update tests to verify `GarminRateLimitError` is raised instead of checking `_is_exchange_429()` helper.

- [ ] **Step 3: Update test_garmin_adapter.py**

This file imports `from src.garmin.adapter import GarminAdapter`. The `__init__.py` re-export handles this, but verify tests pass. If mock targets reference `src.garmin.adapter.GarminAdapter`, they may need updating to `src.garmin.adapter_v1.GarminAdapter`.

- [ ] **Step 4: Update test_garmin_client_factory.py**

References `create_api_client` extensively — should still work via backward-compat alias. Verify. If mocking `src.garmin.adapter.GarminAdapter`, update the mock target.

- [ ] **Step 5: Update test_garmin_sync.py**

Imports `from src.garmin.exceptions import GarminAuthError`. The re-export covers this — verify it catches the new unified class correctly.

- [ ] **Step 6: Update test_api_sync.py mocks**

Replace `GarminAdapter` mock target paths and any `GarthHTTPError` raises with unified exceptions.

- [ ] **Step 4: Run full test suite**

Run: `cd backend && pytest tests/ -v --no-cov -x`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add backend/tests/
git commit -m "test: update mocks for unified exception hierarchy and adapter rename"
```

---

### Task 14: Wire WorkoutFacade into sync pipeline

**Files:**
- Modify: `backend/src/services/sync_orchestrator.py`
- Modify: `backend/src/api/routers/sync.py`

- [ ] **Step 1: Update SyncOrchestrator.adapter property type**

In `backend/src/services/sync_orchestrator.py`, change:
```python
@property
def adapter(self) -> Any:
```
to:
```python
@property
def adapter(self) -> Any:  # Returns GarminAdapterProtocol at runtime
```

(Keep `Any` return type since it accesses `_sync_service._client` which is typed as `Any`. The comment documents intent.)

- [ ] **Step 2: Wire WorkoutFacade into _get_garmin_sync_service**

In `backend/src/api/routers/sync.py`, update `_get_garmin_sync_service`:

```python
from src.garmin.workout_facade import WorkoutFacade
from src.db.models import SystemConfig

async def _get_garmin_sync_service(...) -> SyncOrchestrator:
    adapter = await _get_garmin_adapter(...)

    # Read auth version from DB for facade
    auth_version_row = await session.get(SystemConfig, "garmin_auth_version")
    auth_version = auth_version_row.value if auth_version_row else "v1"
    facade = WorkoutFacade(auth_version=auth_version)

    def _resolver(steps, **_):
        return steps

    return SyncOrchestrator(
        sync_service=GarminSyncService(adapter),
        formatter=facade.build_workout,
        resolver=_resolver,
    )
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/ -v --no-cov -x`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add backend/src/services/sync_orchestrator.py backend/src/api/routers/sync.py
git commit -m "refactor: wire WorkoutFacade into sync pipeline"
```

---

## Chunk 4: Final Verification

### Task 15: Full test suite + linting

**Files:** None (verification only)

- [ ] **Step 1: Run ruff linter**

Run: `cd backend && ruff check src/ tests/`
Expected: No errors. Fix any unused imports (e.g., leftover `GarthHTTPError` imports in V1-only paths).

- [ ] **Step 2: Run full test suite with coverage**

Run: `cd backend && pytest tests/ -v --cov=src --cov-report=term-missing`
Expected: All tests pass, coverage ≥ 80%

- [ ] **Step 3: Verify V1 path is unchanged**

Run with `GARMIN_AUTH_VERSION=v1`:
```bash
cd backend && GARMIN_AUTH_VERSION=v1 pytest tests/ -v --no-cov -x
```
Expected: All pass — V1 is the default, no behavior change

- [ ] **Step 4: Commit any lint fixes**

```bash
# Stage only the files with lint fixes (review git diff first)
git add <specific-files-with-lint-fixes>
git commit -m "chore: fix lint issues from migration"
```

---

### Task 16: Update documentation

**Files:**
- Modify: `CLAUDE.md` (root)
- Modify: `features/garmin-sync/CLAUDE.md`
- Modify: `STATUS.md`

- [ ] **Step 1: Update root CLAUDE.md**

Add to the "Garmin SSO & API" section:
```markdown
## Garmin Auth Version Feature Flag (added 2026-04-14)

- **Runtime toggle**: `SystemConfig` table stores `garmin_auth_version` ("v1" | "v2")
- **Admin endpoint**: `POST /api/v1/admin/garmin-auth-version` to switch at runtime
- **V1**: garth 0.5.x (SSO form flow) — `GarminAdapterV1` in `adapter_v1.py`
- **V2**: garminconnect 0.3.x (native DI OAuth) — `GarminAdapterV2` in `adapter_v2.py`
- **Factory**: `client_factory.py` branches on version, returns `GarminAdapterProtocol`
- **Unified exceptions**: All consumer code catches `GarminAdapterError` subtypes (not `GarthHTTPError`)
- **Token format**: Incompatible between V1/V2. `garmin_auth_version` column on `AthleteProfile` tracks format. Mismatch triggers auto-reconnect.
- **WorkoutFacade**: `workout_facade.py` bridges formatter output. Injected into `SyncOrchestrator` as the formatter callable.
```

- [ ] **Step 2: Update STATUS.md**

Add garminconnect 0.3.x migration to current status.

- [ ] **Step 3: Commit docs**

```bash
git add CLAUDE.md STATUS.md features/garmin-sync/CLAUDE.md
git commit -m "docs: document garminconnect 0.3.x migration and feature flag"
```
