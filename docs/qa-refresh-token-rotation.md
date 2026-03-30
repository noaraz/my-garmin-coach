# QA — Refresh Token Rotation + Auto-Login

**Feature branch:** `feature/refresh-token-rotation`
**Prerequisites:** Backend + frontend running locally (`docker compose up --build`)

---

## Setup

Open two windows before starting:
- **Browser** at `http://localhost:5173`
- **DevTools** → Application → Cookies → `localhost`

---

## Scenario 1: Login sets httpOnly cookie, not localStorage

**Steps:**
1. Navigate to `/login`
2. Sign in with Google
3. Open DevTools → Application → Cookies → `localhost`
4. Open DevTools → Application → Local Storage → `localhost`

**Expected:**
- Cookie named `refresh_token` is present with **HttpOnly ✅** and **SameSite: Lax**
- Cookie `Path` is `/api/v1/auth` (not `/`)
- `localStorage` contains `access_token`
- `localStorage` does **not** contain `refresh_token`

---

## Scenario 2: Access token decoded — correct claims and expiry

**Steps:**
1. While logged in, open DevTools → Console
2. Run:
   ```js
   const [, payload] = localStorage.access_token.split('.')
   console.log(JSON.parse(atob(payload)))
   ```

**Expected:**
```js
{ sub: "1", email: "you@gmail.com", is_admin: true/false, exp: <unix timestamp> }
```
- `new Date(exp * 1000)` is approximately 30 minutes from now
- `refresh_token` is **not** a field in this payload

---

## Scenario 3: Silent refresh — expired access token does not bounce user to login

**Steps:**
1. While logged in, open DevTools → Console
2. Corrupt the access token to simulate expiry:
   ```js
   localStorage.access_token = localStorage.access_token.slice(0, -10) + 'XXXXXXXXXX'
   ```
3. Navigate to `/` (Calendar page)

**Expected:**
- The `GET /api/v1/calendar` call gets 401
- `tryRefreshToken()` silently calls `POST /api/v1/auth/refresh` with the cookie
- A new `access_token` is written to `localStorage`
- The original calendar request is retried and succeeds
- User stays on the Calendar page — **no redirect to `/login`**

---

## Scenario 4: Silent refresh on mount — expired token restored on page load

**Steps:**
1. While logged in, corrupt the access token (same as Scenario 3 step 2)
2. Hard-refresh the page (Cmd+Shift+R)

**Expected:**
- `AuthContext` detects the expired token on mount
- Calls `tryRefreshToken()` silently
- Session is restored — user lands on Calendar, not `/login`

---

## Scenario 5: Refresh fails when cookie absent — user redirected to login

**Steps:**
1. While logged in, delete the `refresh_token` cookie in DevTools (right-click → Delete)
2. Corrupt the access token (Scenario 3 step 2)
3. Navigate to `/`

**Expected:**
- `GET /api/v1/calendar` gets 401
- `tryRefreshToken()` calls `POST /api/v1/auth/refresh` — gets 401 (no cookie)
- `access_token` is removed from `localStorage`
- User is redirected to `/login`

---

## Scenario 6: Logout revokes token and clears cookie

**Steps:**
1. While logged in, note the `refresh_token` cookie value
2. Click logout (Sidebar or bottom tab bar)

**Expected:**
- `POST /api/v1/auth/logout` is called (visible in DevTools → Network)
- `refresh_token` cookie is **gone** from DevTools
- `access_token` is **gone** from localStorage
- User is on `/login`

**Verify revocation:**
3. Manually re-add the old cookie value in DevTools (Application → Cookies → double-click value)
4. Set `localStorage.access_token` to any value
5. Navigate to `/`

**Expected:**
- Silent refresh is attempted, `POST /api/v1/auth/refresh` returns 401
- User is redirected to `/login` (revoked token rejected)

---

## Scenario 7: Logout is idempotent — no error when cookie absent

**Steps:**
1. Delete the `refresh_token` cookie in DevTools
2. Click logout

**Expected:**
- No error in console
- User is redirected to `/login` normally
- `POST /api/v1/auth/logout` returns `200 {"ok": true}`

---

## Scenario 8: Token rotation — each refresh issues a new cookie

**Steps:**
1. While logged in, note the `refresh_token` cookie value (copy it)
2. Corrupt the access token (Scenario 3 step 2)
3. Navigate to `/` (triggers silent refresh)
4. Check the `refresh_token` cookie value again

**Expected:**
- Cookie value has **changed** — new token was issued
- The old cookie value, if submitted manually, returns 401 (old token revoked)

---

## Scenario 9: Sign out of all devices

**Steps:**
1. Log in on **Tab A** and **Tab B** (same browser, two tabs)
2. In Tab A: navigate to Settings
3. Click **"Sign out of all devices"** → confirm

**Expected:**
- Tab A: `POST /api/v1/auth/logout-all` called, then `POST /api/v1/auth/logout` — redirected to `/login`
- Tab B: on next navigation or API call, silent refresh returns 401 (all tokens revoked) → redirected to `/login`
- Cookie cleared in both tabs

---

## Scenario 10: Theft detection — reused revoked token revokes all sessions

**Steps:**
1. Log in and note the `refresh_token` cookie value
2. Log out (revokes the token)
3. Log in again on a second tab (new session, new cookie)
4. In the first tab: re-add the old (revoked) cookie value in DevTools
5. In the first tab: corrupt the access token and navigate to `/`

**Expected:**
- `POST /api/v1/auth/refresh` detects `revoked=True` on the submitted token
- **All** refresh tokens for this user are revoked (including the active session in Tab 2)
- First tab is redirected to `/login`
- Tab 2: on next API call, its refresh also fails → redirected to `/login`
- Backend logs a warning: `"Refresh token reuse detected for user_id=<N>"`

---

## Checklist Summary

| # | Scenario | Pass |
|---|----------|------|
| 1 | Login sets httpOnly cookie, no refresh_token in localStorage | ⬜ |
| 2 | Access token has correct claims and 30-min expiry | ⬜ |
| 3 | Expired token → silent refresh, stays on page | ⬜ |
| 4 | Expired token on page load → session restored | ⬜ |
| 5 | No cookie + expired token → redirect to login | ⬜ |
| 6 | Logout revokes token and clears cookie | ⬜ |
| 7 | Logout without cookie → 200, no error | ⬜ |
| 8 | Each refresh issues a new cookie (rotation) | ⬜ |
| 9 | Sign out of all devices → all sessions invalidated | ⬜ |
| 10 | Revoked token reuse → all sessions nuked (theft detection) | ⬜ |
