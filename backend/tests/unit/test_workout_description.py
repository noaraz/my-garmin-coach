"""Tests for workout_description — mirrors frontend generateDescription.ts."""
from __future__ import annotations

import json

import pytest

from src.services.workout_description import generate_description, generate_description_from_steps


class TestZoneLabelOpenTargetType:
    def test_open_target_type_emits_no_zone_label(self) -> None:
        steps = [{"type": "interval", "duration_sec": 300, "target_type": "open", "zone": 4}]
        assert generate_description(steps) == "5m"

    def test_open_target_type_with_no_zone_emits_no_zone_label(self) -> None:
        steps = [{"type": "interval", "duration_sec": 600, "target_type": "open"}]
        assert generate_description(steps) == "10m"

    def test_pace_zone_target_type_still_emits_zone_label(self) -> None:
        steps = [{"type": "interval", "duration_sec": 600, "target_type": "pace_zone", "zone": 3}]
        assert generate_description(steps) == "10m@Z3"

    def test_hr_zone_target_type_still_emits_hr_suffix(self) -> None:
        steps = [{"type": "interval", "duration_sec": 600, "target_type": "hr_zone", "zone": 2}]
        assert generate_description(steps) == "10m@Z2(HR)"

    def test_open_step_inside_repeat_group_emits_no_zone_label(self) -> None:
        steps = [
            {
                "type": "repeat",
                "repeat_count": 6,
                "steps": [
                    {"type": "interval", "duration_sec": 60, "target_type": "open", "zone": 5},
                    {"type": "recovery", "duration_sec": 90, "target_type": "open"},
                ],
            }
        ]
        assert generate_description(steps) == "6x (1m + 2m)"


class TestGenerateDescriptionFromSteps:
    def test_open_step_via_json_round_trip(self) -> None:
        steps = [{"type": "warmup", "duration_sec": 600, "target_type": "open", "zone": 1}]
        result = generate_description_from_steps(json.dumps(steps))
        assert result == "10m"

    def test_none_input_returns_none(self) -> None:
        assert generate_description_from_steps(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert generate_description_from_steps("") is None

    def test_invalid_json_returns_none(self) -> None:
        assert generate_description_from_steps("not json") is None
