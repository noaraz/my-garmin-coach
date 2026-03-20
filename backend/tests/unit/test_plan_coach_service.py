"""Unit tests for plan_coach_service.py — build_system_prompt and history truncation."""
from __future__ import annotations



from src.db.models import AthleteProfile, GarminActivity, HRZone, PaceZone
from src.services.plan_coach_service import (
    _HISTORY_TRUNCATION,
    _format_pace,
    build_system_prompt,
)


def _make_profile(lthr: int | None = 155, threshold_pace: float | None = 300.0, max_hr: int | None = 185) -> AthleteProfile:
    return AthleteProfile(
        id=1,
        name="Athlete",
        user_id=1,
        lthr=lthr,
        threshold_pace=threshold_pace,
        max_hr=max_hr,
    )


def _make_hr_zones() -> list[HRZone]:
    return [
        HRZone(id=i, profile_id=1, user_id=1, zone_number=i, name=f"Z{i}",
               lower_bpm=float(100 + (i - 1) * 20), upper_bpm=float(120 + (i - 1) * 20),
               calculation_method="friel", pct_lower=0.5, pct_upper=0.6)
        for i in range(1, 6)
    ]


def _make_pace_zones() -> list[PaceZone]:
    return [
        PaceZone(id=i, profile_id=1, user_id=1, zone_number=i, name=f"Z{i}",
                 lower_pace=float(400 - i * 30), upper_pace=float(420 - i * 30),
                 calculation_method="daniels", pct_lower=0.5, pct_upper=0.6)
        for i in range(1, 6)
    ]


def _make_activity(days_ago: int = 5) -> GarminActivity:
    from datetime import datetime, timezone, timedelta
    act_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date()
    return GarminActivity(
        id=1,
        user_id=1,
        garmin_activity_id="act_001",
        activity_type="running",
        name="Easy Run",
        start_time=datetime.now(timezone.utc).replace(tzinfo=None),
        date=act_date,
        duration_sec=3600.0,
        distance_m=10000.0,
        avg_pace_sec_per_km=360.0,
        avg_hr=140.0,
    )


class TestFormatPace:
    def test_format_pace_round_minutes(self) -> None:
        assert _format_pace(300.0) == "5:00/km"

    def test_format_pace_with_seconds(self) -> None:
        assert _format_pace(375.0) == "6:15/km"

    def test_format_pace_sub_minute(self) -> None:
        assert _format_pace(55.0) == "0:55/km"


class TestBuildSystemPrompt:
    def test_prompt_includes_lthr_when_set(self) -> None:
        profile = _make_profile(lthr=155)
        prompt = build_system_prompt(profile, [], [], [])
        assert "155" in prompt
        assert "LTHR" in prompt

    def test_prompt_includes_threshold_pace_when_set(self) -> None:
        profile = _make_profile(threshold_pace=300.0)
        prompt = build_system_prompt(profile, [], [], [])
        assert "5:00/km" in prompt

    def test_prompt_omits_lthr_when_none(self) -> None:
        profile = _make_profile(lthr=None)
        prompt = build_system_prompt(profile, [], [], [])
        assert "LTHR" not in prompt

    def test_prompt_omits_threshold_pace_when_none(self) -> None:
        profile = _make_profile(threshold_pace=None)
        prompt = build_system_prompt(profile, [], [], [])
        assert "Threshold pace" not in prompt

    def test_prompt_includes_hr_zones(self) -> None:
        hr_zones = _make_hr_zones()
        prompt = build_system_prompt(_make_profile(), hr_zones, [], [])
        assert "Heart Rate Zones" in prompt
        assert "Z1" in prompt
        assert "Z5" in prompt

    def test_prompt_includes_pace_zones(self) -> None:
        pace_zones = _make_pace_zones()
        prompt = build_system_prompt(_make_profile(), [], pace_zones, [])
        assert "Pace Zones" in prompt

    def test_prompt_includes_recent_activities_when_present(self) -> None:
        activities = [_make_activity(days_ago=3)]
        prompt = build_system_prompt(_make_profile(), [], [], activities)
        assert "Recent Training" in prompt
        assert "running" in prompt
        assert "10.0km" in prompt

    def test_prompt_omits_activity_section_when_empty(self) -> None:
        prompt = build_system_prompt(_make_profile(), [], [], [])
        assert "Recent Training" not in prompt

    def test_prompt_includes_step_format_spec(self) -> None:
        prompt = build_system_prompt(_make_profile(), [], [], [])
        assert "steps_spec" in prompt
        assert "Z1" in prompt

    def test_prompt_includes_output_instruction(self) -> None:
        prompt = build_system_prompt(_make_profile(), [], [], [])
        assert "```json" in prompt
        assert "date" in prompt
        assert "steps_spec" in prompt

    def test_hr_zones_sorted_by_zone_number(self) -> None:
        # Zones given in reverse order; prompt should list Z1 before Z5
        hr_zones = list(reversed(_make_hr_zones()))
        prompt = build_system_prompt(_make_profile(), hr_zones, [], [])
        z1_pos = prompt.index("Z1")
        z5_pos = prompt.rindex("Z5")
        assert z1_pos < z5_pos


class TestHistoryTruncation:
    def test_truncation_constant_is_40(self) -> None:
        assert _HISTORY_TRUNCATION == 40
