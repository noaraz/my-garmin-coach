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

    def get_scheduled_workout_by_id(self, schedule_id: str) -> dict[str, Any]:
        """Fetch a Garmin calendar entry by its schedule ID.

        Raises an exception (typically HTTPError with 404) when the entry no
        longer exists — used by reconciliation to detect removed calendar entries.
        """
        url = f"{self._client.garmin_workouts_schedule_url}/{schedule_id}"
        return self._client.connectapi(url)

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

    def dump_token(self) -> str:
        """Return the current garth token state as JSON.

        garth may refresh the OAuth2 token in-memory during API calls.
        Call this after sync to capture any refreshed token for DB persistence.
        """
        return self._client.garth.dumps()
