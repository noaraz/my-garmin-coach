---
name: garmin-429-debug
description: >
  Debug Garmin SSO 429 / bot-detection errors in GarminCoach. Use this skill
  whenever Garmin Connect fails in production or locally with a 429, "Too Many
  Requests", "GarthHTTPError", or "Akamai" in the error. Also trigger for any
  error from sso.garmin.com during login, or when POST /api/v1/garmin/connect
  returns 400/503 unexpectedly. Don't wait for the user to ask — if Garmin
  connect is failing, invoke this skill immediately.
---

# Garmin 429 / Bot-Detection Debug

Garmin's `sso.garmin.com` uses **Akamai Bot Manager** which blocks two signals:
1. **Datacenter IPs** — Render's shared IPs get 429
2. **Python `requests` TLS fingerprint** — Akamai fingerprints the TLS handshake regardless of IP

**Current fix in production**: `_ChromeTLSSession(impersonate="chrome120")` in
`backend/src/api/routers/garmin_connect.py` — chrome120 TLS alone bypasses Akamai (no proxy needed).

---

## Step 1 — Identify the failure mode from logs

Check Render logs for the connect attempt. Look for:

| Log line | Meaning |
|----------|---------|
| `Garmin login attempt 1/2: chrome120 TLS, no proxy` | Fix is active |
| `Garmin SSO rate-limited (429) ... proxy=False` | chrome120 blocked — Akamai updated detection |
| `Garmin SSO rate-limited (429) ... proxy=True` | Both chrome120 AND Fixie blocked |
| `'Session' object has no attribute 'hooks'` | garth version mismatch — shim needs update |
| `Garmin login failed: Error in request: 429` (no attempt log) | Old code without the fix deployed |
| `Garmin proxy unreachable` | FIXIE_URL misconfigured |

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
1. Default `requests` — baseline (expect ❌ from Render IP, may ✅ locally)
2. `curl_cffi chrome110` no proxy
3. `curl_cffi chrome110` + Fixie proxy
4. `curl_cffi chrome120` no proxy ← **this is what production uses**

### Interpreting results

| Result | Diagnosis | Fix |
|--------|-----------|-----|
| Test 4 ✅ locally, fails on Render | Render IP blocked, chrome120 not enough | Try chrome124/126 or add Fixie |
| Test 4 ❌ locally too | Akamai updated chrome120 detection | Bump to newer Chrome version |
| Test 4 ✅ but Render still fails | Code not deployed / wrong branch | Check deploy |
| All ❌ locally | Account rate-limited — stop retrying, wait 30–60 min | Wait |

---

## Step 3 — The fix: `_ChromeTLSSession`

The shim lives in `backend/src/api/routers/garmin_connect.py`:

```python
class _ChromeTLSSession(cffi_requests.Session):
    """curl_cffi session with requests.Session compatibility shims for garth.

    Garmin SSO uses Akamai Bot Manager which blocks Python requests' TLS fingerprint.
    Chrome 120 impersonation bypasses it — no proxy needed (confirmed via test_garmin_login.py).
    garth accesses requests.Session internals (adapters, hooks) so we pre-populate them.
    """
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        _rs = requests.Session()
        self.adapters = _rs.adapters
        self.hooks = _rs.hooks
```

**If changing the Chrome version**, update the `impersonate=` in the login loop:
```python
client.sess = _ChromeTLSSession(impersonate="chrome124")  # bump here
```

Available versions in curl_cffi: `chrome99`, `chrome101`, `chrome104`, `chrome107`, `chrome110`,
`chrome116`, `chrome119`, `chrome120`, `chrome123`, `chrome124`. Try the newest available.

**If garth adds a new internal attribute** (e.g., `'Session' object has no attribute 'X'`),
add it to `_ChromeTLSSession.__init__`:
```python
self.X = requests.Session().X
```

---

## Step 4 — Retry flow

```
Attempt 1: chrome120 TLS, no proxy
    ↓ 429
Attempt 2: chrome120 TLS + Fixie proxy (if FIXIE_URL set)
    ↓ 429
→ HTTP 503 returned to user: "Garmin is temporarily rate-limiting this server"
```

If both attempts fail, Akamai has updated its detection. Fix: bump Chrome version (Step 3).

---

## Step 5 — Verify Fixie is routing (if proxy involved)

Check the [Fixie dashboard](https://usefixie.com) — look for `CONNECT` entries to `sso.garmin.com:443`.
If you see CONNECT logs, the proxy IS routing. If still getting 429, it's TLS fingerprint not IP.
If no CONNECT logs, `FIXIE_URL` env var is wrong or not set in Render.

---

## Quick checklist

- [ ] `curl-cffi>=0.6` in `backend/pyproject.toml`
- [ ] `_ChromeTLSSession` class present in `garmin_connect.py`
- [ ] Login loop uses `_ChromeTLSSession(impersonate="chrome120")`
- [ ] Render logs show `Garmin login attempt 1/2: chrome120 TLS, no proxy`
- [ ] `FIXIE_URL` set in Render (optional but good fallback)
