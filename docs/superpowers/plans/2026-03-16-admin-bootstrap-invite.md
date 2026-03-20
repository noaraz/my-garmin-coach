# Admin Bootstrap + Invite System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hardened `/setup` page that creates the first admin user, and an admin-only invite link generator in Settings.

**Architecture:** Add `is_admin: bool` to the `User` model (True only for bootstrap user). The bootstrap endpoint requires a `BOOTSTRAP_SECRET` env var token and locks after first use. The JWT access token gains an `is_admin` claim decoded by `AuthContext`. The `/invite` endpoint becomes admin-only. Settings gains an admin section (visible when `isAdmin=true`) that generates copyable one-time registration links. RegisterPage reads `?invite=` from the URL to pre-fill the code.

**Tech Stack:** FastAPI + SQLModel + python-jose (backend); React 18 + TypeScript + React Router (frontend).

---

## Chunk 1: Backend

### Task 1: Add `is_admin` to User model + `bootstrap_secret` to Settings

**Files:**
- Modify: `backend/src/auth/models.py`
- Modify: `backend/src/core/config.py`

- [ ] **Step 1: Add `is_admin` field to User model**

In `backend/src/auth/models.py`, add after `is_active`:

```python
is_admin: bool = Field(default=False)
```

Full updated class:

```python
class User(SQLModel, table=True):
    """Application user with bcrypt-hashed password."""

    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 2: Add `bootstrap_secret` to Settings**

In `backend/src/core/config.py`, add after `garmincoach_secret_key`:

```python
bootstrap_secret: str = "dev-bootstrap-secret-change-in-prod"
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/auth/models.py backend/src/core/config.py
git commit -m "feat: add is_admin to User model and bootstrap_secret to Settings"
```

---

### Task 2: Add bootstrap schemas + update UserResponse

**Files:**
- Modify: `backend/src/auth/schemas.py`

- [ ] **Step 1: Write the failing test** (verify schemas exist)

In `backend/tests/unit/test_auth_schemas.py` (create if not exists, else append):

```python
def test_bootstrap_request_validates_password_length() -> None:
    from pydantic import ValidationError
    from src.auth.schemas import BootstrapRequest
    import pytest

    with pytest.raises(ValidationError):
        BootstrapRequest(setup_token="tok", email="a@b.com", password="short")


def test_bootstrap_response_has_invite_codes() -> None:
    from src.auth.schemas import BootstrapResponse

    resp = BootstrapResponse(invite_codes=["abc", "def"])
    assert len(resp.invite_codes) == 2


def test_user_response_has_is_admin() -> None:
    from src.auth.schemas import UserResponse

    ur = UserResponse(id=1, email="a@b.com", is_active=True, is_admin=True)
    assert ur.is_admin is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec backend pytest tests/unit/test_auth_schemas.py -v
```
Expected: FAIL (ImportError or ValidationError on BootstrapRequest/BootstrapResponse/UserResponse.is_admin)

- [ ] **Step 3: Add schemas**

In `backend/src/auth/schemas.py`, add after `InviteResponse`:

```python
class BootstrapRequest(BaseModel):
    setup_token: str
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class BootstrapResponse(BaseModel):
    invite_codes: list[str]
```

Update `UserResponse` to include `is_admin`:

```python
class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool
```

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec backend pytest tests/unit/test_auth_schemas.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/auth/schemas.py backend/tests/unit/test_auth_schemas.py
git commit -m "feat: add BootstrapRequest/BootstrapResponse schemas and is_admin to UserResponse"
```

---

### Task 3: Add `is_admin` claim to JWT access token

**Files:**
- Modify: `backend/src/auth/jwt.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/unit/test_auth_jwt.py` (create if not exists, else append):

```python
def test_create_access_token_includes_is_admin_claim() -> None:
    from jose import jwt
    from src.auth.jwt import create_access_token
    from src.core.config import get_settings

    settings = get_settings()
    token = create_access_token(user_id=42, email="a@b.com", is_admin=True)
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["is_admin"] is True


def test_create_access_token_defaults_is_admin_false() -> None:
    from jose import jwt
    from src.auth.jwt import create_access_token
    from src.core.config import get_settings

    settings = get_settings()
    token = create_access_token(user_id=1, email="a@b.com")
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["is_admin"] is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec backend pytest tests/unit/test_auth_jwt.py -v
```
Expected: FAIL (TypeError on unexpected is_admin kwarg)

