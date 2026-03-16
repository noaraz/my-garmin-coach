# Auth — CLAUDE

## Skill Reference

Install when implementing this feature:
```
npx playbooks add skill jezweb/claude-skills --skill fastapi
```
Has production-tested JWT + bcrypt + OAuth2 patterns for this exact stack.

## Auth Dependency Pattern

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> UserDB:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401)
    user = session.get(UserDB, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401)
    return user
```

## Garmin Connect Flow

```
1. User clicks "Connect Garmin" in Settings
2. Frontend shows email/password form (over HTTPS)
3. POST /api/garmin/connect { email, password }
4. Backend: garth.login(email, password)
5. Backend: encrypt tokens with user's Fernet key
6. Backend: store encrypted tokens in DB
7. Backend: discard email + password from memory
8. Return { connected: true }
```

## Security Checklist (Before Deploying)

- [ ] HTTPS via Let's Encrypt
- [ ] GARMINCOACH_SECRET_KEY + JWT_SECRET set as strong random values
- [ ] CORS restricted to your domain
- [ ] Rate limiting on /api/auth/*
- [ ] HttpOnly + Secure + SameSite=Strict on refresh cookie
- [ ] .env NOT in git
- [ ] Database NOT publicly accessible
- [ ] Registration is invite-only

## Gotchas & Patterns (added 2026-03-09)

### JWT must include `email` claim
Frontend's `userFromPayload` in `AuthContext.tsx` requires both `sub` (user_id) and `email`
from the JWT payload. If `email` is missing, `userFromPayload` returns `null` → `setUser(null)` →
ProtectedRoute redirects back to `/login` after a successful login creating an infinite redirect loop.
Always call `create_access_token(user.id, user.email)` — never the one-arg form.

### client.ts 401 handler must be token-aware
A global 401 handler that always redirects to `/login` breaks the login form — a failed login
attempt (wrong password) also returns 401, which would redirect before the form can show an error.
Guard the redirect: only redirect if there was a stored token (expired authenticated session):
```typescript
if (res.status === 401) {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  if (token) {          // ← only redirect when session was authenticated
    window.location.href = '/login'
    return undefined as T
  }
}
```

### FastAPI error format — always parse `detail`
Backend returns `{"detail": "Invalid credentials"}`. Parse `body.detail` in the error handler
rather than `JSON.stringify(body)`, or the UI shows the raw JSON string.

### bcrypt 5.x — use `bcrypt` directly, not passlib
`passlib` doesn't support `bcrypt` ≥ 5.0. Use `bcrypt.gensalt()`, `bcrypt.hashpw()`,
`bcrypt.checkpw()` directly in `auth/passwords.py`.

### Vite proxy inside Docker — use service name
`VITE_PROXY_TARGET=http://backend:8000` in docker-compose.yml frontend environment.
`localhost` inside the container resolves to the container itself, not the host or the
backend container.

### Bootstrap endpoint — needed for Render free plan (added 2026-03-12, updated 2026-03-16)

**Problem**: Render free plan has no Shell access. `scripts/create_admin.py` requires shell.
The invite system is a chicken-and-egg: register needs invite code, create invite needs login, login needs a user.

