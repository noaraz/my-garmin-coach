from __future__ import annotations

import asyncio
from typing import Any

from src.garmin.exceptions import GarminAuthError

# Maximum number of retry attempts on rate-limit or transient errors.
_MAX_RETRIES = 3
# Initial backoff in seconds (doubles on each retry).
_INITIAL_BACKOFF = 1.0

_RATE_LIMIT_INDICATORS = ("429", "too many requests", "rate limit")


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True if the exception looks like a 429 / rate-limit response."""
    msg = str(exc).lower()
    return any(indicator in msg for indicator in _RATE_LIMIT_INDICATORS)


class GarminSyncService:
    """Push, update, schedule and delete workouts on Garmin Connect.

    All Garmin API calls are delegated to *client* so this class is fully
    testable with a mock.  Rate-limiting is handled transparently with
    exponential backoff (up to _MAX_RETRIES attempts).

    Attributes:
        last_sync_status: "synced" | "failed" — updated after every push.
    """

    def __init__(self, client: Any) -> None:
        self._client = client
        self.last_sync_status: str = ""

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> None:
        """Authenticate with Garmin Connect.

        Raises:
            GarminAuthError: if the login attempt fails for any reason.
        """
        try:
            self._client.login(email, password)
        except Exception as exc:
            raise GarminAuthError(f"Garmin login failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Core CRUD operations
    # ------------------------------------------------------------------

    async def push_workout(self, formatted_workout: dict[str, Any]) -> str:
        """Upload a new workout to Garmin Connect.

        Returns:
            The Garmin-assigned workout ID string.

        Raises:
            Exception: after _MAX_RETRIES failed attempts.
        """
        result = await self._call_with_retry(
            self._client.add_workout, formatted_workout
        )
        return str(result["workoutId"])

    def schedule_workout(self, garmin_workout_id: str, date: str) -> str | None:
        """Place a workout on the Garmin calendar for *date* (YYYY-MM-DD).

        Returns:
            The Garmin schedule entry ID (str) if the response includes one,
            otherwise None.  Storing this allows reconciliation to verify the
            calendar entry still exists independently of the workout template.
        """
        result = self._client.schedule_workout(garmin_workout_id, date)
        if isinstance(result, dict):
            sid = result.get("workoutScheduleId") or result.get("scheduledWorkoutId")
            return str(sid) if sid is not None else None
        return None

    def update_workout(
        self, garmin_workout_id: str, formatted_workout: dict[str, Any]
    ) -> None:
        """Replace an existing Garmin workout with new content."""
        self._client.update_workout(garmin_workout_id, formatted_workout)

    def delete_workout(self, garmin_workout_id: str) -> None:
        """Permanently remove a workout from Garmin Connect."""
        self._client.delete_workout(garmin_workout_id)

    def get_workouts(self) -> list[dict[str, Any]]:
        """Fetch all planned workouts from Garmin Connect."""
        return self._client.get_workouts()

    def get_scheduled_workout_by_id(self, workout_id: str) -> Any:
        """Fetch scheduled calendar entries for a workout template (template ID, not schedule entry ID).

        Raises on 404 — used by reconciliation to detect missing calendar entries.
        """
        return self._client.get_scheduled_workout_by_id(workout_id)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    async def bulk_resync(self, workouts: list[dict[str, Any]]) -> list[str]:
        """Push multiple workouts, skipping any that are already completed.

        Args:
            workouts: List of formatted workout dicts.  A workout with
                ``completed=True`` is skipped silently.

        Returns:
            List of Garmin workout IDs for successfully pushed workouts.
        """
        ids: list[str] = []
        for workout in workouts:
            if workout.get("completed", False):
                continue
            garmin_id = await self.push_workout(workout)
            ids.append(garmin_id)
        return ids

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_with_retry(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Call *fn* with retry / exponential backoff on rate-limit errors.

        Sets ``self.last_sync_status`` to "synced" on success or "failed"
        after all retries are exhausted.

        Raises:
            Exception: the last exception when all retries fail.
        """
        backoff = _INITIAL_BACKOFF
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                result = fn(*args, **kwargs)
                self.last_sync_status = "synced"
                return result
            except Exception as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2

        self.last_sync_status = "failed"
        assert last_exc is not None  # always True here
        raise last_exc
