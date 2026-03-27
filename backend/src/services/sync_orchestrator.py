from __future__ import annotations

from typing import Any, Callable


class SyncOrchestrator:
    """Orchestrate the full resolve → format → push → schedule pipeline.

    All collaborators are injected so the orchestrator remains pure (no
    direct I/O) and is trivially testable.

    Args:
        sync_service: An instance of GarminSyncService (or compatible mock).
        formatter:    Callable that accepts (workout_name, steps, description)
                      and returns a Garmin-formatted workout dict.
        resolver:     Callable that accepts (steps, ...) and returns resolved
                      step dicts ready for formatting.
    """

    def __init__(
        self,
        sync_service: Any,
        formatter: Callable[..., dict[str, Any]],
        resolver: Callable[..., list[Any]],
    ) -> None:
        self._sync_service = sync_service
        self._formatter = formatter
        self._resolver = resolver

    @property
    def adapter(self) -> Any:
        """Expose the underlying Garmin adapter for reuse (e.g. activity fetch)."""
        return self._sync_service._client

    # ------------------------------------------------------------------
    # Single-workout sync
    # ------------------------------------------------------------------

    async def sync_workout(
        self,
        resolved_steps: list[Any],
        workout_name: str,
        date: str,
        workout_description: str = "",
    ) -> tuple[str, str | None]:
        """Resolve, format, push and schedule a single workout.

        Args:
            resolved_steps:      Pre-resolved step dicts (already zone-expanded).
            workout_name:        Display name for the Garmin workout.
            date:                Calendar date string (YYYY-MM-DD).
            workout_description: Optional notes shown in Garmin Connect.

        Returns:
            Tuple of (garmin_workout_id, garmin_schedule_id).
            garmin_schedule_id is None when Garmin's response omits it.
        """
        formatted = self._formatter(workout_name, resolved_steps, workout_description)
        garmin_id: str = await self._sync_service.push_workout(formatted)
        schedule_id = self._sync_service.schedule_workout(garmin_id, date)
        return garmin_id, schedule_id

    def get_workouts(self) -> list[dict[str, Any]]:
        """Fetch all planned workouts from Garmin Connect."""
        return self._sync_service.get_workouts()

    def delete_workout(self, garmin_workout_id: str) -> None:
        """Permanently remove a workout from Garmin Connect."""
        self._sync_service.delete_workout(garmin_workout_id)

    def get_scheduled_workout_by_id(self, workout_id: str) -> Any:
        """Fetch scheduled calendar entries for a workout template. Raises on 404."""
        return self._sync_service.get_scheduled_workout_by_id(workout_id)

    def reschedule_workout(self, garmin_workout_id: str, date: str) -> str | None:
        """Schedule an existing Garmin workout template on a new date.

        Cheaper than sync_workout — skips the delete+re-upload of the template.
        Returns the new garmin_schedule_id, or None if the response omits it.
        """
        return self._sync_service.schedule_workout(garmin_workout_id, date)

    # ------------------------------------------------------------------
    # Bulk resync
    # ------------------------------------------------------------------

    async def resync_all(self, workouts: list[dict[str, Any]]) -> dict[str, int]:
        """Push and schedule every workout in *workouts*.

        Each element of *workouts* is expected to have at least:
            - ``name``        (str) — workout display name
            - ``steps``       (list) — raw or resolved step dicts
            - ``date``        (str) — calendar date YYYY-MM-DD
            - ``description`` (str, optional) — notes shown in Garmin Connect

        Returns:
            A dict with ``synced`` and ``failed`` counts.
        """
        synced = 0
        failed = 0

        for workout in workouts:
            try:
                formatted = self._formatter(
                    workout.get("name", ""),
                    workout.get("steps", []),
                    workout.get("description", ""),
                )
                garmin_id: str = await self._sync_service.push_workout(formatted)
                date = workout.get("date", "")
                if date:
                    self._sync_service.schedule_workout(garmin_id, date)
                synced += 1
            except Exception:  # noqa: BLE001
                failed += 1

        return {"synced": synced, "failed": failed}
