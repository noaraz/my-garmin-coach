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
