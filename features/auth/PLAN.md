# Auth — PLAN

## Description

User accounts with JWT authentication, invite-only registration, per-user data
isolation, and encrypted Garmin token storage. Required before deploying the
app for friends.

Each user gets their own profile, zones, workouts, and Garmin connection.
Garmin OAuth tokens are encrypted at rest using a per-user key derived from
a server-side master secret.

Track progress in **STATUS.md**.

---

## Tasks

### Auth Module
- [x] Write `auth/passwords.py` — hash_password, verify_password (pure logic)
- [x] Write `auth/jwt.py` — create_access_token, create_refresh_token, decode_token
- [x] Write `auth/models.py` — User, InviteCode SQLModel tables
- [x] Write `auth/schemas.py` — LoginRequest, RegisterRequest, TokenResponse
- [x] Write all tests in `test_api_auth.py` (see test table)
- [x] Run tests → RED
- [x] Implement `auth/service.py` — register, login, refresh, create_invite
- [x] Implement `auth/dependencies.py` — get_current_user
- [x] Implement `api/routers/auth.py` — /api/auth/* endpoints
- [x] Run tests → GREEN

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

---

## Data Model

### User
```
id, email(unique), password_hash(bcrypt), is_active,
failed_login_attempts, locked_until, created_at
```

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

---

## Tests

### test_api_auth.py

| Test | Scenario |
|------|----------|
| `test_register_new_user` | valid invite → 201 |
| `test_register_duplicate_email` | → 409 |
| `test_register_invalid_invite` | → 403 |
| `test_register_weak_password` | < 8 chars → 422 |
| `test_login_success` | → 200 + tokens |
| `test_login_wrong_password` | → 401 |
| `test_login_nonexistent_user` | → 401 |
| `test_protected_with_token` | valid JWT → 200 |
| `test_protected_no_token` | → 401 |
| `test_protected_expired` | → 401 |
| `test_refresh_token` | → new access_token |
| `test_user_data_isolation` | user A ≠ user B |
| `test_account_lockout` | 5 failures → locked |

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
  models.py, schemas.py, service.py, jwt.py, passwords.py, dependencies.py

backend/src/api/routers/
  auth.py, garmin_connect.py

frontend/src/pages/
  LoginPage.tsx, RegisterPage.tsx, SettingsPage.tsx

frontend/src/contexts/
  AuthContext.tsx

frontend/src/components/auth/
  ProtectedRoute.tsx

frontend/src/api/
  client.ts  (getGarminStatus, connectGarmin, disconnectGarmin, loginUser, registerUser)
  types.ts   (GarminStatusResponse)
```

### Bootstrap + Invite Link UX
- [ ] Add `bootstrap_secret` and `app_url` to `Settings` in `backend/src/core/config.py`; update `.env.example`
- [ ] Add `BootstrapRequest`, `BootstrapResponse` schemas; update `InviteResponse` with `invite_link: str | None`
- [ ] Add `bootstrap()` service function to `auth/service.py`
- [ ] Update `create_invite()` to return `(InviteCode, invite_link | None)`
- [ ] Add `POST /api/v1/auth/bootstrap` route (protected by `BOOTSTRAP_SECRET` env var)
- [ ] Update `POST /api/v1/auth/invite` to return `invite_link`
- [ ] Tests in `test_api_auth.py`: bootstrap success, wrong secret 403, locked 409, unconfigured 503, weak password 422, invite_link present/absent
- [ ] Frontend: `RegisterPage.tsx` reads `?invite=` from URL, hides invite code field when pre-filled
- [ ] Frontend: Tests in `frontend/src/tests/RegisterPage.test.tsx`
