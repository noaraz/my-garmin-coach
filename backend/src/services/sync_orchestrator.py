from __future__ import annotations

from typing import Any, Callable


class SyncOrchestrator:
    """Orchestrate the full resolve → format → push → schedule pipeline.

    All collaborators are injected so the orchestrator remains pure (no
    direct I/O) and is trivially testable.

    Args:
        sync_service: An instance of GarminSyncService (or compatible mock).
        formatter:    Callable that accepts (workout_name, steps) and returns
                      a Garmin-formatted workout dict.
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

    # ------------------------------------------------------------------
    # Single-workout sync
    # ------------------------------------------------------------------

    def sync_workout(
        self,
        resolved_steps: list[Any],
        workout_name: str,
        date: str,
        workout_description: str = "",
    ) -> str:
        """Resolve, format, push and schedule a single workout.

        Args:
            resolved_steps:      Pre-resolved step dicts (already zone-expanded).
            workout_name:        Display name for the Garmin workout.
            date:                Calendar date string (YYYY-MM-DD).
            workout_description: Optional notes shown in Garmin Connect.

        Returns:
            The Garmin workout ID assigned after the push.
        """
        formatted = self._formatter(workout_name, resolved_steps, workout_description)
        garmin_id: str = self._sync_service.push_workout(formatted)
        self._sync_service.schedule_workout(garmin_id, date)
        return garmin_id

    def delete_workout(self, garmin_workout_id: str) -> None:
        """Permanently remove a workout from Garmin Connect."""
        self._sync_service.delete_workout(garmin_workout_id)

    # ------------------------------------------------------------------
    # Bulk resync
    # ------------------------------------------------------------------

    def resync_all(self, workouts: list[dict[str, Any]]) -> dict[str, int]:
        """Push and schedule every workout in *workouts*.

        Each element of *workouts* is expected to have at least:
            - ``name``  (str) — workout display name
            - ``steps`` (list) — raw or resolved step dicts
            - ``date``  (str) — calendar date YYYY-MM-DD

        Returns:
            A dict with ``synced`` and ``failed`` counts.
        """
        synced = 0
        failed = 0

        for workout in workouts:
            try:
                formatted = self._formatter(
                    workout.get("name", ""), workout.get("steps", [])
                )
                garmin_id: str = self._sync_service.push_workout(formatted)
                date = workout.get("date", "")
                if date:
                    self._sync_service.schedule_workout(garmin_id, date)
                synced += 1
            except Exception:  # noqa: BLE001
                failed += 1

        return {"synced": synced, "failed": failed}
