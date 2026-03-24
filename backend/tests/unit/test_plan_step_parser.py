"""Unit tests for plan_step_parser.py — 95%+ coverage target."""
from __future__ import annotations

import pytest

from src.services.plan_step_parser import StepParseError, parse_steps_spec


class TestTimeBased:
    def test_single_minute_step(self) -> None:
        steps = parse_steps_spec("10m@Z1")
        assert steps == [
            {"type": "active", "duration_type": "time", "duration_sec": 600.0, "target_type": "pace_zone", "zone": 1}
        ]

    def test_single_second_step(self) -> None:
        steps = parse_steps_spec("90s@Z3")
        assert steps == [
            {"type": "active", "duration_type": "time", "duration_sec": 90.0, "target_type": "pace_zone", "zone": 3}
        ]

    def test_fractional_minutes(self) -> None:
        steps = parse_steps_spec("1.5m@Z2")
        assert steps[0]["duration_sec"] == pytest.approx(90.0)

    def test_multiple_time_steps(self) -> None:
        steps = parse_steps_spec("10m@Z1, 45m@Z2, 5m@Z1")
        assert len(steps) == 3
        assert steps[0] == {"type": "active", "duration_type": "time", "duration_sec": 600.0, "target_type": "pace_zone", "zone": 1}
        assert steps[1] == {"type": "active", "duration_type": "time", "duration_sec": 2700.0, "target_type": "pace_zone", "zone": 2}
        assert steps[2] == {"type": "active", "duration_type": "time", "duration_sec": 300.0, "target_type": "pace_zone", "zone": 1}

    def test_all_zones_1_to_5(self) -> None:
        for zone in range(1, 6):
            steps = parse_steps_spec(f"5m@Z{zone}")
            assert steps[0]["zone"] == zone


class TestDistanceBased:
    def test_single_km_step(self) -> None:
        steps = parse_steps_spec("2K@Z1")
        assert steps == [
            {"type": "active", "duration_type": "distance", "distance_m": 2000.0, "target_type": "pace_zone", "zone": 1}
        ]

    def test_fractional_km(self) -> None:
        steps = parse_steps_spec("0.4K@Z5")
        assert steps[0]["distance_m"] == pytest.approx(400.0)

    def test_multiple_distance_steps(self) -> None:
        steps = parse_steps_spec("2K@Z1, 5K@Z3, 1K@Z1")
        assert len(steps) == 3
        assert steps[1]["distance_m"] == pytest.approx(5000.0)
        assert steps[1]["zone"] == 3


class TestRepeatGroups:
    def test_simple_repeat(self) -> None:
        steps = parse_steps_spec("6x(90s@Z5 + 90s@Z1)")
        assert len(steps) == 1
        repeat = steps[0]
        assert repeat["type"] == "repeat"
        assert repeat["repeat_count"] == 6
        assert len(repeat["steps"]) == 2
        assert repeat["steps"][0]["duration_sec"] == 90.0
        assert repeat["steps"][0]["zone"] == 5
        assert repeat["steps"][1]["zone"] == 1

    def test_repeat_with_km_steps(self) -> None:
        steps = parse_steps_spec("4x(0.4K@Z5 + 0.2K@Z1)")
        repeat = steps[0]
        assert repeat["repeat_count"] == 4
        assert repeat["steps"][0]["distance_m"] == pytest.approx(400.0)

    def test_mixed_time_and_distance(self) -> None:
        steps = parse_steps_spec("10m@Z1, 6x(90s@Z5 + 60s@Z1), 5m@Z1")
        assert len(steps) == 3
        assert steps[0]["duration_type"] == "time"
        assert steps[1]["type"] == "repeat"
        assert steps[2]["duration_type"] == "time"

    def test_repeat_with_minute_steps(self) -> None:
        steps = parse_steps_spec("3x(3m@Z4 + 2m@Z2)")
        repeat = steps[0]
        assert repeat["repeat_count"] == 3
        assert repeat["steps"][0]["duration_sec"] == pytest.approx(180.0)


class TestWhitespaceHandling:
    def test_extra_spaces_around_commas(self) -> None:
        steps = parse_steps_spec("  10m@Z1 ,  20m@Z2  ")
        assert len(steps) == 2

    def test_spaces_inside_repeat(self) -> None:
        steps = parse_steps_spec("3x( 90s@Z5 + 60s@Z1 )")
        assert steps[0]["type"] == "repeat"
        assert len(steps[0]["steps"]) == 2


class TestCaseInsensitivity:
    def test_uppercase_X_in_repeat(self) -> None:
        steps = parse_steps_spec("6X(90s@Z5 + 90s@Z1)")
        assert steps[0]["repeat_count"] == 6

    def test_lowercase_k_accepted(self) -> None:
        # Parser is lenient: lowercase k is treated same as K
        steps = parse_steps_spec("2k@Z1")
        assert steps[0]["distance_m"] == pytest.approx(2000.0)


class TestErrorCases:
    def test_empty_string(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("   ")

    def test_invalid_zone_6(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("10m@Z6")

    def test_invalid_zone_0(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("10m@Z0")

    def test_unknown_unit(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("10h@Z1")

    def test_missing_zone(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("10m@")

    def test_missing_value(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("m@Z1")

    def test_missing_at_sign(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("10mZ1")

    def test_unmatched_open_paren(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("6x(90s@Z5")

    def test_unmatched_close_paren(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("90s@Z5)")

    def test_empty_repeat_body(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("6x()")

    def test_no_steps_found(self) -> None:
        # Comma only produces empty tokens
        with pytest.raises(StepParseError):
            parse_steps_spec(",")

    def test_invalid_step_inside_repeat(self) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec("3x(invalid@Z1 + 60s@Z2)")

    @pytest.mark.parametrize("spec", [
        "10m@Z6",
        "10m@Z-1",
        "10m@Za",
    ])
    def test_invalid_zone_variants(self, spec: str) -> None:
        with pytest.raises(StepParseError):
            parse_steps_spec(spec)
