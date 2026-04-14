"""Version-aware workout format bridge.

Isolates the rest of the codebase from garminconnect library changes.
V1: delegates to the existing format_workout() in formatter.py.
V2: builds typed RunningWorkout using garminconnect 0.3.x step builders.

The facade's build_workout() signature matches SyncOrchestrator's
formatter callable contract: (workout_name, steps, description) -> dict.
"""
from __future__ import annotations

from typing import Any

from src.garmin.formatter import format_workout


class WorkoutFacade:
    """Stable interface between workout templates and Garmin API format."""

    def __init__(self, auth_version: str = "v1") -> None:
        self._auth_version = auth_version

    def build_workout(
        self,
        workout_name: str,
        resolved_steps: list[dict[str, Any]],
        workout_description: str = "",
    ) -> dict[str, Any]:
        """Convert internal workout data to Garmin-uploadable format.

        Signature matches SyncOrchestrator's formatter callable contract.
        Both V1 and V2 return a dict — V2 builds from typed models then
        serializes to the same dict format for upload.
        """
        if self._auth_version == "v2":
            return self._build_v2(workout_name, resolved_steps, workout_description)
        return format_workout(workout_name, resolved_steps, workout_description)

    def _build_v2(
        self,
        workout_name: str,
        resolved_steps: list[dict[str, Any]],
        workout_description: str,
    ) -> dict[str, Any]:
        """Build workout dict using garminconnect 0.3.x step builders.

        For now, delegates to the same format_workout() since the Garmin
        workout JSON format hasn't changed — only the upload method differs.
        This method exists as the extension point for adopting typed models
        (RunningWorkout, create_warmup_step, etc.) in a follow-up.
        """
        return format_workout(workout_name, resolved_steps, workout_description)
