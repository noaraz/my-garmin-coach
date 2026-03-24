#!/usr/bin/env python3
"""
Compare garth login approaches — TLS fingerprint vs proxy vs both.

Key question: is curl_cffi alone enough, or do we also need Fixie?

Usage:
    pip install garth curl-cffi
    python test_garmin_login.py
"""
from __future__ import annotations

import getpass
import os
import time

import garth
import requests


class _ChromeTLSSession(requests.Session if True else object):
    """Placeholder — overridden below once curl_cffi is imported."""


def _make_chrome_session(impersonate: str = "chrome110") -> object:
    from curl_cffi import requests as cffi_requests  # noqa: PLC0415

    class ChromeSession(cffi_requests.Session):
        def __init__(self) -> None:
            super().__init__(impersonate=impersonate)
            _rs = requests.Session()
            self.adapters = _rs.adapters
            self.hooks = _rs.hooks

    return ChromeSession()


def _try_login(label: str, client: garth.Client, email: str, password: str) -> bool:
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")
    start = time.monotonic()
    try:
        client.login(email, password)
        elapsed = time.monotonic() - start
        print(f"  ✅  SUCCESS  ({elapsed:.1f}s)")
        print(f"  token preview: {client.dumps()[:80]}…")
        return True
    except Exception as exc:
        elapsed = time.monotonic() - start
        print(f"  ❌  FAILED   ({elapsed:.1f}s)")
        print(f"  {type(exc).__name__}: {str(exc)[:120]}")
        return False


def main() -> None:
    print("Garmin login — TLS fingerprint + proxy comparison")
    print("Question: do we need Fixie, or is curl_cffi alone enough?\n")
    email    = input("  Email   : ").strip()
    password = getpass.getpass("  Password: ")

    fixie_url = os.environ.get("FIXIE_URL", "").strip()
    if fixie_url:
        print(f"\n  Fixie URL found in env: {fixie_url[:30]}…")
    else:
        print("\n  No FIXIE_URL in env — proxy tests will be skipped.")
        print("  To test proxy: FIXIE_URL=http://... python test_garmin_login.py")

    results: dict[str, bool] = {}

    # ── Test 1: default requests (baseline — expect ❌ from Render IP) ────────
    results["1. default requests (no proxy, no TLS fix)"] = _try_login(
        "Test 1 — default garth requests session (baseline)",
        garth.Client(), email, password,
    )
    time.sleep(2)

    try:
        # ── Test 2: curl_cffi only — NO proxy ────────────────────────────────
        client2 = garth.Client()
        client2.sess = _make_chrome_session("chrome110")
        results["2. curl_cffi chrome110 (no proxy)"] = _try_login(
            "Test 2 — curl_cffi Chrome 110, NO proxy  ← key test",
            client2, email, password,
        )
        time.sleep(2)

        # ── Test 3: curl_cffi + Fixie proxy ──────────────────────────────────
        if fixie_url:
            client3 = garth.Client()
            client3.sess = _make_chrome_session("chrome110")
            client3.sess.proxies = {"https": fixie_url}
            results["3. curl_cffi chrome110 + Fixie proxy"] = _try_login(
                "Test 3 — curl_cffi Chrome 110 + Fixie proxy",
                client3, email, password,
            )
            time.sleep(2)
        else:
            results["3. curl_cffi chrome110 + Fixie proxy"] = False
            print("\n  ⏭️  Skipping Test 3 (no FIXIE_URL)")

        # ── Test 4: curl_cffi chrome120 (no proxy) ────────────────────────────
        client4 = garth.Client()
        client4.sess = _make_chrome_session("chrome120")
        results["4. curl_cffi chrome120 (no proxy)"] = _try_login(
            "Test 4 — curl_cffi Chrome 120, NO proxy",
            client4, email, password,
        )

    except ImportError:
        print("\n  ⚠️  curl-cffi not installed — pip install curl-cffi")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print("  SUMMARY")
    print(f"{'═'*60}")
    for label, ok in results.items():
        print(f"  {'✅' if ok else '❌'}  {label}")

    if results.get("2. curl_cffi chrome110 (no proxy)"):
        print("\n  🎉 curl_cffi alone is enough — Fixie is not needed!")
    elif results.get("3. curl_cffi chrome110 + Fixie proxy"):
        print("\n  ℹ️  Need both curl_cffi AND Fixie proxy.")
    print()


if __name__ == "__main__":
    main()
