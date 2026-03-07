from __future__ import annotations

from typing import Any

from src.garmin.exceptions import GarminAuthError


class GarminSession:
    """Manage authentication state for a Garmin Connect session.

    Tokens are cached in memory only — never written to disk.
    The underlying garminconnect client is injected so it can be replaced
    with a mock in tests.

    Usage::

        import garminconnect
        client = garminconnect.Garmin(email, password)
        session = GarminSession(client)
        session.login(email, password)
    """

    def __init__(self, client: Any) -> None:
        self._client = client
        self._is_authenticated: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_authenticated(self) -> bool:
        """True if the session has been successfully established."""
        return self._is_authenticated

    def login(self, email: str, password: str) -> None:
        """Authenticate and cache the session tokens in memory.

        The password is NOT stored — it is passed directly to the client
        and discarded immediately after the call.

        Raises:
            GarminAuthError: if the login fails for any reason.
        """
        try:
            self._client.login(email, password)
            self._is_authenticated = True
        except Exception as exc:
            self._is_authenticated = False
            raise GarminAuthError(f"Garmin login failed: {exc}") from exc
        finally:
            # Discard the password reference — do not store it.
            del password

    def logout(self) -> None:
        """Invalidate the current session."""
        self._is_authenticated = False

    def get_client(self) -> Any:
        """Return the authenticated client for use by sync services.

        Raises:
            GarminAuthError: if the session has not been established.
        """
        if not self._is_authenticated:
            raise GarminAuthError(
                "Garmin session is not authenticated. Call login() first."
            )
        return self._client
