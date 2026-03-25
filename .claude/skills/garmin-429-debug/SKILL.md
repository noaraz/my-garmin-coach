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

Garmin uses **Akamai Bot Manager** which blocks two signals:
1. **Datacenter IPs** — Render's shared IPs get 429
2. **Python `requests` TLS fingerprint** — Akamai fingerprints the TLS handshake regardless of IP

Akamai blocks BOTH:
- **SSO login** (`sso.garmin.com`) — during initial Garmin connect
- **OAuth token exchange** (`connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0`) — on every API call (sync, activity fetch, workout push)

**Current fix in production**: `ChromeTLSSession(impersonate="chrome120")` in
`backend/src/garmin/client_factory.py` — single source of truth for all Garmin client creation.

---

## Step 1 — Identify the failure mode from logs

Check Render logs for the error. Two distinct 429 types:

### SSO Login 429 (during Garmin Connect)

| Log line | Meaning |
|----------|---------|
| `Garmin login attempt 1/2: chrome120 TLS, no proxy` | Fix is active |
| `Garmin SSO rate-limited (429) ... proxy=False` | chrome120 blocked — Akamai updated detection |
| `Garmin SSO rate-limited (429) ... proxy=True` | Both chrome120 AND Fixie blocked |
| `'Session' object has no attribute 'hooks'` | garth version mismatch — shim needs update |
| `Garmin login failed: Error in request: 429` (no attempt log) | Old code without the fix deployed |
| `Garmin proxy unreachable` | FIXIE_URL misconfigured |

### API Token Exchange 429 (during Sync/Fetch)

| Log line | Meaning |
|----------|---------|
| `429 Client Error: Too Many Requests for url: .../oauth-service/oauth/exchange/user/2.0` | Token exchange blocked by Akamai |
| `Activity fetch failed (continuing): Rate limit exceeded: 429` | Same issue, during activity fetch |
| `Sync failed for workout X: 429` | Same issue, during workout push |

**If API 429s but login works**: `sync.py` is NOT using `create_api_client()` from `client_factory.py`. Check that `_get_garmin_adapter()` calls `create_api_client(token_json)` instead of bare `garminconnect.Garmin()`.

If you see **no** `Garmin login attempt` log lines, the current fix isn't deployed — check the branch.

---

## Step 2 — Run test_garmin_login.py locally

```bash
cd /Users/noa.raz/workspace/my-garmin-coach
python test_garmin_login.py
# Optional: test with Fixie too
FIXIE_URL=http://fixie:password@... python test_garmin_login.py
```

The script tests 4 approaches side-by-side:
1. Default `requests` — baseline (expect fail from Render IP, may pass locally)
2. `curl_cffi chrome110` no proxy
3. `curl_cffi chrome110` + Fixie proxy
4. `curl_cffi chrome120` no proxy — **this is what production uses**

### Interpreting results

| Result | Diagnosis | Fix |
|--------|-----------|-----|
| Test 4 passes locally, fails on Render | Render IP blocked, chrome120 not enough | Try chrome124/126 or add Fixie |
| Test 4 fails locally too | Akamai updated chrome120 detection | Bump to newer Chrome version |
| Test 4 passes but Render still fails | Code not deployed / wrong branch | Check deploy |
| All fail locally | Account rate-limited — stop retrying, wait 30–60 min | Wait |

---

## Step 3 — The fix: `client_factory.py`

The facade lives in `backend/src/garmin/client_factory.py`:

```python
from src.garmin.client_factory import ChromeTLSSession, create_api_client, create_login_client
```

**`ChromeTLSSession`** — curl_cffi session impersonating Chrome 120:
```python
class ChromeTLSSession(cffi_requests.Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _rs = requests.Session()
        self.adapters = _rs.adapters
        self.hooks = _rs.hooks
```

**`create_login_client(proxy_url=None)`** — for SSO login in `garmin_connect.py`:
```python
client = create_login_client(proxy_url=settings.fixie_url if retry else None)
client.login(email, password)
```

**`create_api_client(token_json)`** — for all API calls in `sync.py`:
```python
adapter = create_api_client(token_json)  # Returns GarminAdapter with chrome120 TLS
```

**If changing the Chrome version**, update `client_factory.py`:
```python
ChromeTLSSession(impersonate="chrome124")  # bump here — affects both login AND API
```

Available versions in curl_cffi: `chrome99`, `chrome101`, `chrome104`, `chrome107`, `chrome110`,
`chrome116`, `chrome119`, `chrome120`, `chrome123`, `chrome124`. Try the newest available.

**If garth adds a new internal attribute** (e.g., `'Session' object has no attribute 'X'`),
add it to `ChromeTLSSession.__init__`:
```python
self.X = requests.Session().X
```

---

## Step 3b — Token exchange 429 (not SSO)

If API calls fail with 429 on `connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0` but login works fine, the issue is that garth's token exchange uses a default `requests.Session` instead of `ChromeTLSSession`.

**Check**: `backend/src/api/routers/sync.py` → `_get_garmin_adapter()` must call:
```python
from src.garmin.client_factory import create_api_client
return create_api_client(token_json)
```

NOT the old pattern:
```python
# WRONG — uses default requests.Session, no chrome120 TLS
garmin_client = garminconnect.Garmin()
garmin_client.garth.loads(token_json)
return GarminAdapter(garmin_client)
```

---

## Step 4 — Retry flow

```
Login:
  Attempt 1: chrome120 TLS, no proxy
      ↓ 429
  Attempt 2: chrome120 TLS + Fixie proxy (if FIXIE_URL set)
      ↓ 429
  → HTTP 503 returned to user: "Garmin is temporarily rate-limiting this server"

API calls (sync/fetch):
  Single attempt with chrome120 TLS via create_api_client()
  No retry at this level — retry logic is in GarminSyncService._call_with_retry()
```

If both login attempts fail, Akamai has updated its detection. Fix: bump Chrome version (Step 3).

---

## Step 5 — Verify Fixie is routing (if proxy involved)

Check the [Fixie dashboard](https://usefixie.com) — look for `CONNECT` entries to `sso.garmin.com:443`.
If you see CONNECT logs, the proxy IS routing. If still getting 429, it's TLS fingerprint not IP.
If no CONNECT logs, `FIXIE_URL` env var is wrong or not set in Render.

---

## Quick checklist

- [ ] `curl-cffi>=0.6` in `backend/pyproject.toml`
- [ ] `ChromeTLSSession` in `backend/src/garmin/client_factory.py`, used by both login and sync
- [ ] `garmin_connect.py` uses `create_login_client()` (not inline `_ChromeTLSSession`)
- [ ] `sync.py` uses `create_api_client()` (not bare `garminconnect.Garmin()`)
- [ ] Render logs show `Garmin login attempt 1/2: chrome120 TLS, no proxy`
- [ ] `FIXIE_URL` set in Render (optional but good fallback)
