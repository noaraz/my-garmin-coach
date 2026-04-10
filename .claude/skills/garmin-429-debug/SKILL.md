---
name: garmin-429-debug
description: >
  Debug Garmin SSO 429 / bot-detection errors in GarminCoach. Use this skill
  whenever Garmin Connect fails in production or locally with a 429, "Too Many
  Requests", "GarthHTTPError", or "Akamai" in the error. Also trigger for any
  error from sso.garmin.com during login, connectapi.garmin.com during sync,
  or when POST /api/v1/garmin/connect returns 400/503 unexpectedly. Don't wait
  for the user to ask — if Garmin connect or sync is failing, invoke this skill
  immediately.
---

# Garmin 429 / Bot-Detection Debug

Garmin uses **Akamai Bot Manager** which blocks based on:
1. **TLS fingerprint** — Python `requests` default TLS is fingerprinted and blocked
2. **Datacenter IPs** — Render's shared IPs may be blocked on some endpoints

**Critical insight: different Garmin subdomains have different Akamai configs.**

| Subdomain | curl_cffi (chrome TLS) | Standard Python TLS | Notes |
|-----------|----------------------|---------------------|-------|
| `sso.garmin.com` | ✅ Allowed | ❌ Blocked | SSO login |
| `connectapi.garmin.com` (API calls) | ✅ Allowed | ❌ Blocked | Regular API via `client.sess` |
| `connectapi.garmin.com` (OAuth exchange) | ❌ Blocked | ✅ Allowed | Token refresh via `GarminOAuth1Session` |

**Current fix**: `FINGERPRINT_SEQUENCE` in `backend/src/garmin/client_factory.py` — tries
`chrome136 → safari15_5 → edge101 → chrome120 → chrome99`. Attempt 2+ waits
`random.uniform(30, 45)` s before calling `client.login()` to mimic human form-fill time.
Proxy (Fixie) applied only on the last attempt. Token exchange is intentionally NOT overridden —
garth's native `sso.exchange()` uses standard Python TLS via `GarminOAuth1Session`, which
Akamai allows on the exchange endpoint.

---

## Step 0 — Check which library raises the 429

> **Auto-reconnect is live (2026-03-29).** When exchange 429 occurs, `sync_all` triggers `attempt_auto_reconnect()` — re-logins using stored encrypted credentials, gets fresh tokens, retries the sync. Three layers of storm prevention: (1) early-exit on first exchange 429, (2) 30-min module-level cooldown, (3) in-process client cache per user. Token persistence alone does NOT fix exchange 429s (it saves the stale expired token). The real fix is auto-reconnect + exchange storm prevention. See `backend/src/garmin/auto_reconnect.py`.

**This is the most important diagnostic step.** Look at the stack trace bottom:

| Stack trace ends with | Library | Meaning |
|-----------------------|---------|---------|
| `requests/models.py` → `raise HTTPError` | Standard `requests` | Python native TLS was used |
| `curl_cffi/requests/models.py` → `raise HTTPError` | `curl_cffi` | Chrome TLS impersonation was used |

**If `curl_cffi` raises the 429**: Akamai is blocking chrome TLS on that endpoint.
Do NOT try to "fix" by routing more traffic through curl_cffi — that makes it worse.

**If `requests` raises the 429** on the exchange endpoint and `ChromeTLSSession` IS set:
This is a **rate-limit 429**, not a TLS fingerprint block. Auto-reconnect should handle this
automatically. If it's still failing, check the auto-reconnect failure diagnostics below.

**If `requests` raises the 429 and `ChromeTLSSession` is NOT set**: The ChromeTLSSession is not being used.
Check that `create_api_client()` sets `client.garth.sess = ChromeTLSSession(...)`.

### Auto-reconnect failure diagnostics

| Log message | Cause | Operator action |
|-------------|-------|----------------|
| `Auto-reconnect login failed for user X (clearing credentials)` | Bad password or Garmin account locked (`GarthHTTPError` or `cffi_requests.HTTPError`). Credentials cleared, 1-hour cooldown. | User must reconnect in Settings with correct password |
| `Auto-reconnect failed for user X: <ExcType>` | Transient network error. Credentials kept, 15-min cooldown, will retry. | Check network/Render status, wait for retry |
| `Garmin credentials expired (30-day policy) for user X` | Credentials older than 30 days, auto-cleared. | User reconnects in Settings (normal flow) |
| `Auto-reconnect on cooldown for user X` | A previous reconnect attempt failed recently. | Wait for cooldown to expire (15 min or 1 hour) |

---

## Step 1 — Identify the failure mode from logs

Check Render logs for the error. Three distinct 429 types:

