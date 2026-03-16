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
  -d '{"setup_token": "your-bootstrap-secret", "google_id_token": "<token from SetupPage>"}'
# Returns: {"invite_codes": ["abc123", ...]}
```

## Google OAuth (added 2026-03-16)

### Overview

Email/password login and registration are removed. All authentication flows through Google OAuth.

```
Endpoint:  POST /api/v1/auth/google
Body:      { id_token: string, invite_code?: string }
Response:  { access_token, refresh_token, token_type }
```

- New user (first time): requires `invite_code`. 403 if missing or invalid.
- Existing user: `invite_code` ignored. Matched by `google_oauth_sub` first, then by email (migration path).
- Backend verifies token with `google.oauth2.id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)`.

### Backend patterns

```python
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

payload = id_token.verify_oauth2_token(
    token, google_requests.Request(), settings.google_client_id
)
google_sub = payload["sub"]
email = payload["email"]
```

User lookup order:
1. `WHERE google_oauth_sub = :sub`
2. `WHERE email = :email` (migration: links existing account to Google identity)

If neither match and `invite_code` is provided and valid → create new user.

### User model changes

```python
class User(SQLModel, table=True):
    google_oauth_sub: str | None = Field(default=None, unique=True, index=True)
    password_hash: str | None = Field(default=None)   # nullable — legacy only
```

### Frontend patterns

```tsx
// @react-oauth/google
import { GoogleLogin } from '@react-oauth/google'

<GoogleLogin
  onSuccess={async (credentialResponse) => {
    await googleLogin(credentialResponse.credential!, inviteCode)
  }}
  onError={() => setError('Google sign-in failed')}
/>
```

`googleLogin(idToken, inviteCode?)` in `AuthContext` — replaces `login` and `register`.

Wrap `<App>` in `<GoogleOAuthProvider clientId={VITE_GOOGLE_CLIENT_ID}>`.

### Google Console setup

- OAuth 2.0 Client ID (Web application type)
- Authorized JavaScript origins: your deployed domain + `http://localhost:5173` for dev
- Audience: External
- Publishing status: Published (avoids 7-day token expiry and test-user list requirement)
- `VITE_GOOGLE_CLIENT_ID` in frontend env; `GOOGLE_CLIENT_ID` in backend env

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
