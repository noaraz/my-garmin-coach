# Garmin Auto-Reconnect: Encrypted Credential Storage + Exchange 429 Recovery

**Date:** 2026-03-28
**Status:** Design
**Problem:** Garmin OAuth2 token exchange endpoint returns 429 after token expiry (~1 hour). Once blocked, all syncs fail indefinitely. Users must manually disconnect/reconnect Garmin in Settings to recover.

## Overview

Store Garmin credentials (email + password) encrypted in the DB with a **separate encryption key** from the OAuth token key. When the OAuth2 exchange fails with 429, automatically re-login using stored credentials to obtain fresh tokens. Credentials auto-expire after 30 days for security.

## Architecture

### Encryption

| | OAuth Tokens (existing) | Garmin Credentials (new) |
|---|---|---|
| **Env var** | `GARMINCOACH_SECRET_KEY` | `GARMIN_CREDENTIAL_KEY` |
| **Algorithm** | Fernet (AES-128-CBC + HMAC-SHA256) | Fernet (same) |
| **KDF** | HKDF-SHA256, salt=user_id | HKDF-SHA256, salt=user_id |
| **Domain** | `b"garmincoach-token-v1"` | `b"garmincoach-credential-v1"` |
| **Storage** | `AthleteProfile.garmin_oauth_token_encrypted` | `AthleteProfile.garmin_credential_encrypted` |
| **Lifetime** | Until next refresh | 30 days from storage |

Two independent keys protect against a **stolen DB backup** (attacker has ciphertext but not env vars). They do NOT protect against a compromised application environment (both keys live in the same Render process). This is the correct boundary for a 4-5 user self-hosted app.

### Data model changes

```python
# AthleteProfile — new fields
garmin_credential_encrypted: Optional[str] = Field(default=None)
garmin_credential_stored_at: Optional[datetime] = Field(default=None)  # UTC, naive
```

### Credential lifecycle

```
User connects Garmin in Settings
  → POST /api/v1/garmin/connect { email, password }
  → garth.login(email, password) → success
  → encrypt OAuth tokens with GARMINCOACH_SECRET_KEY → save to DB
  → encrypt credentials with GARMIN_CREDENTIAL_KEY → save to DB with timestamp
  → del email, password (discard from memory)
  → return 200

Sync with valid token
  → load token from DB → garth.loads() → oauth2_token.expired = False
  → API calls succeed → done

Sync with expired token (exchange succeeds)
  → garth.refresh_oauth2() → sso.exchange() → success
  → persist refreshed token to DB → done

Sync with expired token (exchange 429) — THE FIX
  → garth.refresh_oauth2() → sso.exchange() → 429
  → check garmin_credential_encrypted exists
  → check garmin_credential_stored_at < 30 days ago
  → decrypt credentials
  → create_login_client().login(email, password) → fresh tokens
  → encrypt & save new tokens to DB
  → invalidate client cache
  → retry sync with fresh adapter
  → del email, password

Sync with expired token + expired credentials (>30 days)
  → exchange 429 → credentials expired → clear from DB
  → return error: "Garmin credentials expired (30-day security policy).
     Please reconnect in Settings."
```

### Auto-reconnect implementation

**Location:** `backend/src/garmin/auto_reconnect.py` (new module)

```python
async def attempt_auto_reconnect(
    user_id: int,
    session: AsyncSession,
) -> GarminAdapter | None:
    """Try to re-login using stored credentials when exchange fails.

    Returns a fresh GarminAdapter on success, None if credentials are
    missing, expired, or login fails.
    """
    profile = await _get_profile(session, user_id)
    if not profile or not profile.garmin_credential_encrypted:
        return None

    # Check 30-day expiry
    if _credentials_expired(profile.garmin_credential_stored_at):
        # Clear expired credentials
        profile.garmin_credential_encrypted = None
        profile.garmin_credential_stored_at = None
        session.add(profile)
        await session.commit()
        return None

    # Per-user reconnect cooldown (prevent repeated login attempts → account lockout)
    if _reconnect_on_cooldown(user_id):
        return None

    # Decrypt and re-login
    creds = decrypt_credential(user_id, settings.garmin_credential_key, ...)
    email, password = creds["email"], creds["password"]
    try:
        client = create_login_client()
        client.login(email, password)
        token_json = client.dumps()

        # Persist fresh tokens
        profile.garmin_oauth_token_encrypted = encrypt_token(...)
        session.add(profile)
        await session.commit()
        cache.invalidate(f"profile:{user_id}")
        client_cache.invalidate(user_id)

        return create_api_client(token_json)
    except GarthHTTPError:
        # Bad credentials or Garmin blocked → clear stored credentials immediately
        # (a bad password will never succeed; repeated attempts risk account lockout)
        logger.warning("Auto-reconnect login failed for user %s (clearing credentials)", user_id)
        profile.garmin_credential_encrypted = None
        profile.garmin_credential_stored_at = None
        session.add(profile)
        await session.commit()
        _set_reconnect_cooldown(user_id, seconds=3600)  # 1 hour for auth failures
        return None
    except Exception as exc:
        logger.warning("Auto-reconnect failed for user %s: %s", user_id, type(exc).__name__)
        _set_reconnect_cooldown(user_id, seconds=900)  # 15 min for network errors
        return None
```

**Integration in sync.py:**

