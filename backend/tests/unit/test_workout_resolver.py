from __future__ import annotations

import pytest

from src.workout_resolver.exceptions import WorkoutResolveError
from src.workout_resolver.models import ResolvedStep, WorkoutStep
from src.workout_resolver.resolver import resolve_step, resolve_workout


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

HR_ZONES: dict[int, tuple[float, float]] = {
    1: (115, 141),
    2: (142, 156),
    3: (157, 163),
    4: (164, 170),
    5: (171, 185),
}

PACE_ZONES: dict[int, tuple[float, float]] = {
    1: (360, 420),
    2: (330, 359),
    3: (280, 300),
    4: (255, 279),
    5: (230, 254),
}


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
# test_resolve_hr_zone_step
# ---------------------------------------------------------------------------


def test_resolve_hr_zone_step() -> None:
    # Arrange
    step = _make_step(target_type="hr_zone", target_zone=2)

    # Act
    resolved = resolve_step(step, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)

    # Assert
    assert resolved.target_low == 142
    assert resolved.target_high == 156


# ---------------------------------------------------------------------------
# test_resolve_pace_zone_step
# ---------------------------------------------------------------------------


def test_resolve_pace_zone_step() -> None:
    # Arrange
    step = _make_step(target_type="pace_zone", target_zone=3)

    # Act
    resolved = resolve_step(step, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)

    # Assert
    assert resolved.target_low == 280
    assert resolved.target_high == 300


# ---------------------------------------------------------------------------
# test_resolve_open_unchanged
# ---------------------------------------------------------------------------


def test_resolve_open_unchanged() -> None:
    # Arrange
    step = _make_step(target_type="open", target_low=None, target_high=None)

    # Act
    resolved = resolve_step(step, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)

    # Assert
    assert resolved.target_type == "open"
    assert resolved.target_low is None
    assert resolved.target_high is None


# ---------------------------------------------------------------------------
# test_resolve_explicit_range_unchanged
# ---------------------------------------------------------------------------


def test_resolve_explicit_range_unchanged() -> None:
    # Arrange
    step = _make_step(target_type="hr_range", target_low=140.0, target_high=155.0)

    # Act
    resolved = resolve_step(step, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)

    # Assert
    assert resolved.target_type == "hr_range"
    assert resolved.target_low == 140.0
    assert resolved.target_high == 155.0


# ---------------------------------------------------------------------------
# test_resolve_repeat_children
# ---------------------------------------------------------------------------


def test_resolve_repeat_children() -> None:
    # Arrange
    child1 = _make_step(order=1, target_type="hr_zone", target_zone=2)
    child2 = _make_step(order=2, target_type="pace_zone", target_zone=4)
    repeat_step = _make_step(
        order=1,
        type="repeat",
        target_type="open",
        repeat_count=4,
        steps=[child1, child2],
    )

    # Act
    resolved = resolve_step(repeat_step, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)

    # Assert — children are resolved
    assert len(resolved.steps) == 2
    assert resolved.steps[0].target_low == 142
    assert resolved.steps[0].target_high == 156
    assert resolved.steps[1].target_low == 255
    assert resolved.steps[1].target_high == 279


# ---------------------------------------------------------------------------
# test_resolve_full_workout
# ---------------------------------------------------------------------------


def test_resolve_full_workout() -> None:
    # Arrange — warmup + 4x[interval(z4)+recovery(z1)] + cooldown
    warmup = _make_step(order=1, type="warmup", target_type="hr_zone", target_zone=1)
    interval = _make_step(order=1, type="active", target_type="hr_zone", target_zone=4)
    recovery = _make_step(order=2, type="recovery", target_type="hr_zone", target_zone=1)
    repeat = _make_step(
        order=2,
        type="repeat",
        target_type="open",
        repeat_count=4,
        steps=[interval, recovery],
    )
    cooldown = _make_step(order=3, type="cooldown", target_type="hr_zone", target_zone=1)
    workout = [warmup, repeat, cooldown]

    # Act
    resolved = resolve_workout(workout, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)

    # Assert
    assert resolved[0].target_low == 115  # z1 low
    assert resolved[0].target_high == 141  # z1 high
    assert resolved[1].steps[0].target_low == 164  # z4 low
    assert resolved[1].steps[0].target_high == 170  # z4 high
    assert resolved[1].steps[1].target_low == 115  # z1 low
    assert resolved[2].target_low == 115  # cooldown z1


# ---------------------------------------------------------------------------
# test_resolve_mixed_targets
# ---------------------------------------------------------------------------


def test_resolve_mixed_targets() -> None:
    # Arrange
    hr_step = _make_step(order=1, target_type="hr_zone", target_zone=2)
    pace_step = _make_step(order=2, target_type="pace_zone", target_zone=3)
    open_step = _make_step(order=3, target_type="open")
    workout = [hr_step, pace_step, open_step]

    # Act
    resolved = resolve_workout(workout, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)

    # Assert — each resolved independently
    assert resolved[0].target_low == 142
    assert resolved[0].target_high == 156
    assert resolved[1].target_low == 280
    assert resolved[1].target_high == 300
    assert resolved[2].target_type == "open"
    assert resolved[2].target_low is None


# ---------------------------------------------------------------------------
# test_resolve_missing_zone_raises
# ---------------------------------------------------------------------------


def test_resolve_missing_zone_raises() -> None:
    # Arrange — zone 6 does not exist (only 1-5)
    step = _make_step(target_type="hr_zone", target_zone=6)

    # Act / Assert
    with pytest.raises(WorkoutResolveError, match="6"):
        resolve_step(step, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)


# ---------------------------------------------------------------------------
# test_resolve_returns_new_objects
# ---------------------------------------------------------------------------


def test_resolve_returns_new_objects() -> None:
    # Arrange
    step = _make_step(target_type="hr_zone", target_zone=2)
    original_low = step.target_low  # None before resolution

    # Act
    resolved = resolve_step(step, hr_zones=HR_ZONES, pace_zones=PACE_ZONES)

    # Assert — original is not mutated
    assert step.target_low == original_low  # still None
    assert resolved is not step
    assert isinstance(resolved, ResolvedStep)
