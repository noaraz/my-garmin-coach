"""Centralized Garmin client creation with Chrome TLS impersonation.

All Garmin API calls (login, sync, activity fetch) go through clients created
here, ensuring Chrome 120 TLS fingerprint bypasses Akamai Bot Manager on both
SSO login (sso.garmin.com) and OAuth token exchange (connectapi.garmin.com).
"""
from __future__ import annotations

from typing import Any

import garminconnect
import garth
import requests
from curl_cffi import requests as cffi_requests

from src.garmin.adapter import GarminAdapter


class ChromeTLSSession(cffi_requests.Session):
    """curl_cffi session impersonating Chrome 120 to bypass Akamai Bot Manager.

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
    """
    client = garminconnect.Garmin()
    client.garth.loads(token_json)
    client.garth.sess = ChromeTLSSession(impersonate="chrome120")
    return GarminAdapter(client)


def create_login_client(proxy_url: str | None = None) -> garth.Client:
    """Create a garth.Client with Chrome TLS for SSO login.

    Used by garmin_connect.py for the initial Garmin authentication.
    """
    client = garth.Client()
    client.sess = ChromeTLSSession(impersonate="chrome120")
    if proxy_url:
        client.sess.proxies = {"https": proxy_url}
    return client
