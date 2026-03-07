from __future__ import annotations

from typing import Any

from src.db.database import get_session
from src.services.sync_orchestrator import SyncOrchestrator


def _noop_formatter(name: str, steps: list[Any]) -> dict[str, Any]:
    """No-op formatter used when no real Garmin client is configured."""
    return {"workoutName": name, "steps": steps}


def _noop_resolver(steps: list[Any], **_kwargs: Any) -> list[Any]:
    """No-op resolver used when no real Garmin client is configured."""
    return steps


class _NoopGarminClient:
    """Placeholder client — raises if called without proper auth configuration."""

    def add_workout(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError(
            "Garmin client is not configured. Override get_sync_service() "
            "or configure Garmin credentials."
        )

    def schedule_workout(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Garmin client is not configured.")

    def update_workout(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Garmin client is not configured.")

    def delete_workout(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Garmin client is not configured.")


def get_sync_service() -> SyncOrchestrator:
    """Provide a SyncOrchestrator instance.

    In production this returns an orchestrator wired to the real Garmin client
    once auth is implemented.  In tests, override this dependency with a mock.

    Returns:
        A SyncOrchestrator backed by the noop client until auth is wired up.
    """
    from src.garmin.sync_service import GarminSyncService

    client = _NoopGarminClient()
    sync_service = GarminSyncService(client)
    return SyncOrchestrator(
        sync_service=sync_service,
        formatter=_noop_formatter,
        resolver=_noop_resolver,
    )


__all__ = ["get_session", "get_sync_service"]