### SSO Login 429 (during Garmin Connect)

| Log line | Meaning |
|----------|---------|
| `Garmin login attempt 1/5: chrome136 TLS, no proxy` | Fix is active (5-fingerprint rotation) |
| `Garmin login attempt N/5: <fingerprint> TLS, ...` | Rotation in progress |
| `Garmin SSO rate-limited (429) ... proxy=False` | Fingerprint blocked — Akamai updated detection |
| `Garmin SSO rate-limited (429) ... proxy=True` | All fingerprints AND Fixie blocked |
| `'Session' object has no attribute 'hooks'` | garth version mismatch — shim needs update |
| `Garmin login failed: Error in request: 429` (no attempt log) | Old code without the fix deployed |
| `Garmin proxy unreachable` | FIXIE_URL misconfigured |

### API Token Exchange 429 (during Sync/Fetch)

| Log line | Meaning |
|----------|---------|
| `curl_cffi...HTTPError: HTTP Error 429` on `.../exchange/user/2.0` | curl_cffi is being used for exchange — **this is the bug**. The exchange must use garth's native `sso.exchange()` (standard Python TLS). Do NOT override `refresh_oauth2`. |
| `requests...HTTPError: 429` on `.../exchange/user/2.0` | Standard Python TLS blocked — rare. Check if `client.garth.sess` is set to `ChromeTLSSession` (the parent session matters for `GarminOAuth1Session` adapter inheritance). |
| `Sync failed for workout X: 429` | Check the full traceback to determine which library (see Step 0) |

### Regular API 429 (not exchange)

| Log line | Meaning |
|----------|---------|
| `requests...HTTPError: 429` on non-exchange URL | `ChromeTLSSession` not set on `client.garth.sess` |
| `curl_cffi...HTTPError: 429` on non-exchange URL | Akamai updated — try bumping Chrome version |

**Key diagnostic: login exchange works → refresh exchange fails**

During login, `sso.exchange()` creates `GarminOAuth1Session(parent=client.sess)` which uses
standard Python TLS — and this works. If refresh exchange fails, check whether someone overrode
`refresh_oauth2` to route through curl_cffi. The override causes the 429.

---