```python
# In sync_all, after first exchange 429:
try:
    garmin_workouts = sync_service.get_workouts()
except Exception as exc:
    if _is_exchange_429(exc):
        adapter = await attempt_auto_reconnect(current_user.id, session)
        if adapter is None:
            return SyncAllResponse(
                ..., fetch_error="Garmin credentials expired. Reconnect in Settings."
            )
        # Rebuild orchestrator with fresh adapter and retry
        sync_service = SyncOrchestrator(...)
        garmin_workouts = sync_service.get_workouts()  # retry once
```

### Exchange storm prevention (complementary)

Even with auto-reconnect, prevent the 429 storm:

1. **Early-exit:** If first API call gets exchange 429, don't continue to other stages
2. **Module-level cooldown:** After a 429, skip exchange for 30 minutes (resets on process restart)
3. **Client cache:** Cache GarminAdapter per user_id in process memory

### 30-day expiry UX

**Frontend changes:**

When `sync_all` returns `fetch_error` containing "credentials expired":
- `CalendarPage` shows a **toast notification**: "Your Garmin credentials expired for security. Please reconnect in Settings to resume syncing." with a "Go to Settings" link
- `SettingsPage` Garmin section shows info text: "For your security, Garmin credentials are re-verified every 30 days."

**Connect flow update:**
- Settings → Garmin Connect form unchanged (email + password)
- After successful connect, a brief success toast: "Connected. Credentials stored securely for 30 days."

### Security measures

1. **Separate encryption key** — `GARMIN_CREDENTIAL_KEY` env var, independent from `GARMINCOACH_SECRET_KEY`. Protects against stolen DB backup without env vars.
2. **30-day auto-expiry** — credentials cleared on read if expired. Uses `datetime.now(timezone.utc).replace(tzinfo=None)` for both write and comparison (project convention for naive UTC datetimes in PostgreSQL).
3. **Minimal decryption** — only decrypted when exchange actually fails (not on every sync)
4. **Memory cleanup caveat** — `del` removes Python name bindings but CPython strings are immutable and cannot be zeroed. Decrypted credentials may survive in memory until GC. This is a known CPython limitation accepted for this deployment (Render ephemeral containers, short process lifetime).
5. **No logging of credentials** — same pattern as existing connect flow: log `type(exc).__name__` only, never `exc` objects (garth embeds PreparedRequest with form body containing plaintext credentials)
6. **Config validation** — enforce non-dev key in production. Reuse same `@field_validator` pattern as `garmincoach_secret_key`. Fail startup if default value in non-debug mode.
7. **Suppress library debug logs** — `garth` and `curl_cffi` loggers set to WARNING
8. **Reconnect cooldown** — per-user cooldown prevents repeated login attempts that could trigger Garmin account lockout. 15 min for network errors, 1 hour for auth failures (with immediate credential clearing).
9. **Disconnect clears credentials** — `disconnect_garmin` must clear `garmin_credential_encrypted` and `garmin_credential_stored_at` alongside existing token cleanup.

### Threat model acceptance

We accept storing a reversible password (encrypted with Fernet) for up to 30 days because:
- The alternative (manual reconnect on every exchange 429) is operationally unacceptable for 4-5 users
- OAuth tokens we already store grant immediate API access — similar risk profile
- Encryption uses a separate key from tokens (defense-in-depth for cold storage)
- 30-day auto-expiry limits exposure window
- Garmin passwords are typically unique (not reused) for users of a training app

### Alembic migration

```python
# New migration
op.add_column('athleteprofile', sa.Column('garmin_credential_encrypted', sa.String(), nullable=True))
op.add_column('athleteprofile', sa.Column('garmin_credential_stored_at', sa.DateTime(), nullable=True))
```

### Environment changes

```bash
# .env.example
GARMIN_CREDENTIAL_KEY=change-me-to-different-random-32-chars

# Render dashboard: add GARMIN_CREDENTIAL_KEY env var
```

### Files to create/modify

| File | Change |
|------|--------|
| `backend/src/garmin/auto_reconnect.py` | **New** — auto-reconnect logic |
| `backend/src/garmin/encryption.py` | Add `encrypt_credential()` / `decrypt_credential()` |
| `backend/src/garmin/client_cache.py` | **New** — in-process adapter cache |
| `backend/src/garmin/token_persistence.py` | **New** — extracted shared helper |
| `backend/src/db/models.py` | Add credential fields to AthleteProfile |
| `backend/src/core/config.py` | Add `garmin_credential_key` setting |
| `backend/src/api/routers/sync.py` | Wire auto-reconnect, early-exit, cooldown, client cache |
| `backend/src/api/routers/garmin_connect.py` | Store credentials on connect, clear on disconnect |
| `backend/src/api/routers/calendar.py` | Add token persistence after Garmin calls |
| `backend/src/api/routers/plans.py` | Add token persistence after Garmin calls |
| `backend/alembic/versions/` | New migration for credential columns |
| `frontend/src/pages/CalendarPage.tsx` | Show credential expiry toast |
| `frontend/src/pages/SettingsPage.tsx` | Add info text about 30-day policy |
| `.env.example` | Add `GARMIN_CREDENTIAL_KEY` |

### Testing

- Unit: `encrypt_credential` / `decrypt_credential` round-trip, per-user isolation, wrong key rejection
- Unit: `attempt_auto_reconnect` — success, expired credentials, missing credentials, login failure
- Unit: `_is_exchange_429` helper
- Unit: Exchange cooldown behavior
- Integration: sync_all with exchange 429 → auto-reconnect → retry succeeds
- Integration: sync_all with expired credentials → clean error returned
- Security: verify no credential leakage in logs (`caplog` assertions)
