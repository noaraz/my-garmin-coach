"""V1 Garmin adapter using garth (legacy SSO form flow).

Bridges the garminconnect 0.2.x/garth interface to GarminAdapterProtocol.
All garth/requests exceptions are translated to the unified hierarchy.
"""
from __future__ import annotations

from typing import Any

import garminconnect
import requests
from curl_cffi import requests as cffi_requests
from garth.exc import GarthHTTPError

from src.garmin.adapter_protocol import (
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)


def _get_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from various exception types."""
    # GarthHTTPError wraps requests.HTTPError
    if isinstance(exc, GarthHTTPError):
        inner = getattr(exc, "error", None)
        response = getattr(inner, "response", None)
        if response is not None:
            return getattr(response, "status_code", None)
    # curl_cffi or requests HTTPError
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)
    return None


def _translate_exception(exc: Exception) -> None:
    """Translate garth/requests exceptions to unified hierarchy. Always raises."""
    status = _get_status_code(exc)
    if status == 404:
        raise GarminNotFoundError(str(exc)) from exc
    if status == 429:
        raise GarminRateLimitError(str(exc)) from exc
    if status == 401:
        raise GarminAuthError(str(exc)) from exc
    raise GarminConnectionError(str(exc)) from exc


class GarminAdapter:
    """V1 adapter: wraps garminconnect.Garmin (garth-based) with unified exceptions."""

    def __init__(self, client: garminconnect.Garmin) -> None:
        self._client = client

    def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]:
        """Upload a workout and return the Garmin response (contains workoutId)."""
        try:
            return self._client.upload_workout(formatted_workout)
        except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
            _translate_exception(exc)
            raise  # unreachable, satisfies type checker

    def schedule_workout(self, workout_id: str, workout_date: str) -> dict[str, Any]:
        """Schedule a workout on a specific date via the Garmin Connect API."""
        try:
            url = f"{self._client.garmin_workouts_schedule_url}/{workout_id}"
            resp = self._client.garth.post("connectapi", url, json={"date": workout_date}, api=True)
            return resp.json() if hasattr(resp, "json") else {}
        except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
            _translate_exception(exc)
            raise

    def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None:
        """Update an existing Garmin workout in-place."""
        try:
            url = f"/workout-service/workout/{workout_id}"
            self._client.garth.put("connectapi", url, json=formatted_workout, api=True)
        except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
            _translate_exception(exc)

    def delete_workout(self, workout_id: str) -> None:
        """Permanently delete a workout from Garmin Connect."""
        try:
            url = f"/workout-service/workout/{workout_id}"
            self._client.garth.delete("connectapi", url, api=True)
        except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
            _translate_exception(exc)

    def unschedule_workout(self, schedule_id: str) -> None:
        """Remove a single calendar schedule entry from Garmin Connect."""
        try:
            url = f"/workout-service/schedule/{schedule_id}"
            self._client.garth.delete("connectapi", url, api=True)
        except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
            _translate_exception(exc)

    def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch activities from Garmin within a date range."""
        try:
            return self._client.get_activities_by_date(start_date, end_date)
        except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
            _translate_exception(exc)
            raise

    def get_workouts(self) -> list[dict[str, Any]]:
        """Fetch all planned workouts from Garmin Connect."""
        try:
            return self._client.get_workouts()
        except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
            _translate_exception(exc)
            raise

    def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
        """Fetch scheduled calendar items for a given month from Garmin.

        **Important**: Garmin uses 0-indexed months (Jan=0, Dec=11).
        Callers pass 1-indexed months (Python ``date.month``); this method
        converts internally.
        """
        try:
            garmin_month = month - 1
            path = f"/calendar-service/year/{year}/month/{garmin_month}"
            result = self._client.connectapi(path)
            return result.get("calendarItems", []) if isinstance(result, dict) else []
        except (GarthHTTPError, requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError) as exc:
            _translate_exception(exc)
            raise

    def dump_token(self) -> str:
        """Return the current garth token state as JSON."""
        return self._client.garth.dumps()
