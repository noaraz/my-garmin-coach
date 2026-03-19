from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core import cache


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Clear cache before each test to prevent cross-test contamination."""
    cache.clear()


@pytest.fixture
def mock_garmin_client() -> MagicMock:
    client = MagicMock()
    client.login.return_value = None
    client.get_workouts.return_value = []
    client.add_workout.return_value = {"workoutId": "garmin-12345"}
    client.schedule_workout.return_value = None
    client.update_workout.return_value = None
    client.delete_workout.return_value = None
    return client
