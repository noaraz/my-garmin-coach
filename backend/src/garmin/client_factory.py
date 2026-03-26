"""Centralized Garmin client creation with Chrome TLS impersonation.

All Garmin API calls (login, sync, activity fetch) go through clients created
here, ensuring Chrome 124 TLS fingerprint bypasses Akamai Bot Manager on
SSO login (sso.garmin.com) and regular API calls (connectapi.garmin.com).

garth's native sso.exchange() creates a GarminOAuth1Session that inherits
adapters from ChromeTLSSession via parent=client.sess. This uses standard
Python TLS for the OAuth2 token exchange — which Akamai allows (proven by
login flow working). We do NOT override refresh_oauth2.
"""
from __future__ import annotations

from typing import Any

import garminconnect
import garth
import requests
from curl_cffi import requests as cffi_requests

from src.garmin.adapter import GarminAdapter

CHROME_VERSION = "chrome124"


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


def create_api_client(token_json: str) -> GarminAdapter:
    """Create a GarminAdapter from stored OAuth tokens with Chrome TLS.

    Used by sync.py for all API calls (workout push, activity fetch, etc.).
    garth's native refresh_oauth2 handles token exchange via
    GarminOAuth1Session(parent=ChromeTLSSession) — same path as login.
    """
    client = garminconnect.Garmin()
    client.garth.loads(token_json)
    client.garth.sess = ChromeTLSSession(impersonate=CHROME_VERSION)
    return GarminAdapter(client)


def create_login_client(proxy_url: str | None = None) -> garth.Client:
    """Create a garth.Client with Chrome TLS for SSO login.

    Used by garmin_connect.py for the initial Garmin authentication.
    """
    client = garth.Client()
    client.sess = ChromeTLSSession(impersonate=CHROME_VERSION)
    if proxy_url:
        client.sess.proxies = {"https": proxy_url}
    return client
