from __future__ import annotations


class WorkoutResolveError(Exception):
    """Raised when a workout step references a zone that does not exist."""
