"""Centralized Garmin client creation with feature-flag branching.

V1 (garth): Chrome TLS impersonation, manual fingerprint rotation.
V2 (garminconnect 0.3.x): Library handles TLS + cascading login internally.

The factory reads the auth version from Settings (env var seed).
Runtime switching is handled by the admin endpoint writing to SystemConfig;
callers that need the DB-backed value should query it via dependency injection.
"""
from __future__ import annotations

import json
from typing import Any

import garminconnect
import garth
import requests
from curl_cffi import requests as cffi_requests

from src.garmin.adapter_protocol import (
    GarminAdapterProtocol,
    GarminAuthError,
    GarminConnectionError,
    GarminRateLimitError,
)
from src.garmin.adapter_v1 import GarminAdapter
from src.garmin.adapter_v2 import GarminAdapterV2

CHROME_VERSION = "chrome136"

FINGERPRINT_SEQUENCE: list[str] = [
    "chrome136",
    "safari15_5",
    "edge101",
    "chrome120",
    "chrome99",
]


class ChromeTLSSession(cffi_requests.Session):
    """curl_cffi session impersonating Chrome to bypass Akamai Bot Manager.

    garth accesses requests.Session internals (adapters, hooks) so we
    pre-populate them from a real requests.Session.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _rs = requests.Session()
        self.adapters = _rs.adapters
        self.hooks = _rs.hooks


def _get_auth_version() -> str:
    """Read auth version from Settings (env var seed). For DB-backed runtime
    value, callers should use the FastAPI dependency instead."""
    from src.core.config import get_settings
    return get_settings().garmin_auth_version


# ---------------------------------------------------------------------------
# Adapter creation (token → adapter)
# ---------------------------------------------------------------------------

def create_adapter(token_json: str, auth_version: str | None = None) -> GarminAdapterProtocol:
    """Create the appropriate adapter based on auth version.

    Args:
        token_json: Serialized token (garth format for V1, JSON dict for V2).
        auth_version: Override auth version. If None, reads from Settings.
    """
    version = auth_version or _get_auth_version()
    if version == "v2":
        return _create_adapter_v2(token_json)
    return _create_adapter_v1(token_json)


def _create_adapter_v1(token_json: str) -> GarminAdapter:
    """Create a V1 GarminAdapter from garth tokens with Chrome TLS."""
    client = garminconnect.Garmin()
    client.garth.loads(token_json)
    client.garth.sess = ChromeTLSSession(impersonate=CHROME_VERSION)
    return GarminAdapter(client)


def _create_adapter_v2(token_json: str) -> GarminAdapterV2:
    """Create a V2 GarminAdapterV2 from 0.3.x token dict."""
    tokens = json.loads(token_json)
    client = garminconnect.Garmin()
    client.garmin_tokens = tokens
    return GarminAdapterV2(client)


# ---------------------------------------------------------------------------
# Login (email+password → token JSON)
# ---------------------------------------------------------------------------

def login_and_get_token(
    email: str,
    password: str,
    fingerprint: str = CHROME_VERSION,
    proxy_url: str | None = None,
    auth_version: str | None = None,
) -> str:
    """Login and return serialized token JSON.

    V1: Creates garth.Client with ChromeTLSSession. Caller handles retry loop.
    V2: Creates Garmin(email, password), calls login(). Library handles retries.
    """
    version = auth_version or _get_auth_version()
    if version == "v2":
        return _login_v2(email, password)
    return _login_v1(email, password, fingerprint, proxy_url)


def _login_v1(
    email: str,
    password: str,
    fingerprint: str = CHROME_VERSION,
    proxy_url: str | None = None,
) -> str:
    """V1 login via garth.Client + Chrome TLS."""
    client = garth.Client()
    client.sess = ChromeTLSSession(impersonate=fingerprint)
    if proxy_url:
        client.sess.proxies = {"https": proxy_url}
    client.login(email, password)
    return client.dumps()


def _login_v2(email: str, password: str) -> str:
    """V2 login via garminconnect 0.3.x native auth.

    garminconnect 0.3.2+ has its own 5-strategy cascading login with automatic
    retry and MFA dual-endpoint fallback. Do NOT inject ChromeTLSSession or
    fingerprint rotation — it interferes with the library's built-in cascade.
    """
    try:
        client = garminconnect.Garmin(email=email, password=password)
        client.login()
        return json.dumps(client.garmin_tokens)
    except garminconnect.GarminConnectAuthenticationError as exc:
        raise GarminAuthError(str(exc)) from exc
    except garminconnect.GarminConnectTooManyRequestsError as exc:
        raise GarminRateLimitError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise GarminConnectionError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Backward compat (used by existing code during migration)
# ---------------------------------------------------------------------------

def create_api_client(token_json: str) -> GarminAdapterProtocol:
    """Backward-compat alias for create_adapter(). Reads version from Settings."""
    return create_adapter(token_json)


def create_login_client(
    fingerprint: str = CHROME_VERSION,
    proxy_url: str | None = None,
) -> garth.Client:
    """V1-only: Create a garth.Client for SSO login. Used by garmin_connect.py retry loop."""
    client = garth.Client()
    client.sess = ChromeTLSSession(impersonate=fingerprint)
    if proxy_url:
        client.sess.proxies = {"https": proxy_url}
    return client
