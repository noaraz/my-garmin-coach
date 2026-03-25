"""Centralized Garmin client creation with Chrome TLS impersonation.

All Garmin API calls (login, sync, activity fetch) go through clients created
here, ensuring Chrome 120 TLS fingerprint bypasses Akamai Bot Manager on both
SSO login (sso.garmin.com) and OAuth token exchange (connectapi.garmin.com).

Key problem solved: garth's sso.exchange() creates a GarminOAuth1Session
(extends requests.Session) for the OAuth2 token exchange — bypassing our
ChromeTLSSession entirely. We override refresh_oauth2 to sign with OAuth1
headers manually and send through curl_cffi.
"""
from __future__ import annotations

import time
from typing import Any

import garminconnect
import garth
import requests
from curl_cffi import requests as cffi_requests
from garth.auth_tokens import OAuth1Token, OAuth2Token
from garth.sso import OAUTH_CONSUMER, OAUTH_CONSUMER_URL, USER_AGENT
from requests_oauthlib import OAuth1

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


def _chrome_tls_exchange(
    oauth1: OAuth1Token, client: garth.Client
) -> OAuth2Token:
    """Exchange OAuth1 token for OAuth2 using curl_cffi (chrome120 TLS).

    Replaces garth's sso.exchange() which creates a GarminOAuth1Session
    (requests.Session subclass) — that uses Python's TLS fingerprint,
    which Akamai blocks with 429.

    This function:
    1. Signs the request with OAuth1 credentials (via requests_oauthlib)
    2. Sends the signed request through curl_cffi with chrome120 TLS
    """
    global OAUTH_CONSUMER
    if not OAUTH_CONSUMER:
        OAUTH_CONSUMER.update(requests.get(OAUTH_CONSUMER_URL).json())

    # Build OAuth1 auth to generate the Authorization header
    auth = OAuth1(
        client_key=OAUTH_CONSUMER["consumer_key"],
        client_secret=OAUTH_CONSUMER["consumer_secret"],
        resource_owner_key=oauth1.oauth_token,
        resource_owner_secret=oauth1.oauth_token_secret,
    )

    url = (
        f"https://connectapi.{client.domain}"
        "/oauth-service/oauth/exchange/user/2.0"
    )
    headers = {
        **USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = dict(mfa_token=oauth1.mfa_token) if oauth1.mfa_token else {}

    # Use requests to prepare the signed request (adds Authorization header)
    req = requests.Request("POST", url, headers=headers, data=data, auth=auth)
    prepared = req.prepare()

    # Send through curl_cffi with chrome120 TLS fingerprint
    sess = ChromeTLSSession(impersonate="chrome120")
    resp = sess.post(
        url,
        headers=dict(prepared.headers),
        data=data or None,
        timeout=client.timeout,
    )
    resp.raise_for_status()

    token = resp.json()
    token["expires_at"] = int(time.time() + token["expires_in"])
    token["refresh_token_expires_at"] = int(
        time.time() + token["refresh_token_expires_in"]
    )
    return OAuth2Token(**token)


def create_api_client(token_json: str) -> GarminAdapter:
    """Create a GarminAdapter from stored OAuth tokens with Chrome TLS.

    Used by sync.py for all API calls (workout push, activity fetch, etc.).
    Overrides refresh_oauth2 so token exchange also uses chrome120 TLS.
    """
    client = garminconnect.Garmin()
    client.garth.loads(token_json)
    client.garth.sess = ChromeTLSSession(impersonate="chrome120")

    # Override refresh_oauth2 to route token exchange through curl_cffi
    # instead of garth's GarminOAuth1Session (which uses requests.Session)
    garth_client = client.garth

    def _patched_refresh_oauth2() -> None:
        assert garth_client.oauth1_token and isinstance(
            garth_client.oauth1_token, OAuth1Token
        ), "OAuth1 token is required for OAuth2 refresh"
        garth_client.oauth2_token = _chrome_tls_exchange(
            garth_client.oauth1_token, garth_client
        )

    garth_client.refresh_oauth2 = _patched_refresh_oauth2  # type: ignore[assignment]

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