- [ ] **Step 3: Update `create_access_token`**

In `backend/src/auth/jwt.py`, update `create_access_token`:

```python
def create_access_token(user_id: int, email: str = "", is_admin: bool = False) -> str:
    """Create a short-lived JWT access token for the given user."""
    settings = _settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec backend pytest tests/unit/test_auth_jwt.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/auth/jwt.py backend/tests/unit/test_auth_jwt.py
git commit -m "feat: add is_admin claim to JWT access token"
```

---

### Task 4: Add `bootstrap` service + update `login` and `refresh_token`

**Files:**
- Modify: `backend/src/auth/service.py`

- [ ] **Step 1: Update imports in service.py**

At the top of `backend/src/auth/service.py`, the import section becomes:

```python
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.auth.models import InviteCode, User
from src.auth.passwords import hash_password, verify_password
from src.auth.schemas import (
    AccessTokenResponse,
    BootstrapRequest,
    BootstrapResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from src.core.config import get_settings
```

- [ ] **Step 2: Write failing integration tests for bootstrap**

In `backend/tests/integration/test_api_auth.py`, add to the end:

```python
# ---------------------------------------------------------------------------
# Bootstrap tests
# ---------------------------------------------------------------------------


async def test_bootstrap_creates_admin_and_invite_codes(
    auth_client: AsyncClient,
) -> None:
    # Act
    resp = await auth_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "setup_token": "dev-bootstrap-secret-change-in-prod",
            "email": "admin@example.com",
            "password": "adminpassword",
        },
    )

    # Assert
    assert resp.status_code == 201
    body = resp.json()
    assert "invite_codes" in body
    assert len(body["invite_codes"]) == 5


async def test_bootstrap_returns_409_when_users_exist(
    auth_client: AsyncClient,
    invite_code: str,  # fixture creates a user
) -> None:
    # Act — users already exist (from invite_code fixture)
    resp = await auth_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "setup_token": "dev-bootstrap-secret-change-in-prod",
            "email": "second@example.com",
            "password": "password123",
        },
    )

    # Assert
    assert resp.status_code == 409


async def test_bootstrap_returns_403_on_wrong_token(
    auth_client: AsyncClient,
) -> None:
    # Act
    resp = await auth_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "setup_token": "wrong-token",
            "email": "admin@example.com",
            "password": "adminpassword",
        },
    )

    # Assert
    assert resp.status_code == 403


async def test_me_includes_is_admin(
    auth_client: AsyncClient,
) -> None:
    # Arrange — bootstrap creates an admin
    await auth_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "setup_token": "dev-bootstrap-secret-change-in-prod",
            "email": "admin@example.com",
            "password": "adminpassword",
        },
    )
    login_resp = await _login_user(auth_client, "admin@example.com", "adminpassword")
    token = login_resp.json()["access_token"]

    # Act
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_admin"] is True


async def test_invite_blocked_for_non_admin(
    auth_client: AsyncClient,
    invite_code: str,
) -> None:
    # Arrange — register a normal (non-admin) user
    await _register_user(auth_client, "user@example.com", "password123", invite_code)
    login_resp = await _login_user(auth_client, "user@example.com", "password123")
    token = login_resp.json()["access_token"]

    # Act — try to create an invite as non-admin
    resp = await auth_client.post(
        "/api/v1/auth/invite",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert
    assert resp.status_code == 403
```

- [ ] **Step 3: Run new tests to verify they fail**

