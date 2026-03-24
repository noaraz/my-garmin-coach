"""Pure utility: generate a short description string from workout steps JSON.

Mirrors frontend/src/utils/generateDescription.ts :: generateDescription().

Rule: description must ALWAYS be derived from steps. Never set them independently.
Whenever steps is written to a WorkoutTemplate, call generate_description_from_steps()
and store the result in description. See features/workout-builder/CLAUDE.md.
"""
from __future__ import annotations

import json


def _fmt_dur(step: dict) -> str:
    if step.get("duration_type") == "distance":
        # Accept both builder key (distance_m) and legacy CSV parser key (duration_distance_m)
        dist_m = step.get("distance_m") or step.get("duration_distance_m")
        if dist_m is not None:
            km = dist_m / 1000
            return f"{int(km)}K" if km == int(km) else f"{km:.1f}K"
    if step.get("duration_sec") is not None:
        m = round(step["duration_sec"] / 60)
        return f"{m}m"
    return "?"


def _zone_label(step: dict) -> str:
    zone = step.get("zone")
    if zone is not None:
        # HR zone gets a suffix; pace zone (or legacy CSV steps without target_type) just @ZN
        return f"@Z{zone}(HR)" if step.get("target_type") == "hr_zone" else f"@Z{zone}"
    defaults = {"warmup": "@Z1", "interval": "@Z4", "recovery": "@Z1", "cooldown": "@Z1"}
    return defaults.get(step.get("type", ""), "")


def _step_desc(step: dict) -> str:
    return f"{_fmt_dur(step)}{_zone_label(step)}"


def generate_description(steps: list[dict]) -> str:
    """Generate a short one-liner from a parsed steps list.

    Example: [warmup 10m Z1, run 25m Z2] → "10m@Z1, 25m@Z2"
    """
    parts = []
    for step in steps:
        if step.get("type") == "repeat":
            inner = " + ".join(_step_desc(s) for s in step.get("steps", []))
            parts.append(f"{step.get('repeat_count', 1)}x ({inner})")
        else:
            parts.append(_step_desc(step))
    return ", ".join(parts)


def generate_description_from_steps(steps_json: str | None) -> str | None:
    """Parse steps JSON and return a generated description, or None if steps is empty/invalid."""
    if not steps_json:
        return None
    try:
        steps = json.loads(steps_json)
        if not isinstance(steps, list) or not steps:
            return None
        return generate_description(steps)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
