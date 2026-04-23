"""Unit tests for plan_import_service diff logic."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.plan_import_service import (
    ParsedWorkout,
    _compute_diff,
    commit_plan,
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

    def test_compute_diff_uses_reference_date_for_past_cutoff(self) -> None:
        # reference_date makes the cutoff deterministic — workout dated 2026-04-01
        # is past relative to 2026-04-12, future relative to 2026-03-01
        active = [_active("2026-04-01", "Old Run", "30m@Z2")]

        past = _compute_diff([], active, reference_date=date(2026, 4, 12))
        future = _compute_diff([], active, reference_date=date(2026, 3, 1))

        assert len(past.past_locked) == 1
        assert len(past.removed) == 0
        assert len(future.removed) == 1
        assert len(future.past_locked) == 0

    def test_today_workout_not_in_new_plan_is_past_locked(self) -> None:
        # A workout rescheduled to today, absent from the new plan, should be preserved
        # (not removed) — past_locked uses <= today (inclusive)
        today = datetime.now(timezone.utc).date()
        today_str = today.isoformat()
        incoming: list[ParsedWorkout] = []
        active = [_active(today_str, "Today Run", "30m@Z2")]

        result = _compute_diff(incoming, active, reference_date=today)

        assert len(result.past_locked) == 1
        assert result.past_locked[0].date == today_str
        assert len(result.removed) == 0

    def test_rescheduled_paired_workout_shown_as_completed_locked_not_removed(self) -> None:
        # Workout was planned April 24, rescheduled to April 23 (today), then paired.
        # completed_dates has "2026-04-23" (DB date) but plan JSON has "2026-04-24".
        # The plan date should still be treated as completed_locked, not removed.
        incoming: list[ParsedWorkout] = []
        active = [_active("2026-04-24", "Long Run 7K", "10m@Z1 + 50m@Z2")]

        # completed_dates reflects the rescheduled DB date AND the plan date (from helper)
        result = _compute_diff(incoming, active, completed_dates={"2026-04-23", "2026-04-24"})

        assert len(result.completed_locked) == 0  # absent from incoming → silent preserve
        assert len(result.removed) == 0
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


class TestCommitPlanPastLocked:
    async def test_commit_plan_preserves_past_workouts_not_in_new_plan(self) -> None:
        """Past workouts absent from the new plan are re-associated — workout_count includes them."""
        from src.db.models import ScheduledWorkout, TrainingPlan

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        past_date = date(2020, 1, 1)
        future_date = date(2099, 1, 1)
        reference = date(2026, 4, 12)  # fixed "today"

        draft = TrainingPlan(
            id=99, user_id=1, name="Short Plan", status="draft", source="csv",
            start_date=future_date,
            parsed_workouts=json.dumps([{
                "date": "2099-01-01", "name": "Easy Run",
                "steps_spec": "30m@Z2", "sport_type": "running", "steps": [],
            }]),
            created_at=now, updated_at=now,
        )
        active = TrainingPlan(
            id=1, user_id=1, name="Old Plan", status="active", source="csv",
            start_date=past_date,
            parsed_workouts=json.dumps([{
                "date": "2020-01-01", "name": "Old Run",
                "steps_spec": "30m@Z2", "sport_type": "running",
            }]),
            created_at=now, updated_at=now,
        )
        past_sw = ScheduledWorkout(
            id=42, user_id=1, date=past_date, training_plan_id=1,
            sync_status="synced", completed=False, created_at=now, updated_at=now,
        )

        session = AsyncMock()
        session.get.return_value = draft

        sw_result = MagicMock()
        sw_result.all.return_value = [past_sw]
        completed_result = MagicMock()
        completed_result.all.return_value = []
        template_result = MagicMock()
        template_result.all.return_value = []
        session.exec.side_effect = [sw_result, completed_result, template_result]

        with patch("src.services.plan_import_service.get_active_plan", return_value=active):
            result = await commit_plan(
                session=session, user_id=1, plan_id=99, reference_date=reference,
            )

        # 1 kept past workout + 1 new future workout = 2 total
        assert result.workout_count == 2
