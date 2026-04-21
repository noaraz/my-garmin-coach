from __future__ import annotations

from typing import Any

from src.garmin.adapter_protocol import (
    GarminAdapterError,
    GarminAdapterProtocol,
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)


class TestGarminAdapterProtocol:
    """Verify the protocol and exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        """All specific exceptions are subclasses of GarminAdapterError."""
        assert issubclass(GarminAuthError, GarminAdapterError)
        assert issubclass(GarminRateLimitError, GarminAdapterError)
        assert issubclass(GarminConnectionError, GarminAdapterError)
        assert issubclass(GarminNotFoundError, GarminAdapterError)

    def test_catch_all_with_base(self) -> None:
        """Catching GarminAdapterError catches all subtypes."""
        for exc_cls in (GarminAuthError, GarminRateLimitError, GarminConnectionError, GarminNotFoundError):
            try:
                raise exc_cls("test")
            except GarminAdapterError:
                pass  # should be caught

    def test_protocol_structural_typing(self) -> None:
        """A class matching the protocol is accepted by runtime_checkable."""
        class FakeAdapter:
            def add_workout(self, formatted_workout: dict[str, Any]) -> dict[str, Any]:
                return {}
            def schedule_workout(self, workout_id: str, workout_date: str) -> dict[str, Any]:
                return {}
            def update_workout(self, workout_id: str, formatted_workout: dict[str, Any]) -> None:
                pass
            def delete_workout(self, workout_id: str) -> None:
                pass
            def unschedule_workout(self, schedule_id: str) -> None:
                pass
            def get_activities_by_date(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
                return []
            def get_workouts(self) -> list[dict[str, Any]]:
                return []
            def get_calendar_items(self, year: int, month: int) -> list[dict[str, Any]]:
                return []
            def get_activity(self, activity_id: str) -> dict[str, Any]:
                return {}
            def get_activity_splits(self, activity_id: str) -> list[dict]:
                return []
            def dump_token(self) -> str:
                return ""

        assert isinstance(FakeAdapter(), GarminAdapterProtocol)
