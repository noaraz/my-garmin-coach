"""V2 Garmin adapter for garminconnect 0.3.x (native DI OAuth).

Implements GarminAdapterProtocol using the new library's native methods.
All garminconnect-specific exceptions are translated to the unified hierarchy.
"""
from __future__ import annotations

from typing import Any

import garminconnect

from src.garmin.adapter_protocol import (
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)


def _translate_exception(exc: Exception) -> None:
    """Translate garminconnect 0.3.x exceptions to unified hierarchy. Always raises."""
    if isinstance(exc, garminconnect.GarminConnectAuthenticationError):
        raise GarminAuthError(str(exc)) from exc
    if isinstance(exc, garminconnect.GarminConnectTooManyRequestsError):
        raise GarminRateLimitError(str(exc)) from exc
    # GarminConnectConnectionError may carry a status_code for 404s
    status = getattr(exc, "status_code", None)
    if status == 404:
        raise GarminNotFoundError(str(exc)) from exc
    if "404" in str(exc):
        raise GarminNotFoundError(str(exc)) from exc
    raise GarminConnectionError(str(exc)) from exc


class GarminAdapterV2:
    """Wraps garminconnect 0.3.x Garmin client with the standard adapter interface."""

    def __init__(self, client: garminconnect.Garmin) -> None:
        self._client = client

    def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]:
        """Upload a workout via connectapi."""
        try:
            return self._client.connectapi(
                "/workout-service/workout",
                method="POST",
                json=formatted_workout,
            )
        except Exception as exc:  # noqa: BLE001  # noqa: BLE001
            _translate_exception(exc)
            raise  # unreachable, satisfies type checker

    def schedule_workout(self, workout_id: str, workout_date: str) -> dict[str, Any]:
        """Schedule a workout on a specific date."""
        try:
            return self._client.schedule_workout(workout_id, workout_date)
        except Exception as exc:  # noqa: BLE001
            _translate_exception(exc)
            raise

    def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None:
        """Update an existing Garmin workout in-place."""
        try:
            self._client.connectapi(
                f"/workout-service/workout/{workout_id}",
                method="PUT",
                json=formatted_workout,
            )
        except Exception as exc:  # noqa: BLE001
            _translate_exception(exc)

    def delete_workout(self, workout_id: str) -> None:
        """Permanently delete a workout from Garmin Connect."""
        try:
            self._client.delete_workout(workout_id)
        except Exception as exc:  # noqa: BLE001
            _translate_exception(exc)

    def unschedule_workout(self, schedule_id: str) -> None:
        """Remove a single calendar schedule entry."""
        try:
            self._client.unschedule_workout(schedule_id)
        except Exception as exc:  # noqa: BLE001
            _translate_exception(exc)

    def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch activities from Garmin within a date range."""
        try:
            return self._client.get_activities_by_date(start_date, end_date)
        except Exception as exc:  # noqa: BLE001
            _translate_exception(exc)
            raise

    def get_workouts(self) -> list[dict[str, Any]]:
        """Fetch all planned workouts from Garmin Connect."""
        try:
            return self._client.get_workouts()
        except Exception as exc:  # noqa: BLE001
            _translate_exception(exc)
            raise

    def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
        """Fetch calendar items. Converts 1-indexed month to Garmin's 0-indexed."""
        try:
            garmin_month = month - 1
            path = f"/calendar-service/year/{year}/month/{garmin_month}"
            result = self._client.connectapi(path)
            return result.get("calendarItems", []) if isinstance(result, dict) else []
        except Exception as exc:  # noqa: BLE001
            _translate_exception(exc)
            raise

    def dump_token(self) -> str:
        """Serialize current token state as JSON string."""
        return self._client.client.dumps()