```bash
docker compose exec backend pytest tests/integration/test_api_auth.py::test_bootstrap_creates_admin_and_invite_codes tests/integration/test_api_auth.py::test_invite_blocked_for_non_admin -v
```
Expected: FAIL (404 — route doesn't exist yet)

- [ ] **Step 4: Add `bootstrap` function + update `login` and `refresh_token` in service.py**

In `backend/src/auth/service.py`:

**Add `bootstrap` function** (after imports, before `register`):

```python
async def bootstrap(
    request: BootstrapRequest,
    session: AsyncSession,
) -> BootstrapResponse:
    """Create the first admin user and 5 invite codes.

    Raises:
        HTTPException 403 if setup_token is wrong.
        HTTPException 409 if any user already exists.
    """
    settings = get_settings()
    if not secrets.compare_digest(request.setup_token, settings.bootstrap_secret):
        raise HTTPException(status_code=403, detail="Invalid setup token")

    existing = (await session.exec(select(User).limit(1))).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Admin already exists")

    admin = User(
        email=request.email,
        password_hash=hash_password(request.password),
        is_admin=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    codes: list[str] = []
    for _ in range(5):
        code = secrets.token_urlsafe(16)
        invite = InviteCode(code=code, created_by=admin.id)
        session.add(invite)
        codes.append(code)
    await session.commit()

    return BootstrapResponse(invite_codes=codes)
```

**Update `login`** — pass `is_admin` to `create_access_token`:

```python
    return TokenResponse(
        access_token=create_access_token(user.id, user.email, user.is_admin),
        refresh_token=create_refresh_token(user.id),
    )
```

**Update `refresh_token`** — use `user.email` and `user.is_admin` (user already fetched from DB):

```python
    return AccessTokenResponse(
        access_token=create_access_token(user.id, user.email, user.is_admin)
    )
```

- [ ] **Step 5: Update `invite_code_fixture` — set `is_admin=True` on admin**

In `backend/tests/integration/test_api_auth.py`, update the `invite_code_fixture`:

```python
@pytest.fixture(name="invite_code")
async def invite_code_fixture(auth_session: AsyncSession) -> str:
    """Create a first user (admin) and an unused invite code, return the code string."""
    from src.auth.passwords import hash_password

    admin = User(
        email="admin@example.com",
        password_hash=hash_password("adminpassword"),
        is_admin=True,
    )
    auth_session.add(admin)
    await auth_session.commit()
    await auth_session.refresh(admin)

    code = InviteCode(code="VALID-INVITE-001", created_by=admin.id)
    auth_session.add(code)
    await auth_session.commit()

    return "VALID-INVITE-001"
```

- [ ] **Step 6: Run all backend integration auth tests**

```bash
docker compose exec backend pytest tests/integration/test_api_auth.py -v
```
Expected: All existing tests still PASS, new bootstrap/invite tests still FAIL (route not added yet)

- [ ] **Step 7: Commit service changes**

```bash
git add backend/src/auth/service.py backend/tests/integration/test_api_auth.py
git commit -m "feat: add bootstrap service, update login/refresh to include is_admin in JWT"
```

---

### Task 5: Add bootstrap route + admin guard on invite

**Files:**
- Modify: `backend/src/api/routers/auth.py`

- [ ] **Step 1: Update auth router**

Replace `backend/src/api/routers/auth.py` with:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth import service as auth_service
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.schemas import (
    AccessTokenResponse,
    BootstrapRequest,
    BootstrapResponse,
    InviteResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/bootstrap", response_model=BootstrapResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap(
    request: BootstrapRequest,
    session: AsyncSession = Depends(get_session),
) -> BootstrapResponse:
    """Create the first admin user and initial invite codes. Permanently locked after first use."""
    return await auth_service.bootstrap(request, session)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    """Register a new user using a valid invite code."""
    user = await auth_service.register(request, session)
    return RegisterResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate with email + password and receive JWT tokens."""
    return await auth_service.login(request, session)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> AccessTokenResponse:
    """Exchange a refresh token for a new access token."""
    return await auth_service.refresh_token(request.refresh_token, session)


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InviteResponse:
    """Create a new invite code (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    invite = await auth_service.create_invite(current_user, session)
    return InviteResponse(code=invite.code)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )
```

- [ ] **Step 2: Run all backend auth tests**

```bash
docker compose exec backend pytest tests/integration/test_api_auth.py -v
```
Expected: All tests PASS including the 5 new ones

- [ ] **Step 3: Run full test suite**

```bash
docker compose exec backend pytest -v --cov=src --cov-report=term-missing
```
Expected: All green, coverage maintained

- [ ] **Step 4: Commit**

```bash
git add backend/src/api/routers/auth.py
git commit -m "feat: add POST /bootstrap route and admin-only guard on POST /invite"
```

---

## Chunk 2: Frontend

### Task 6: Update types.ts and client.ts

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add types to types.ts**

In `frontend/src/api/types.ts`, add after `GarminStatusResponse`:

```typescript
export interface BootstrapResponse {
  invite_codes: string[]
}
```

- [ ] **Step 2: Update client.ts**

In `frontend/src/api/client.ts`:

1. Add `BootstrapResponse` to the import at the top:

```typescript
import type {
  Profile, ProfileUpdate,
  HRZone, HRZoneCreate,
  PaceZone,
  WorkoutTemplate, WorkoutTemplateCreate,
  ScheduledWorkout, ScheduleCreate,
  SyncAllResponse, SyncStatusItem,
  GarminStatusResponse,
  BootstrapResponse,
} from './types'
```

2. Update `fetchMe` return type to include `is_admin`:

```typescript
export const fetchMe = () =>
  request<{ id: number; email: string; is_active: boolean; is_admin: boolean }>('/auth/me')
```

3. Add `bootstrapAdmin` and `createInvite` functions after `registerUser`:

```typescript
export const bootstrapAdmin = (setupToken: string, email: string, password: string) =>
  request<BootstrapResponse>(
    '/auth/bootstrap',
    { method: 'POST', body: JSON.stringify({ setup_token: setupToken, email, password }) }
  )

export const createInvite = () =>
  request<{ code: string }>('/auth/invite', { method: 'POST' })
```

- [ ] **Step 3: Run frontend type check**

```bash
cd frontend && npm run build 2>&1 | head -30
```
Expected: No new TypeScript errors from these changes

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat: add BootstrapResponse type, bootstrapAdmin and createInvite API functions"
```

---

### Task 7: Update AuthContext to expose `isAdmin`

**Files:**
- Modify: `frontend/src/contexts/AuthContext.tsx`

- [ ] **Step 1: Update AuthContext**

Replace `frontend/src/contexts/AuthContext.tsx` with:

```typescript
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { loginUser as apiLoginUser, registerUser as apiRegisterUser } from '../api/client'

interface User {
  id: number
  email: string
  isAdmin: boolean
}

interface AuthContextValue {
  user: User | null
  accessToken: string | null
  isAdmin: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, inviteCode: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

interface JwtPayload {
  userId?: number
  sub?: string
  email?: string
  is_admin?: boolean
  exp?: number
}

function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = parts[1]
    // base64url → base64
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=')
    return JSON.parse(atob(padded)) as JwtPayload
  } catch {
    return null
  }
}

function isTokenExpired(payload: JwtPayload): boolean {
  if (!payload.exp) return false
  return Date.now() / 1000 > payload.exp
}

function userFromPayload(payload: JwtPayload): User | null {
  const id = payload.userId ?? (payload.sub ? parseInt(payload.sub, 10) : undefined)
  const email = payload.email
  if (!id || !email) return null
  return { id, email, isAdmin: payload.is_admin ?? false }
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  accessToken: null,
  isAdmin: false,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  isLoading: true,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('access_token')
    if (stored) {
      const payload = decodeJwtPayload(stored)
      if (payload && !isTokenExpired(payload)) {
        const parsedUser = userFromPayload(payload)
        if (parsedUser) {
          setUser(parsedUser)
          setAccessToken(stored)
        } else {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      } else {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
    }
    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string): Promise<void> => {
    const data = await apiLoginUser(email, password)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    setAccessToken(data.access_token)
    const payload = decodeJwtPayload(data.access_token)
    if (payload) {
      const parsedUser = userFromPayload(payload)
      setUser(parsedUser)
    }
  }

  const register = async (email: string, password: string, inviteCode: string): Promise<void> => {
    await apiRegisterUser(email, password, inviteCode)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
    setAccessToken(null)
  }

  const isAdmin = user?.isAdmin ?? false

  return (
    <AuthContext.Provider value={{ user, accessToken, isAdmin, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
```

- [ ] **Step 2: Run type check**

```bash
cd frontend && npm run build 2>&1 | head -40
```
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/contexts/AuthContext.tsx
git commit -m "feat: add isAdmin to AuthContext decoded from JWT is_admin claim"
```

---

### Task 8: Create SetupPage and add /setup route

**Files:**
- Create: `frontend/src/pages/SetupPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create SetupPage.tsx**

Create `frontend/src/pages/SetupPage.tsx`:

```typescript
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { bootstrapAdmin } from '../api/client'

export function SetupPage() {
  const navigate = useNavigate()

  const [setupToken, setSetupToken] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await bootstrapAdmin(setupToken, email, password)
      navigate('/login')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Setup failed'
      if (msg.includes('409')) {
        setError('Admin already exists. Please sign in.')
      } else {
        setError(msg)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '9px 11px',
    background: 'var(--input-bg)',
    border: '1px solid var(--input-border)',
    borderRadius: '5px',
    color: 'var(--text-primary)',
    fontSize: '13px',
    fontFamily: "'Barlow', system-ui, sans-serif",
    outline: 'none',
    boxSizing: 'border-box',
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text-secondary)',
    marginBottom: '6px',
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-main)',
    }}>
      <div style={{ width: '100%', maxWidth: '380px', padding: '0 16px' }}>
        {/* Logo */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '32px',
          justifyContent: 'center',
        }}>
          <div style={{
            width: '34px',
            height: '34px',
            background: 'var(--accent)',
            borderRadius: '7px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-on-accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <div style={{
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
            fontWeight: 700,
            fontSize: '20px',
            letterSpacing: '0.08em',
            color: 'var(--text-primary)',
            textTransform: 'uppercase',
          }}>GarminCoach</div>
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '10px',
          padding: '28px 24px',
        }}>
          <h1 style={{
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
            fontWeight: 700,
            fontSize: '20px',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--text-primary)',
            margin: '0 0 4px',
          }}>Admin Setup</h1>
          <p style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            fontFamily: "'Barlow', system-ui, sans-serif",
            margin: '0 0 20px',
          }}>One-time setup. Set BOOTSTRAP_SECRET in your environment first.</p>

          <form onSubmit={handleSubmit} noValidate action="." method="post">
            <div style={{ marginBottom: '14px' }}>
              <label htmlFor="setup-token" style={labelStyle}>Setup Token</label>
              <input
                id="setup-token"
                name="setup-token"
                type="password"
                autoComplete="off"
                value={setupToken}
                onChange={e => setSetupToken(e.target.value)}
                required
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label htmlFor="email" style={labelStyle}>Admin Email</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label htmlFor="password" style={labelStyle}>Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                style={inputStyle}
              />
            </div>

            {error && (
              <div
                role="alert"
                style={{
                  marginBottom: '14px',
                  padding: '9px 11px',
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  borderRadius: '5px',
                  fontSize: '12px',
                  color: '#ef4444',
                  fontFamily: "'Barlow', system-ui, sans-serif",
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                width: '100%',
                padding: '10px',
                background: isSubmitting ? 'var(--border-strong)' : 'var(--accent)',
                color: 'var(--text-on-accent)',
                border: 'none',
                borderRadius: '5px',
                fontSize: '12px',
                fontWeight: 600,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                transition: 'background 0.15s',
              }}
            >
              {isSubmitting ? 'Creating admin…' : 'Create Admin'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add /setup route to App.tsx**

In `frontend/src/App.tsx`, add the import:

```typescript
import { SetupPage } from './pages/SetupPage'
```

Add the route after `/register` (before the protected routes):

```typescript
<Route path="/setup" element={<SetupPage />} />
```

- [ ] **Step 3: Run type check**

```bash
cd frontend && npm run build 2>&1 | head -40
```
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SetupPage.tsx frontend/src/App.tsx
git commit -m "feat: add SetupPage and /setup public route for admin bootstrap"
```

---

### Task 9: Add Admin section to SettingsPage

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Update SettingsPage**

In `frontend/src/pages/SettingsPage.tsx`:

1. Add imports at the top:

```typescript
import { useState, useEffect, useCallback, type FormEvent } from 'react'
import { getGarminStatus, connectGarmin, disconnectGarmin, createInvite } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
```

2. Inside `SettingsPage()` function, add after the existing state declarations:

```typescript
const { isAdmin } = useAuth()
const [inviteLink, setInviteLink] = useState<string | null>(null)
const [isGenerating, setIsGenerating] = useState(false)
const [inviteError, setInviteError] = useState<string | null>(null)

const handleGenerateInvite = useCallback(async () => {
  setInviteError(null)
  setIsGenerating(true)
  try {
    const { code } = await createInvite()
    setInviteLink(`${window.location.origin}/register?invite=${code}`)
  } catch (err) {
    setInviteError(err instanceof Error ? err.message : 'Failed to generate invite')
  } finally {
    setIsGenerating(false)
  }
}, [])
```

3. Add the admin section JSX at the end of the returned `<div>`, after the Garmin Connect section closing `</div>`:

```tsx
{/* Admin section — only visible to admin */}
{isAdmin && (
  <div style={{ marginTop: '32px' }}>
    <div style={sectionLabel}>Admin</div>
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '20px 22px',
    }}>
      <p style={{
        fontSize: '12px',
        color: 'var(--text-secondary)',
        fontFamily: "'Barlow', system-ui, sans-serif",
        margin: '0 0 16px',
        lineHeight: 1.5,
      }}>
        Generate a one-time invite link to share with a friend. Each link can only be used once.
      </p>

      {inviteError && (
        <div style={{
          marginBottom: '14px',
          padding: '9px 11px',
          background: 'var(--color-error-bg)',
          border: '1px solid var(--color-error-border)',
          borderRadius: '5px',
          fontSize: '12px',
          color: 'var(--color-error)',
          fontFamily: "'Barlow', system-ui, sans-serif",
        }}>
          {inviteError}
        </div>
      )}

      <button
        onClick={handleGenerateInvite}
        disabled={isGenerating}
        style={{
          padding: '9px 20px',
          background: isGenerating ? 'var(--border-strong)' : 'var(--accent)',
          color: 'var(--text-on-accent)',
          border: 'none',
          borderRadius: '5px',
          fontSize: '11px',
          fontWeight: 700,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          cursor: isGenerating ? 'not-allowed' : 'pointer',
          transition: 'background 0.15s',
        }}
      >
        {isGenerating ? 'Generating…' : 'Generate Invite Link'}
      </button>

      {inviteLink && (
        <div style={{ marginTop: '16px' }}>
          <label style={{
            display: 'block',
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--text-secondary)',
            marginBottom: '6px',
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          }}>
            Invite Link
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              readOnly
              value={inviteLink}
              style={{
                flex: 1,
                padding: '9px 11px',
                background: 'var(--bg-surface-2)',
                border: '1px solid var(--border)',
                borderRadius: '5px',
                color: 'var(--text-primary)',
                fontSize: '12px',
                fontFamily: "'Barlow', system-ui, sans-serif",
                outline: 'none',
              }}
              onFocus={e => e.target.select()}
            />
            <button
              onClick={() => void navigator.clipboard.writeText(inviteLink)}
              style={{
                padding: '9px 14px',
                background: 'var(--bg-surface-3)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
                borderRadius: '5px',
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.06em',
                fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Copy
            </button>
          </div>
        </div>
      )}
    </div>
  </div>
)}
```

- [ ] **Step 2: Run type check**

```bash
cd frontend && npm run build 2>&1 | head -40
```
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx
git commit -m "feat: add admin invite section to SettingsPage (visible only to admin)"
```

---

### Task 10: RegisterPage — pre-fill invite code from URL param

**Files:**
- Modify: `frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: Update RegisterPage to read `?invite=` param**

In `frontend/src/pages/RegisterPage.tsx`:

1. Add `useSearchParams` to the react-router-dom import:

```typescript
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
```

2. Inside `RegisterPage()`, add after the existing hooks:

```typescript
const [searchParams] = useSearchParams()
```

3. Change the `inviteCode` initial state to read from URL:

```typescript
const [inviteCode, setInviteCode] = useState(() => searchParams.get('invite') ?? '')
```

- [ ] **Step 2: Run type check**

```bash
cd frontend && npm run build 2>&1 | head -40
```
Expected: No errors

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm test -- --run
```
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/RegisterPage.tsx
git commit -m "feat: pre-fill invite code from ?invite= URL param on RegisterPage"
```

---

## Final Verification

- [ ] **Start dev server and test manually**

```bash
docker compose up
```

1. Navigate to `http://localhost:5173/setup`
2. Enter token `dev-bootstrap-secret-change-in-prod` + email + password → click "Create Admin" → redirects to `/login`
3. Log in as admin → go to Settings → see "Admin" section → click "Generate Invite Link" → copy the link
4. Open incognito → navigate to the copied link → invite code pre-filled on `/register?invite=XXX` → register friend
5. Navigate to `/setup` again → should redirect to `/login` (409 handled)
6. Try to create invite as non-admin → Settings shows no admin section

- [ ] **Run full backend test suite**

```bash
docker compose exec backend pytest -v --cov=src --cov-report=term-missing
```
Expected: All green, 80%+ coverage

- [ ] **Run full frontend test suite**

```bash
cd frontend && npm test -- --run
```
Expected: All green
