"""Unit tests for plan_import_service diff logic."""
from __future__ import annotations

from src.services.plan_import_service import (
    ParsedWorkout,
    _compute_diff,
)


def _pw(date: str, name: str, steps_spec: str) -> ParsedWorkout:
    return ParsedWorkout(date=date, name=name, steps_spec=steps_spec, steps=[])


def _active(date: str, name: str, steps_spec: str) -> dict:
    return {"date": date, "name": name, "steps_spec": steps_spec}


class TestComputeDiff:
    def test_unchanged_when_same_name_and_steps(self) -> None:
        incoming = [_pw("2026-04-07", "Easy Run", "30m@Z2")]
        active = [_active("2026-04-07", "Easy Run", "30m@Z2")]

        result = _compute_diff(incoming, active)

        assert len(result.unchanged) == 1
        assert result.unchanged[0].date == "2026-04-07"
        assert len(result.added) == 0
        assert len(result.changed) == 0

    def test_changed_when_steps_differ_populates_before_after(self) -> None:
        incoming = [_pw("2026-04-07", "Easy Run", "40m@Z2")]
        active = [_active("2026-04-07", "Easy Run", "30m@Z2")]

        result = _compute_diff(incoming, active)

        assert len(result.changed) == 1
        diff = result.changed[0]
        assert diff.old_steps_spec == "30m@Z2"
        assert diff.new_steps_spec == "40m@Z2"
        assert diff.old_name == "Easy Run"
        assert len(result.unchanged) == 0

    def test_completed_locked_overrides_changed(self) -> None:
        incoming = [_pw("2026-04-07", "Easy Run", "40m@Z2")]
        active = [_active("2026-04-07", "Easy Run", "30m@Z2")]

        result = _compute_diff(incoming, active, completed_dates={"2026-04-07"})

        assert len(result.completed_locked) == 1
        assert result.completed_locked[0].date == "2026-04-07"
        assert len(result.changed) == 0
        assert len(result.unchanged) == 0

    def test_past_workout_not_in_new_plan_goes_to_past_locked(self) -> None:
        # A workout from the past that's absent from the new plan should be preserved
        incoming: list[ParsedWorkout] = []
        active = [_active("2020-01-01", "Old Run", "30m@Z2")]

        result = _compute_diff(incoming, active)

        assert len(result.past_locked) == 1
        assert result.past_locked[0].date == "2020-01-01"
        assert result.past_locked[0].name == "Old Run"
        assert len(result.removed) == 0

    def test_future_workout_not_in_new_plan_goes_to_removed(self) -> None:
        # A workout in the future that's absent from the new plan should be removed
        incoming: list[ParsedWorkout] = []
        active = [_active("2099-12-31", "Future Run", "30m@Z2")]

        result = _compute_diff(incoming, active)

        assert len(result.removed) == 1
        assert result.removed[0].date == "2099-12-31"
        assert len(result.past_locked) == 0

    def test_past_completed_workout_not_in_new_plan_is_silently_preserved(self) -> None:
        # A workout that is both past and completed, absent from the new plan,
        # is silently kept (not in any diff bucket) — completed_dates gate prevents deletion
        incoming: list[ParsedWorkout] = []
        active = [_active("2020-01-01", "Old Run", "30m@Z2")]

        result = _compute_diff(incoming, active, completed_dates={"2020-01-01"})

        assert len(result.completed_locked) == 0
        assert len(result.past_locked) == 0
        assert len(result.removed) == 0
