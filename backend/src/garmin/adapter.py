"""Shared Garmin client adapter.

Bridges the garminconnect library interface to the interface expected by
GarminSyncService and ActivityFetchService.
"""
from __future__ import annotations

from typing import Any

import garminconnect


class GarminAdapter:
    """Wraps garminconnect.Garmin to provide a clean interface."""

    def __init__(self, client: garminconnect.Garmin) -> None:
        self._client = client

    def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]:
        """Upload a workout and return the Garmin response (contains workoutId)."""
        return self._client.upload_workout(formatted_workout)

    def schedule_workout(self, workout_id: str, workout_date: str) -> dict[str, Any]:
        """Schedule a workout on a specific date via the Garmin Connect API.

        Returns the raw Garmin response dict, which typically includes
        ``workoutScheduleId`` — the schedule entry ID used for reconciliation.
        """
        url = f"{self._client.garmin_workouts_schedule_url}/{workout_id}"
        resp = self._client.garth.post("connectapi", url, json={"date": workout_date}, api=True)
        return resp.json() if hasattr(resp, "json") else {}

    def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None:
        """Update an existing Garmin workout in-place."""
        url = f"/workout-service/workout/{workout_id}"
        self._client.garth.put("connectapi", url, json=formatted_workout, api=True)

    def delete_workout(self, workout_id: str) -> None:
        """Permanently delete a workout from Garmin Connect."""
        url = f"/workout-service/workout/{workout_id}"
        self._client.garth.delete("connectapi", url, api=True)

    def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch activities from Garmin within a date range."""
        return self._client.get_activities_by_date(start_date, end_date)

    def get_workouts(self) -> list[dict[str, Any]]:
        """Fetch all planned workouts from Garmin Connect.

        Returns a list of Garmin workout dicts, each containing at minimum
        ``workoutId`` and ``workoutName``.
        """
        return self._client.get_workouts()

    def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
        """Fetch scheduled calendar items for a given month from Garmin.

        Calls ``/calendar-service/year/{year}/month/{month}`` and returns
        the ``calendarItems`` list.  Each item has at minimum ``workoutId``,
        ``date`` (YYYY-MM-DD), and ``title``.
        """
        path = f"/calendar-service/year/{year}/month/{month}"
        result = self._client.connectapi(path)
        return result.get("calendarItems", []) if isinstance(result, dict) else []

    def dump_token(self) -> str:
        """Return the current garth token state as JSON.

        garth may refresh the OAuth2 token in-memory during API calls.
        Call this after sync to capture any refreshed token for DB persistence.
        """
        return self._client.garth.dumps()