**Solution**: `POST /api/v1/auth/bootstrap`
- *(Updated 2026-03-16)* Accepts `{ setup_token, google_id_token }` — email/password form removed
- Checks `SELECT COUNT(*) FROM user` — if > 0, returns HTTP 409 (permanently locked)
- Verifies `setup_token` against `BOOTSTRAP_SECRET` env var — 403 on mismatch
- Verifies `google_id_token` with Google — creates user from Google profile
- Creates first user (admin) + 5 invite codes, returns invite codes in response
- No auth required (that's the point)
- Safe: once any user exists, endpoint is a permanent no-op

**Files touched**:
- `backend/src/auth/service.py` — `bootstrap(request, session)` function
- `backend/src/auth/schemas.py` — `BootstrapRequest` + `BootstrapResponse`
- `backend/src/api/routers/auth.py` — `POST /bootstrap` route
- `backend/tests/integration/test_api_auth.py` — bootstrap tests

**Usage after deploy**:
```bash
# Get your Google id_token from the SetupPage UI, then:
curl -X POST https://garmincoach.onrender.com/api/v1/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"setup_token": "your-bootstrap-secret", "google_access_token": "<token from SetupPage>"}'
# Returns: {"invite_codes": ["abc123", ...]}
```

## Google OAuth (added 2026-03-16, updated 2026-03-17)

### Overview

Email/password login and registration are removed. All authentication flows through Google OAuth
using the **access token + userinfo** approach (not ID token verification).

```
Endpoint:  POST /api/v1/auth/google
Body:      { access_token: string, invite_code?: string }
Response:  { access_token, refresh_token, token_type }
```

- New user (first time): requires `invite_code`. 403 if missing or invalid.
- Existing user: `invite_code` ignored. Matched by `google_oauth_sub` only (never email fallback).

### Why access token + userinfo (not ID token)

The `google-auth` library's `verify_oauth2_token` approach requires `GOOGLE_CLIENT_ID` on the
backend and is tightly coupled to the specific OAuth client. The userinfo endpoint approach:
- No `GOOGLE_CLIENT_ID` needed on backend
- Works with any valid Google access token
- Simpler: one HTTP call, no cryptographic verification machinery

### Backend pattern

```python
import httpx

_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

async def _google_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google access token")
    data = resp.json()   # has "sub", "email", "email_verified", "name", etc.
    if not data.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")
    return data
```

User lookup: `WHERE google_oauth_sub = :sub` **only**.
**Never fall back to email** — that allows any Google account with a matching email to take over
an existing account (account takeover via OR query, fixed 2026-03-17).

If sub doesn't match and `invite_code` provided and valid → create new user.

### User model changes

```python
class User(SQLModel, table=True):
    google_oauth_sub: str | None = Field(default=None, unique=True, index=True)
    password_hash: str | None = Field(default=None)   # nullable — Google users have no password
```

Requires Alembic migration — see "Alembic + SQLite" section below.

### Frontend patterns — React 19 gotcha

**`useGoogleLogin` from `@react-oauth/google` crashes React 19** with `Uncaught _.od`.
Do NOT use `GoogleLogin` component either (renders in user's Google account language, ignores `locale` prop).

**Correct approach**: use `useGoogleOAuth` (low-level context hook) + call GIS directly:

```tsx
import { useGoogleOAuth } from '@react-oauth/google'

const { clientId, scriptLoadedSuccessfully } = useGoogleOAuth()

const handleSignIn = () => {
  if (!scriptLoadedSuccessfully) return
  const client = (window as any).google.accounts.oauth2.initTokenClient({
    client_id: clientId,
    scope: 'openid profile email',
    callback: async (response: { access_token?: string; error?: string }) => {
      if (response.error || !response.access_token) { setError('Google sign-in failed'); return }
      await googleLogin(response.access_token, inviteCode)
    },
  })
  client.requestAccessToken()
}
```

This gives a fully custom button (English text, any styling) that works with React 19.

`googleLogin(accessToken, inviteCode?)` in `AuthContext` — replaces `login` and `register`.

Wrap `<App>` in `<GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>`.

### Test mock patterns (added 2026-03-17)

**Backend tests** — mock `_google_userinfo`, not `id_token.verify_oauth2_token`:

```python
# ✅ Correct mock target
@patch("src.auth.service._google_userinfo", return_value=FAKE_GOOGLE_IDINFO)

# For error cases
@patch("src.auth.service._google_userinfo", side_effect=HTTPException(status_code=401, detail="..."))
```

Request field names: `access_token` (not `id_token`) for `GoogleAuthRequest`;
`google_access_token` (not `google_id_token`) for `BootstrapRequest`.

**Frontend tests (`LoginPage.test.tsx`)** — mock `useGoogleOAuth` + GIS global:

```tsx
vi.mock('@react-oauth/google', () => ({
  useGoogleOAuth: () => ({ clientId: 'test-client-id', scriptLoadedSuccessfully: true }),
  GoogleOAuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// In beforeEach: capture the GIS callback
let capturedTokenCallback: ((r: { access_token?: string; error?: string }) => void) | null = null
let mockRequestAccessToken: ReturnType<typeof vi.fn>

beforeEach(() => {
  mockRequestAccessToken = vi.fn()
  ;(window as unknown as Record<string, unknown>).google = {
    accounts: { oauth2: {
      initTokenClient: vi.fn((config) => {
        capturedTokenCallback = config.callback
        return { requestAccessToken: mockRequestAccessToken }
      }),
    }},
  }
})

// In test: click button → call captured callback
await user.click(screen.getByRole('button', { name: /sign in with google/i }))
expect(mockRequestAccessToken).toHaveBeenCalled()
await act(async () => { capturedTokenCallback?.({ access_token: 'fake-token' }) })
```

Do NOT mock `GoogleLogin` component — `LoginPage` doesn't use it.

### Google Console setup

- OAuth 2.0 Client ID (Web application type)
- Authorized JavaScript origins: your deployed domain + `http://localhost:5173` for dev
- Audience: External
- Publishing status: Published (avoids 7-day token expiry and test-user list requirement)
- `VITE_GOOGLE_CLIENT_ID` in frontend env (Vite bakes it in at build time)
- `GOOGLE_CLIENT_ID` in backend env (not used for auth, but good to have for future)

### Admin user creation (scripts)
```bash
docker compose exec backend python - <<'EOF'
import asyncio, secrets
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.auth.models import User, InviteCode
from src.auth.passwords import hash_password
from src.core.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        user = User(email="admin@garmincoach.com", password_hash=hash_password("YourPassword123"))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        code = secrets.token_urlsafe(16)
        invite = InviteCode(code=code, created_by=user.id)
        session.add(invite)
        await session.commit()
        print(f"User id={user.id}, invite code={code}")

asyncio.run(main())
EOF
```