## Step 2 — Run test_garmin_login.py locally

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
python test_garmin_login.py
# Optional: test with Fixie too
FIXIE_URL=http://fixie:password@... python test_garmin_login.py
```

The script tests multiple approaches side-by-side. Update it to test the current `FINGERPRINT_SEQUENCE` entries when Akamai updates detection.

### Interpreting results

| Result | Diagnosis | Fix |
|--------|-----------|-----|
| First fingerprint passes locally, fails on Render | Render IP blocked on SSO | Fixie proxy fallback on last attempt |
| First fingerprint fails locally too | Akamai updated detection for that fingerprint | Rotation will try next fingerprint automatically |
| All fingerprints fail locally | Account rate-limited — stop retrying, wait 30–60 min | Wait; then add new fingerprints to `FINGERPRINT_SEQUENCE` |
| Passes locally but Render still fails | Code not deployed / wrong branch | Check deploy |

---

## Step 3 — The architecture: `client_factory.py`

The facade lives in `backend/src/garmin/client_factory.py`:

```python
from src.garmin.client_factory import ChromeTLSSession, CHROME_VERSION, create_api_client, create_login_client
```

**`FINGERPRINT_SEQUENCE`** — ordered list of TLS fingerprints tried on each login attempt:
```python
FINGERPRINT_SEQUENCE = ["chrome136", "safari15_5", "edge101", "chrome120", "chrome99"]
# Add new fingerprints at the front — affects login retry only, not API
```

**`ChromeTLSSession`** — curl_cffi session with requests.Session compatibility:
```python
class ChromeTLSSession(cffi_requests.Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _rs = requests.Session()
        self.adapters = _rs.adapters
        self.hooks = _rs.hooks
```

**`create_login_client(fingerprint, proxy_url=None)`** — for SSO login in `garmin_connect.py`:
```python
# Called in a loop over FINGERPRINT_SEQUENCE with random 30-45s delay before attempt 2+
client = create_login_client(fingerprint, proxy_url=settings.fixie_url if last_attempt else None)
client.login(email, password)
```

**`create_api_client(token_json)`** — for all API calls in `sync.py`:
```python
adapter = create_api_client(token_json)  # Returns GarminAdapter with first fingerprint TLS
```

### How token exchange works (DO NOT OVERRIDE)

```
garth.Client.request(api=True)
  → oauth2_token expired?
  → self.refresh_oauth2()                    # native garth method — DO NOT monkey-patch
  → sso.exchange(self.oauth1_token, self)
  → GarminOAuth1Session(parent=self.sess)    # self.sess = ChromeTLSSession
     → copies parent.adapters["https://"]     # gets standard HTTPAdapter
     → sess.post(url, ...)                    # standard Python TLS (requests.Session)
     → Akamai ALLOWS this                     # ✅
```

**Why this works**: `GarminOAuth1Session` extends `requests_oauthlib.OAuth1Session` which extends
`requests.Session`. Even though `parent` is a `ChromeTLSSession`, the OAuth1Session only copies
`adapters`, `proxies`, and `verify` — it does NOT inherit curl_cffi's TLS engine. The actual HTTP
call uses standard Python TLS, which Akamai allows on `connectapi.garmin.com/oauth-service/`.

**Anti-pattern — DO NOT do this**:
```python
# ❌ WRONG — routing exchange through curl_cffi causes 429
def _patched_refresh_oauth2():
    garth_client.oauth2_token = _chrome_tls_exchange(...)  # curl_cffi → 429
garth_client.refresh_oauth2 = _patched_refresh_oauth2
```

Available fingerprints in curl_cffi 0.14+: `chrome99`, `chrome101`, `chrome104`, `chrome107`,
`chrome110`, `chrome116`, `chrome119`, `chrome120`, `chrome123`, `chrome124`, `chrome136`,
`safari15_5`, `edge101`. Add new ones to the front of `FINGERPRINT_SEQUENCE`.

**If garth adds a new internal attribute** (e.g., `'Session' object has no attribute 'X'`),
add it to `ChromeTLSSession.__init__`:
```python
self.X = requests.Session().X
```

---

## Step 4 — Retry flow

```
Login (5-fingerprint rotation):
  Attempt 1: chrome136 TLS, no proxy, no delay
      ↓ 429
  Attempt 2: safari15_5 TLS, no proxy, wait 30-45s
      ↓ 429
  Attempt 3: edge101 TLS, no proxy, wait 30-45s
      ↓ 429
  Attempt 4: chrome120 TLS, no proxy, wait 30-45s
      ↓ 429
  Attempt 5: chrome99 TLS + Fixie proxy (if FIXIE_URL set), wait 30-45s
      ↓ 429
  → HTTP 503 returned to user: "Garmin is temporarily rate-limiting this server"

API calls (sync/fetch):
  Regular API: chrome136 TLS via ChromeTLSSession (client.garth.sess)
  Token exchange: standard Python TLS via GarminOAuth1Session (garth native)
  Retry logic: GarminSyncService._call_with_retry() (exponential backoff)
```

If all 5 login attempts fail, Akamai has updated its detection. Fix: add new fingerprints to `FINGERPRINT_SEQUENCE` in `client_factory.py` (Step 3).

---

## Step 5 — Verify Fixie is routing (if proxy involved)

Check the [Fixie dashboard](https://usefixie.com) — look for `CONNECT` entries to `sso.garmin.com:443`.
If you see CONNECT logs, the proxy IS routing. If still getting 429, it's TLS fingerprint not IP.
If no CONNECT logs, `FIXIE_URL` env var is wrong or not set in Render.

---

## Quick checklist

- [ ] `curl-cffi>=0.6` in `backend/pyproject.toml`
- [ ] `FINGERPRINT_SEQUENCE` in `client_factory.py` — add new fingerprints at front if Akamai starts blocking all current ones
- [ ] `ChromeTLSSession` in `client_factory.py`, used by both login and sync
- [ ] `garmin_connect.py` uses `create_login_client()` (not inline session creation)
- [ ] `sync.py` uses `create_api_client()` (not bare `garminconnect.Garmin()`)
- [ ] `refresh_oauth2` is NOT overridden (garth native exchange uses standard Python TLS)
- [ ] Render logs show `Garmin login attempt 1/5: chrome136 TLS, no proxy`
- [ ] `FIXIE_URL` set in Render (optional fallback for last SSO login attempt only)
- [ ] Check stack trace library (Step 0) before assuming curl_cffi is the fix
- [ ] After updating `FINGERPRINT_SEQUENCE`, grep docs for stale fingerprint refs: `grep -r "chrome1[0-9][0-9]\|safari15\|edge101" features/ .claude/skills/ CLAUDE.md`
- [ ] `auto_reconnect.py` exists in `backend/src/garmin/`
- [ ] `GARMIN_CREDENTIAL_KEY` set to a **production-unique value** in Render (NOT the `.env.example` placeholder)
- [ ] Credentials stored after connect (`garmin_credential_encrypted` populated in DB)
- [ ] `client_cache.py` exists in `backend/src/garmin/` (in-process adapter cache)
