# Refresh Token Rotation + Auto-Login — Design Spec

**Date:** 2026-03-29
**Status:** Approved (reviewed by spec-document-reviewer, 3 passes, 15 issues resolved)
**Implementation plan:** `.claude/plans/fizzy-coalescing-dahl.md`

---

## Context

The current auth flow issues a 7-day JWT refresh token stored in `localStorage`. Two problems:
1. **No revocation** — a stolen refresh token stays valid for 7 days with no way to invalidate it
2. **No auto-login** — when the 30-min access token expires the user is bounced to `/login`, even though the refresh token is still valid (the frontend never calls `/auth/refresh`)

This spec replaces stateless JWT refresh tokens with DB-backed opaque tokens stored in `httpOnly` cookies, adds sliding window rotation, and implements silent auto-refresh in the frontend so active users stay logged in transparently.

---

## Goals

- Users stay logged in indefinitely while active (sliding window — refresh token TTL resets on each use)
- Inactive users expire after 7 days
- Refresh tokens can be revoked on logout
- "Sign out of all devices" invalidates every session for a user
- Token theft detected: reuse of a revoked token revokes all sessions for that user
- Refresh token never accessible to JavaScript (`httpOnly` cookie)

---

## Data Model

### New table: `RefreshToken`

```python
class RefreshToken(SQLModel, table=True):
    __tablename__ = "refreshtoken"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, index=True)  # SHA-256 of opaque token
    user_id: int = Field(foreign_key="user.id", index=True)
    expires_at: datetime  # sliding window: reset to now+7d on each rotation
    revoked: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
```

**Token format:** `secrets.token_urlsafe(32)` — opaque random string, not a JWT.
**Storage:** Only `SHA-256(raw_token)` stored in DB. Raw token goes to cookie only.

---

## Cookie Spec

```python
response.set_cookie(
    key="refresh_token", value=raw_token,
    httponly=True,
    secure=settings.environment != "development",
    samesite="lax",
    max_age=7 * 24 * 3600,
    path="/api/v1/auth",
)
```

- `httponly=True` — inaccessible to JavaScript (XSS protection)
- `samesite="lax"` — blocks cross-site POST CSRF; compatible with Google OAuth popup
- `path="/api/v1/auth"` — not sent on calendar/sync calls
- `secure=True` in prod (Render enforces HTTPS); `False` in dev

---

## Commit Ordering Rule

**Always: `session.commit()` first, then `response.set_cookie()`.**

`set_cookie` is in-memory and always succeeds. The DB commit is what can fail. Committing first ensures both rotation writes are atomic before any cookie leaves the server.

---

## Backend Endpoints

### `POST /auth/google` (updated)
- Returns `{"access_token": "..."}` in JSON — **no `refresh_token` field**
- Creates `RefreshToken` DB record; sets `httpOnly` cookie
- Uses `session.flush()` (not `session.commit()`) after `User` creation to get `user.id`; router does single terminal `session.commit()`

### `POST /auth/refresh` (updated)
Reads `refresh_token` cookie. Three explicit cases:

1. Hash **not found in DB** → plain 401
2. Hash found, `revoked=True` → **theft detection**: revoke ALL tokens for `user_id`, log warning, 401
3. Hash found, not revoked, `expires_at < now` → plain 401

Valid path: rotate (revoke old, insert new), `session.commit()`, set new cookie, return `{"access_token": "..."}`.

### `POST /auth/logout` (new)
- Cookie absent → 200 `{"ok": true}` immediately (idempotent)
- Cookie present → revoke token, `session.commit()`, `delete_cookie`
- Does not require access token

### `POST /auth/logout-all` (new)
- Requires valid access token
- Revokes ALL `RefreshToken` rows for `current_user.id`
- Returns `{"revoked": N}`

### `reset_admins` (updated)
Delete order: `RefreshToken` → `InviteCode` → `User` (FK constraint on PostgreSQL).

---

## Service Layer

All DB writes are in service functions that do NOT commit. The router commits exactly once.

```python
create_refresh_token_record(user_id, session) -> str      # returns raw token
rotate_refresh_token(old_hash, user_id, session) -> str   # returns new raw token
revoke_refresh_token(token_hash, session) -> None
revoke_all_refresh_tokens(user_id, session) -> int
```

---

## Frontend

### `client.ts`
- `credentials: 'include'` on all fetches
- Export `tryRefreshToken(): Promise<boolean>` — calls `/auth/refresh`, updates `localStorage.access_token`
- `request()` adds `retried=false` parameter — on 401, try refresh once, retry with `retried=true`; if refresh fails, redirect to login

### `AuthContext` on mount
1. Valid token → restore session immediately
2. Expired token → call `tryRefreshToken()` → if ok, restore; if fail, clear token
3. No token → cold start, `isLoading=false`

Preserve existing `userFromPayload` null-guard throughout.

### `logout` (async)
```typescript
const logout = async () => {
  try { await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' }) } catch {}
  localStorage.removeItem('access_token')
  setUser(null); setAccessToken(null)
}
```
Update `AuthContextValue`: `logout: () => Promise<void>`

### Callers to update
- `Sidebar.tsx` — `async`, `await logout()`, keep `navigate('/login')`
- `BottomTabBar.tsx` — `async () => { setMoreOpen(false); await logout() }`
- `SettingsPage.tsx` — update if logout button present

### Settings — new button
"Sign out of all devices" → confirm → `POST /auth/logout-all` → `await logout()`

---

## Testing

### Backend
`test_login_sets_httponly_cookie`, `test_login_response_has_no_refresh_token_field`, `test_refresh_rotates_token`, `test_refresh_extends_expiry`, `test_refresh_rejects_revoked_token_and_revokes_all`, `test_refresh_rejects_expired_token`, `test_refresh_rejects_unknown_token`, `test_logout_revokes_token`, `test_logout_clears_cookie`, `test_logout_idempotent_no_cookie`, `test_logout_all_revokes_all_tokens`, `test_reset_admins_deletes_refresh_tokens`

### Frontend (Vitest)
`AuthContext_validToken_restoresSession`, `AuthContext_noStoredToken_setsLoadingFalse`, `AuthContext_expiredToken_silentlyRefreshes`, `AuthContext_refreshFails_clearsToken`, `client_401_triesToRefresh_thenRetries`, `client_401_refreshFails_redirectsToLogin`, `client_401_noInfiniteRetry`, `logout_callsBackendEndpoint`

---

## Migration / Rollout

- New `refreshtoken` table — non-destructive, safe on Neon
- Existing users redirected to login once (access token expired, no cookie) — new flow kicks in after
- `TokenResponse` → `AccessTokenResponse` consolidation is a breaking API change; frontend + backend deploy together
- Expired/revoked row cleanup out of scope (acceptable at current scale)
