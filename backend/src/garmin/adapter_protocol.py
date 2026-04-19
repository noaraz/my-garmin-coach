"""Shared protocol and exception hierarchy for Garmin adapters.

All Garmin adapter implementations (V1/garth, V2/native) implement
GarminAdapterProtocol and translate library-specific exceptions into
the unified hierarchy defined here.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Unified exception hierarchy
# ---------------------------------------------------------------------------

class GarminAdapterError(Exception):
    """Base exception for all Garmin adapter errors."""


class GarminAuthError(GarminAdapterError):
    """Authentication failed (invalid credentials, expired token)."""


class GarminRateLimitError(GarminAdapterError):
    """Garmin Connect returned 429 — rate limited."""


class GarminConnectionError(GarminAdapterError):
    """Network or connection error communicating with Garmin."""


class GarminNotFoundError(GarminAdapterError):
    """Garmin resource not found (404)."""


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class GarminAdapterProtocol(Protocol):
    """Interface contract for all Garmin adapter implementations."""

    def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]: ...

    def schedule_workout(self, workout_id: str, workout_date: str) -> dict[str, Any]: ...

    def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None: ...

    def delete_workout(self, workout_id: str) -> None: ...

    def unschedule_workout(self, schedule_id: str) -> None: ...

    def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict[str, Any]]: ...

    def get_workouts(self) -> list[dict[str, Any]]: ...

    def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]: ...

    def get_activity(self, activity_id: str) -> dict[str, Any]: ...

    def dump_token(self) -> str: ...
