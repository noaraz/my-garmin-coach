from __future__ import annotations

from src.workout_resolver.estimator import estimate_distance, estimate_duration
from src.workout_resolver.models import WorkoutStep


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_step(**kwargs: object) -> WorkoutStep:
    defaults: dict[str, object] = {
        "order": 1,
        "type": "active",
        "duration_type": "time",
        "duration_value": 600.0,
        "duration_unit": "seconds",
        "target_type": "open",
        "target_zone": None,
        "target_low": None,
        "target_high": None,
        "notes": None,
        "repeat_count": None,
        "steps": [],
    }
    defaults.update(kwargs)
    return WorkoutStep(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# test_duration_simple
# ---------------------------------------------------------------------------


def test_duration_simple() -> None:
    # Arrange — three timed steps: 600 + 1800 + 300 = 2700 seconds
    steps = [
        _make_step(order=1, duration_type="time", duration_value=600.0, duration_unit="seconds"),
        _make_step(order=2, duration_type="time", duration_value=1800.0, duration_unit="seconds"),
        _make_step(order=3, duration_type="time", duration_value=300.0, duration_unit="seconds"),
    ]

    # Act
    total = estimate_duration(steps)

    # Assert
    assert total == 2700.0


# ---------------------------------------------------------------------------
# test_duration_with_repeats
# ---------------------------------------------------------------------------


def test_duration_with_repeats() -> None:
    # Arrange — warmup(600) + 4x(interval 300 + recovery 120) + cooldown(300)
    #           = 600 + 4*(300+120) + 300 = 600 + 1680 + 300 = 2580
    warmup = _make_step(
        order=1,
        type="warmup",
        duration_type="time",
        duration_value=600.0,
        duration_unit="seconds",
    )
    interval = _make_step(
        order=1,
        type="active",
        duration_type="time",
        duration_value=300.0,
        duration_unit="seconds",
    )
    recovery = _make_step(
        order=2,
        type="recovery",
        duration_type="time",
        duration_value=120.0,
        duration_unit="seconds",
    )
    repeat = _make_step(
        order=2,
        type="repeat",
        duration_type="time",
        duration_value=None,
        duration_unit=None,
        repeat_count=4,
        steps=[interval, recovery],
    )
    cooldown = _make_step(
        order=3,
        type="cooldown",
        duration_type="time",
        duration_value=300.0,
        duration_unit="seconds",
    )

    # Act
    total = estimate_duration([warmup, repeat, cooldown])

    # Assert
    assert total == 2580.0


# ---------------------------------------------------------------------------
# test_distance_simple
# ---------------------------------------------------------------------------


def test_distance_simple() -> None:
    # Arrange — three distance steps: 1000 + 8000 + 1000 = 10000 meters
    steps = [
        _make_step(order=1, duration_type="distance", duration_value=1000.0, duration_unit="meters"),
        _make_step(order=2, duration_type="distance", duration_value=8000.0, duration_unit="meters"),
        _make_step(order=3, duration_type="distance", duration_value=1000.0, duration_unit="meters"),
    ]

    # Act
    total = estimate_distance(steps)

    # Assert
    assert total == 10000.0


# ---------------------------------------------------------------------------
# test_lap_button_returns_none
# ---------------------------------------------------------------------------


def test_lap_button_returns_none() -> None:
    # Arrange — a step with lap_button duration_type cannot be estimated
    steps = [
        _make_step(
            order=1,
            duration_type="lap_button",
            duration_value=None,
            duration_unit=None,
        )
    ]

    # Act
    result = estimate_duration(steps)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# test_duration_repeat_with_lap_button_child_returns_none
# ---------------------------------------------------------------------------


def test_duration_repeat_with_lap_button_child_returns_none() -> None:
    # Arrange — repeat group contains a lap_button child → duration is indeterminate
    # This exercises line 19: child_dur is None → return None inside _step_duration
    lap_child = _make_step(
        order=1,
        duration_type="lap_button",
        duration_value=None,
        duration_unit=None,
    )
    repeat = _make_step(
        order=1,
        type="repeat",
        duration_type="time",
        duration_value=None,
        duration_unit=None,
        repeat_count=3,
        steps=[lap_child],
    )

    # Act
    result = estimate_duration([repeat])

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# test_duration_distance_step_contributes_zero
# ---------------------------------------------------------------------------


def test_duration_distance_step_contributes_none() -> None:
    # Arrange — a distance step has no time duration → estimate_duration returns None
    # This exercises line 30: distance steps return None in _step_duration
    steps = [
        _make_step(order=1, duration_type="distance", duration_value=5000.0, duration_unit="meters"),
    ]

    # Act
    result = estimate_duration(steps)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# test_distance_with_repeats
# ---------------------------------------------------------------------------


def test_distance_with_repeats() -> None:
    # Arrange — 2x(500m + 400m) = 2 * 900 = 1800m
    # This exercises lines 36-43: _step_distance for repeat groups
    interval = _make_step(
        order=1,
        type="active",
        duration_type="distance",
        duration_value=500.0,
        duration_unit="meters",
    )
    recovery = _make_step(
        order=2,
        type="recovery",
        duration_type="distance",
        duration_value=400.0,
        duration_unit="meters",
    )
    repeat = _make_step(
        order=1,
        type="repeat",
        duration_type="distance",
        duration_value=None,
        duration_unit=None,
        repeat_count=2,
        steps=[interval, recovery],
    )

    # Act
    result = estimate_distance([repeat])

    # Assert
    assert result == 1800.0


# ---------------------------------------------------------------------------
# test_distance_time_step_returns_none
# ---------------------------------------------------------------------------


def test_distance_time_step_returns_none() -> None:
    # Arrange — a time-based step has no distance → estimate_distance returns None
    # This exercises line 48: non-distance steps return None in _step_distance
    steps = [
        _make_step(order=1, duration_type="time", duration_value=600.0, duration_unit="seconds"),
    ]

    # Act
    result = estimate_distance(steps)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# test_distance_with_null_child_in_repeat_returns_none
# ---------------------------------------------------------------------------


def test_distance_repeat_with_time_child_returns_none() -> None:
    # Arrange — repeat group has a time child → distance is indeterminate
    # This exercises line 41: child_dist is None → return None inside _step_distance
    time_child = _make_step(
        order=1,
        type="active",
        duration_type="time",
        duration_value=300.0,
        duration_unit="seconds",
    )
    repeat = _make_step(
        order=1,
        type="repeat",
        duration_type="distance",
        duration_value=None,
        duration_unit=None,
        repeat_count=4,
        steps=[time_child],
    )

    # Act
    result = estimate_distance([repeat])

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# test_estimate_distance_propagates_none_from_mixed_steps
# ---------------------------------------------------------------------------


def test_estimate_distance_propagates_none_from_mixed_steps() -> None:
    # Arrange — first step has distance, second step is time-based
    # This exercises line 74: estimate_distance returns None when any step is None
    steps = [
        _make_step(order=1, duration_type="distance", duration_value=1000.0, duration_unit="meters"),
        _make_step(order=2, duration_type="time", duration_value=300.0, duration_unit="seconds"),
    ]

    # Act
    result = estimate_distance(steps)

    # Assert
    assert result is None
