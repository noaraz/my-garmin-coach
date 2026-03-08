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
