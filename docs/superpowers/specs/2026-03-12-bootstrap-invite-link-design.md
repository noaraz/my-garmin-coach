# Bootstrap Endpoint & Invite Link UX — Design Spec

**Date:** 2026-03-12
**Status:** Approved

---

## Problem

Two connected blockers prevent deploying GarminCoach to Render and sharing it with friends:

1. **Bootstrap chicken-and-egg**: Registration requires an invite code. Invite codes require an existing user. On Render's free plan there is no shell access, so `scripts/create_admin.py` cannot run. There is no way to create the first user.

2. **Invite UX**: The existing `/invite` endpoint returns a raw code. To share with a friend, the admin must manually construct a URL, tell the friend to visit `/register`, and have them type in the code. This is friction-heavy.

---

## Goals

- Unblock deployment: allow admin account creation on Render with no shell access.
- Make registering as a friend a one-click flow: click link → enter email + password → done.
- Secure the bootstrap endpoint so a random internet user cannot claim admin.

---

## Out of Scope

- Invite management UI (no frontend needed — invite generation is via curl/API).
- Rate limiting on auth endpoints (documented in CLAUDE.md Nice-to-Have, post-deploy).
- Refresh token rotation (post-MVP).

---

## Architecture

### Backend Changes

#### 1. `POST /api/v1/auth/bootstrap` (new, no auth required)

**Request schema (`BootstrapRequest`):**

```json
{
  "email": "you@example.com",
  "password": "YourPass123",
  "bootstrap_secret": "<value of BOOTSTRAP_SECRET env var>"
}
```

**Behavior (in order):**

1. Validate `bootstrap_secret` matches `BOOTSTRAP_SECRET` env var → `403 Forbidden` on mismatch.
2. Count users in DB. If `count > 0` → `409 Conflict` (endpoint permanently locked). Safe to call again.
3. Validate password strength (min 8 chars) → `422` on failure.
4. Create user with bcrypt-hashed password via existing `register` service primitives.
5. Return success.

**Response schema (`BootstrapResponse`):**

```json
{
  "message": "Bootstrap successful. You can now log in."
}
```

**New env vars required (add to `backend/src/core/config.py` `Settings` class):**

| Var | Python field | Example | Purpose |
|-----|-------------|---------|---------|
| `BOOTSTRAP_SECRET` | `bootstrap_secret: str \| None = None` | `openssl rand -hex 32` | Guards the endpoint against unauthorized use |
| `APP_URL` | `app_url: str \| None = None` | `https://garmincoach.onrender.com` | Used to construct shareable invite links (no trailing slash) |

> If `BOOTSTRAP_SECRET` is not set (empty/missing), the endpoint returns `503 Service Unavailable` with message "Bootstrap is not configured." This prevents accidental open access on misconfigured deploys.

---

#### 2. `POST /api/v1/auth/invite` — response update (existing endpoint)

Currently returns: `{ "code": "abc123xyz" }`

Updated to return:

```json
{
  "code": "abc123xyz",
  "invite_link": "https://garmincoach.onrender.com/register?invite=abc123xyz"
}
```

The link is constructed as `{APP_URL}/register?invite={code}`.
If `APP_URL` is not set, `invite_link` is `null` (code still returned, link omitted gracefully).
`APP_URL` is stripped of trailing slash before concatenation to avoid double slashes.

---

### Frontend Changes

#### `RegisterPage.tsx` — URL invite param

**Behavior:**

- On mount, read `invite` from URL query string using `useSearchParams()`.
- If `?invite=CODE` is present:
  - Store code in state (submitted with form).
  - **Do not render the invite code input field at all.** Friend sees only email + password.
- If no `?invite=` param:
  - Render the invite code input field as currently implemented (required, user types it in).

**Error handling:** If the code from the URL is invalid or already used, the backend returns `403`. The frontend displays the existing error message ("Invalid or already used invite code") just as it would for a manually entered bad code. The field being hidden does not change error UX — the error still shows.

---

## Admin Workflow (Post-Deploy)

```bash
# Step 1: Bootstrap (one-time, before any user exists)
curl -X POST https://garmincoach.onrender.com/api/v1/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "YourSecurePass123",
    "bootstrap_secret": "<your BOOTSTRAP_SECRET>"
  }'
# → { "message": "Bootstrap successful. You can now log in." }

# Step 2: Log in, capture access token
TOKEN=$(curl -s -X POST https://garmincoach.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"YourSecurePass123"}' \
  | jq -r '.access_token')

# Step 3: Generate an invite link (repeat per friend)
curl -s -X POST https://garmincoach.onrender.com/api/v1/auth/invite \
  -H "Authorization: Bearer $TOKEN"
# → { "code": "abc123xyz", "invite_link": "https://garmincoach.onrender.com/register?invite=abc123xyz" }
```

Send the `invite_link` to the friend. They click it, see email + password fields, register, done.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/src/auth/schemas.py` | Add `BootstrapRequest`, `BootstrapResponse`; update `InviteResponse` to include `invite_link: str \| None` |
| `backend/src/auth/service.py` | Add `bootstrap(request, session)` function; update `create_invite()` to accept and use `app_url: str \| None` |
| `backend/src/api/routers/auth.py` | Add `POST /bootstrap` route; update `/invite` to pass `APP_URL` to service |
| `backend/tests/integration/test_api_auth.py` | Add bootstrap tests (see below) |
| `frontend/src/pages/RegisterPage.tsx` | Read `?invite=` via `useSearchParams`, hide field when pre-filled |
| `frontend/src/pages/RegisterPage.test.tsx` | Add tests for URL-param flow |

---

## Tests

### Backend (integration)

| Test | Expected |
|------|----------|
| `test_bootstrap_creates_admin_user` | 200, user exists in DB |
| `test_bootstrap_wrong_secret_returns_403` | 403 |
| `test_bootstrap_locked_after_first_user_returns_409` | 409 |
| `test_bootstrap_missing_secret_env_returns_503` | 503 |
| `test_bootstrap_weak_password_returns_422` | 422 |
| `test_invite_response_includes_invite_link` | `invite_link` contains `APP_URL + /register?invite=` |
| `test_invite_response_link_null_without_app_url` | `invite_link` is null when APP_URL not set |

### Frontend (Vitest + RTL)

| Test | Expected |
|------|----------|
| `test_register_invite_field_hidden_when_url_param_present` | Input `[name="invite_code"]` not in DOM |
| `test_register_invite_field_visible_without_url_param` | Input `[name="invite_code"]` present and required |
| `test_register_submits_invite_from_url_param` | Form POST includes code from URL, not from field |

---

## Verification

1. Run `pytest tests/integration/test_api_auth.py -v` — all bootstrap + invite tests green.
2. Run `npm test -- --run` — RegisterPage tests green.
3. Manual: deploy to Render staging, run bootstrap curl, confirm 409 on second call.
4. Manual: generate invite link, open in incognito, confirm only email + password fields shown, complete registration, confirm can log in.
