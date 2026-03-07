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
