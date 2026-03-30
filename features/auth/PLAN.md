# Auth — PLAN

> **Updated 2026-03-16**: Email/password auth has been superseded by Google OAuth.
> `POST /auth/login` and `POST /auth/register` are removed.
> `POST /auth/google` handles both login and first-time registration (with invite code).
> `POST /auth/bootstrap` now accepts a `google_id_token` instead of email/password.
> See the **Google OAuth Migration** section below and `features/auth/CLAUDE.md` for patterns.

## Description

User accounts with Google OAuth authentication, invite-only registration, per-user data
isolation, and encrypted Garmin token storage. Required before deploying the
app for friends.

Each user gets their own profile, zones, workouts, and Garmin connection.
Garmin OAuth tokens are encrypted at rest using a per-user key derived from
a server-side master secret.

The first user (admin) is created via a hardened `/setup` page (requires `BOOTSTRAP_SECRET` env var).
Only the admin can generate invite codes for others.

Track progress in **STATUS.md**.

---

## Tasks

### Auth Module (original email/password — superseded by Google OAuth)
- [x] Write `auth/passwords.py` — hash_password, verify_password (pure logic) *(no longer used for login)*
- [x] Write `auth/jwt.py` — create_access_token, create_refresh_token, decode_token
- [x] Write `auth/models.py` — User, InviteCode SQLModel tables
- [x] Write `auth/schemas.py` — LoginRequest, RegisterRequest, TokenResponse *(LoginRequest/RegisterRequest removed)*
- [x] Write all tests in `test_api_auth.py` (see test table)
- [x] Run tests → RED
- [x] Implement `auth/service.py` — register, login, refresh, create_invite *(register/login replaced by google_auth)*
- [x] Implement `auth/dependencies.py` — get_current_user
- [x] Implement `api/routers/auth.py` — /api/auth/* endpoints
- [x] Run tests → GREEN

### Google OAuth Migration (2026-03-16)
- [x] Remove `POST /auth/login` and `POST /auth/register` endpoints
- [x] Add `POST /auth/google { access_token, invite_code? }` — login + first-time register
- [x] Update `POST /auth/bootstrap` to accept `{ setup_token, google_access_token }` instead of email/password
- [x] Add `google_oauth_sub` (unique) to `User` model; make `password_hash` nullable
- [x] Backend: verify token via httpx GET `/oauth2/v3/userinfo` (access token + userinfo approach)
- [x] Backend: user lookup by `google_oauth_sub` **only** — no email fallback (prevents account takeover)
- [x] Backend: reject tokens where `email_verified != True`
- [x] Frontend: add `@react-oauth/google` — custom button via `useGoogleOAuth` on LoginPage, RegisterPage, SetupPage
- [x] Frontend: `googleLogin(accessToken, inviteCode?)` in AuthContext replaces login/register functions

### Garmin Token Encryption
- [x] Write all tests in `test_garmin_connect_flow.py` (see test table)
- [x] Run tests → RED
- [x] Implement encryption in garmin/session.py (Fernet per-user key)
- [x] Implement `api/routers/garmin_connect.py` — connect, status, disconnect
- [x] Run tests → GREEN

### Retrofit Existing Code
- [x] Add `user_id` FK to AthleteProfile, HRZone, PaceZone, WorkoutTemplate, ScheduledWorkout
- [x] Write DB migration (add column, set existing rows to admin user)
- [x] Add `Depends(get_current_user)` to ALL existing route handlers
- [x] Filter ALL existing queries by `current_user.id`
- [x] Update ALL existing integration test fixtures to include auth headers
- [x] Run ALL tests (new + existing) → GREEN

### Frontend
- [x] Add login page
- [x] Add registration page (with invite code field)
- [x] Add auth context/provider to React app
- [x] Add auth header to all API client calls
- [x] Settings page (`/settings`) with Garmin Connect section
  - Always shows connection status (red/green dot badge)
  - Not connected: email + password form → `POST /api/v1/garmin/connect`
  - Connected: info text + Disconnect button → `POST /api/v1/garmin/disconnect`
  - Status polled on mount via `GET /api/v1/garmin/status`

### Bootstrap + Admin + Invite UI
Full plan: `docs/superpowers/plans/2026-03-16-admin-bootstrap-invite.md`

### Refresh Token Rotation + Auto-Login (2026-03-29)
Design spec: `docs/superpowers/specs/2026-03-29-refresh-token-rotation-design.md`

- [x] Phase 1: Add `RefreshToken` SQLModel + Alembic migration
- [x] Phase 2a: `jwt.py` — add `hash_token`, remove `create_refresh_token`
- [x] Phase 2b: `schemas.py` — remove `RefreshRequest`, consolidate `TokenResponse` → `AccessTokenResponse`
- [x] Phase 2c: `service.py` — add rotation/revocation helpers, fix `google_auth` flush, update `reset_admins`
- [x] Phase 2d: `routers.py` — httpOnly cookie on login/refresh, new logout + logout-all endpoints
- [x] Phase 3a: `client.ts` — `credentials: 'include'`, export `tryRefreshToken`, retry guard
- [x] Phase 3b: `AuthContext.tsx` — silent refresh on mount, async logout
- [x] Phase 3c: Update logout callers (Sidebar, BottomTabBar, SettingsPage)
- [x] Phase 3d: SettingsPage — "Sign out of all devices" button

- [x] Add `is_admin: bool = False` to `User` model
- [x] Add `bootstrap_secret` to `Settings` (env var `BOOTSTRAP_SECRET`)
- [x] Add `BootstrapRequest`/`BootstrapResponse` schemas; add `is_admin` to `UserResponse`
- [x] Add `is_admin` claim to JWT access token; update callers
- [x] Add `bootstrap()` service (403 wrong token, 409 users exist, creates admin + 5 invite codes)
- [x] Add `POST /api/v1/auth/bootstrap` route; gate `POST /invite` to admin only
- [x] Add 5 new backend tests (bootstrap success/409/403, invite blocked, me.is_admin)
- [x] Add `BootstrapResponse` to `types.ts`; add `bootstrapAdmin` + `createInvite` to `client.ts`
- [x] Update `AuthContext` — decode `is_admin` from JWT, expose `isAdmin: boolean`
- [x] Create `SetupPage.tsx` + add `/setup` public route in `App.tsx`
- [x] Add Admin section to `SettingsPage` (admin only: generate invite → copyable link)
- [x] Update `RegisterPage` — pre-fill invite code from `?invite=` URL param (read from URL, field hidden)

---

## Data Model

### User
```
id, email(unique), google_oauth_sub(unique), password_hash(bcrypt, nullable — legacy only),
is_active, is_admin(default=False), failed_login_attempts, locked_until, created_at
```
> `password_hash` is nullable as of the Google OAuth migration (2026-03-16).
> `google_oauth_sub` is the primary identity claim. New users have no password hash.

### InviteCode
```
id, code(unique), created_by→User, used_by→User(null), used_at(null)
```

### Garmin Token Storage (on AthleteProfile)
```
garmin_oauth_token_encrypted    TEXT (Fernet encrypted)
garmin_connected                BOOLEAN
```

### Encryption Scheme
```python
key = SHA256(GARMINCOACH_SECRET_KEY + ":" + str(user_id))
cipher = Fernet(base64_urlsafe_encode(key))
encrypted = cipher.encrypt(token_json.encode())
```

### Environment Secrets
| Env var | Purpose |
|---------|---------|
| `JWT_SECRET` | JWT signing key |
| `GARMINCOACH_SECRET_KEY` | Garmin token encryption master key |
| `BOOTSTRAP_SECRET` | Admin bootstrap endpoint token |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `FIXIE_URL` | Fixie proxy URL — optional fallback only; curl_cffi chrome120 TLS fingerprint handles Akamai without it |

---

## Tests

### test_api_auth.py

> Tests marked ~~strikethrough~~ belong to the removed email/password flow and are no longer active.

| Test | Scenario |
|------|----------|
| ~~`test_register_new_user`~~ | ~~valid invite → 201~~ *(removed)* |
| ~~`test_register_duplicate_email`~~ | ~~→ 409~~ *(removed)* |
| ~~`test_register_invalid_invite`~~ | ~~→ 403~~ *(removed)* |
| ~~`test_register_weak_password`~~ | ~~< 8 chars → 422~~ *(removed)* |
| ~~`test_login_success`~~ | ~~→ 200 + tokens~~ *(removed)* |
| ~~`test_login_wrong_password`~~ | ~~→ 401~~ *(removed)* |
| ~~`test_login_nonexistent_user`~~ | ~~→ 401~~ *(removed)* |
| `test_protected_with_token` | valid JWT → 200 |
| `test_protected_no_token` | → 401 |
| `test_protected_expired` | → 401 |
| `test_refresh_token` | → new access_token |
| `test_user_data_isolation` | user A ≠ user B |
| ~~`test_account_lockout`~~ | ~~5 failures → locked~~ *(no longer applicable — no password)* |
| `test_bootstrap_creates_admin_and_invite_codes` | empty DB + valid token → 201 + 5 codes |
| `test_bootstrap_returns_409_when_users_exist` | users exist → 409 |
| `test_bootstrap_returns_403_on_wrong_token` | wrong token → 403 |
| `test_me_includes_is_admin` | bootstrap admin login → is_admin: true |
| `test_invite_blocked_for_non_admin` | non-admin POST /invite → 403 |

#### Google OAuth tests (added 2026-03-16)

| Test | Scenario |
|------|----------|
| `test_google_login_new_user_with_invite` | valid id_token + invite → 201 + tokens |
| `test_google_login_existing_user` | known google_oauth_sub → 200 + tokens |
| `test_google_login_new_user_no_invite` | no invite code → 403 |
| `test_google_login_invalid_token` | bad id_token → 401 |
| `test_google_login_invalid_invite` | unknown invite code → 403 |
| `test_bootstrap_google_creates_admin` | valid setup_token + google_id_token → 201 + invite codes |

### test_garmin_connect_flow.py

| Test | Scenario |
|------|----------|
| `test_connect_encrypts_token` | POST → encrypted in DB |
| `test_status_connected` | after connect → true |
| `test_disconnect_removes` | POST → removed |
| `test_decryption_works` | encrypt → decrypt → valid |
| `test_different_users_different_keys` | user A ≠ user B |

---

## Implementation Files

```
backend/src/auth/
  models.py       — User (google_oauth_sub, password_hash nullable), InviteCode
  schemas.py      — GoogleAuthRequest, BootstrapRequest (google_id_token), TokenResponse
  service.py      — google_auth(), bootstrap(), refresh, create_invite
  jwt.py          — create_access_token, create_refresh_token, decode_token
  passwords.py    — hash_password, verify_password (legacy / Garmin connect only)
  dependencies.py — get_current_user

backend/src/api/routers/
  auth.py         — POST /google, POST /bootstrap, POST /refresh, POST /invite, GET /me
  garmin_connect.py

frontend/src/pages/
  LoginPage.tsx    — GoogleLogin button
  RegisterPage.tsx — GoogleLogin button + invite from URL param (hidden input)
  SettingsPage.tsx
  SetupPage.tsx    — GoogleLogin button for admin bootstrap

frontend/src/contexts/
  AuthContext.tsx  — googleLogin(idToken, inviteCode?), isAdmin, user

frontend/src/components/auth/
  ProtectedRoute.tsx

backend/src/core/
  config.py        — bootstrap_secret, google_client_id

frontend/src/api/
  client.ts   (getGarminStatus, connectGarmin, disconnectGarmin, googleLogin, bootstrapAdmin, createInvite)
  types.ts    (GarminStatusResponse, BootstrapResponse)
```
