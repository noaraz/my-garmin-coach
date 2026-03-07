"""
try_it.py — interactive demo of GarminCoach core logic.

Run with:
    docker compose exec backend python scripts/try_it.py

Or customise with your own values:
    docker compose exec backend python scripts/try_it.py --lthr 165 --threshold-pace 4:45 --max-hr 185
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/app")

from src.garmin.formatter import format_workout
from src.workout_resolver.estimator import estimate_distance, estimate_duration
from src.workout_resolver.models import WorkoutStep
from src.workout_resolver.resolver import resolve_workout
from src.zone_engine.hr_zones import HRZoneCalculator
from src.zone_engine.models import ZoneConfig
from src.zone_engine.pace_zones import PaceZoneCalculator, format_pace

# ── ANSI colours ──────────────────────────────────────────────────────────────
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
DIM = "\033[2m"

ZONE_COLOURS = ["\033[34m", "\033[32m", "\033[33m", "\033[35m", "\033[31m"]


def header(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 60}{RESET}")


def parse_pace(s: str) -> float:
    """Convert "M:SS" string to seconds per km."""
    parts = s.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"Pace must be M:SS format, got {s!r}")
    return int(parts[0]) * 60 + int(parts[1])


def print_zones(zone_set: object, unit: str) -> None:
    for zone in zone_set.zones:  # type: ignore[attr-defined]
        colour = ZONE_COLOURS[zone.zone_number - 1]
        if unit == "bpm":
            lo = f"{zone.lower:.0f}"
            hi = f"{zone.upper:.0f}"
            fmt = f"{lo}–{hi} bpm"
        else:
            lo = format_pace(zone.lower)
            hi = format_pace(zone.upper)
            fmt = f"{lo}–{hi} /km  {DIM}({zone.lower:.0f}–{zone.upper:.0f} s/km){RESET}"
        print(f"  {colour}{BOLD}Z{zone.zone_number}{RESET} {zone.name:<12} {fmt}")


def build_sample_workout(hr_zone_set: object, pace_zone_set: object) -> list[WorkoutStep]:
    """Build a classic interval session: warmup + 5×(1 km @ Z4 + recovery Z1) + cooldown."""
    # Build zone lookup dicts: {zone_number: (lower, upper)}
    hr_zones = {z.zone_number: (z.lower, z.upper) for z in hr_zone_set.zones}  # type: ignore[attr-defined]
    pace_zones = {z.zone_number: (z.lower, z.upper) for z in pace_zone_set.zones}  # type: ignore[attr-defined]

    steps = [
        WorkoutStep(
            order=1, type="warmup",
            duration_type="time", duration_value=600, duration_unit="seconds",
            target_type="hr_zone", target_zone=2,
        ),
        WorkoutStep(
            order=2, type="repeat", repeat_count=5,
            duration_type="time",  # required but unused for repeat
            target_type="open",
            steps=[
                WorkoutStep(
                    order=1, type="active",
                    duration_type="distance", duration_value=1000, duration_unit="meters",
                    target_type="pace_zone", target_zone=4,
                ),
                WorkoutStep(
                    order=2, type="recovery",
                    duration_type="time", duration_value=90, duration_unit="seconds",
                    target_type="hr_zone", target_zone=1,
                ),
            ],
        ),
        WorkoutStep(
            order=3, type="cooldown",
            duration_type="time", duration_value=600, duration_unit="seconds",
            target_type="hr_zone", target_zone=2,
        ),
    ]

    resolved = resolve_workout(steps, hr_zones=hr_zones, pace_zones=pace_zones)
    return resolved, hr_zones, pace_zones


def main() -> None:
    parser = argparse.ArgumentParser(description="GarminCoach core logic demo")
    parser.add_argument("--lthr", type=float, default=170,
                        help="Lactate threshold HR in bpm (default: 170)")
    parser.add_argument("--max-hr", type=float, default=190,
                        help="Max HR in bpm (default: 190)")
    parser.add_argument("--resting-hr", type=float, default=48,
                        help="Resting HR in bpm (default: 48)")
    parser.add_argument("--threshold-pace", type=parse_pace, default="4:30",
                        metavar="M:SS",
                        help="Threshold pace per km (default: 4:30)")
    args = parser.parse_args()

    # ── 1. HR Zones ───────────────────────────────────────────────────────────
    header("HR Zones  (Coggan method, LTHR-based)")
    hr_config = ZoneConfig(threshold=args.lthr, method="coggan")
    hr_zones = HRZoneCalculator(hr_config).calculate()
    print(f"  LTHR: {args.lthr:.0f} bpm\n")
    print_zones(hr_zones, "bpm")

    # ── 2. Pace Zones ─────────────────────────────────────────────────────────
    header("Pace Zones  (Daniels % of threshold)")
    pace_config = ZoneConfig(threshold=args.threshold_pace, method="pct_threshold")
    pace_zones = PaceZoneCalculator(pace_config).calculate()
    print(f"  Threshold pace: {format_pace(args.threshold_pace)}/km\n")
    print_zones(pace_zones, "pace")

    # ── 3. Workout resolution ─────────────────────────────────────────────────
    header("Sample Workout: 5×1 km Intervals")
    print("  Warmup 10 min @ HR Z2  →  5× (1 km @ Pace Z4 + 90s recovery @ HR Z1)  →  Cooldown 10 min @ HR Z2\n")

    hr_dict = {z.zone_number: (z.lower, z.upper) for z in hr_zones.zones}
    pace_dict = {z.zone_number: (z.lower, z.upper) for z in pace_zones.zones}

    steps = [
        WorkoutStep(
            order=1, type="warmup",
            duration_type="time", duration_value=600, duration_unit="seconds",
            target_type="hr_zone", target_zone=2,
        ),
        WorkoutStep(
            order=2, type="repeat", repeat_count=5,
            duration_type="time",
            target_type="open",
            steps=[
                WorkoutStep(
                    order=1, type="active",
                    duration_type="distance", duration_value=1000, duration_unit="meters",
                    target_type="pace_zone", target_zone=4,
                ),
                WorkoutStep(
                    order=2, type="recovery",
                    duration_type="time", duration_value=90, duration_unit="seconds",
                    target_type="hr_zone", target_zone=1,
                ),
            ],
        ),
        WorkoutStep(
            order=3, type="cooldown",
            duration_type="time", duration_value=600, duration_unit="seconds",
            target_type="hr_zone", target_zone=2,
        ),
    ]

    resolved = resolve_workout(steps, hr_zones=hr_dict, pace_zones=pace_dict)

    warmup = resolved[0]
    repeat = resolved[1]
    interval = repeat.steps[0]
    recovery = repeat.steps[1]
    cooldown = resolved[2]

    z2_lo, z2_hi = warmup.target_low, warmup.target_high
    int_lo, int_hi = interval.target_low, interval.target_high
    rec_lo, rec_hi = recovery.target_low, recovery.target_high

    print(f"  {BOLD}Warmup{RESET}    10 min   HR {z2_lo:.0f}–{z2_hi:.0f} bpm")
    print(f"  {BOLD}5× Interval{RESET}")
    print(f"    Interval  1 km     Pace {format_pace(int_lo)}–{format_pace(int_hi)}/km  "
          f"{DIM}({int_lo:.0f}–{int_hi:.0f} s/km){RESET}")
    print(f"    Recovery  90 s     HR {rec_lo:.0f}–{rec_hi:.0f} bpm")
    print(f"  {BOLD}Cooldown{RESET}  10 min   HR {z2_lo:.0f}–{z2_hi:.0f} bpm")

    # ── 4. Garmin JSON ────────────────────────────────────────────────────────
    header("Garmin Connect JSON  (what gets pushed to your watch)")

    garmin_steps = [
        {"step_type": "warmup", "end_condition": "time", "end_condition_value": 600,
         "target_type": "hr_zone", "target_value_one": z2_lo, "target_value_two": z2_hi},
        {"step_type": "repeat", "repeat_count": 5, "steps": [
            {"step_type": "active", "end_condition": "distance", "end_condition_value": 1000,
             "target_type": "pace_zone", "target_value_one": int_lo, "target_value_two": int_hi},
            {"step_type": "recovery", "end_condition": "time", "end_condition_value": 90,
             "target_type": "hr_zone", "target_value_one": rec_lo, "target_value_two": rec_hi},
        ]},
        {"step_type": "cooldown", "end_condition": "time", "end_condition_value": 600,
         "target_type": "hr_zone", "target_value_one": z2_lo, "target_value_two": z2_hi},
    ]

    garmin_json = format_workout("5×1km Intervals", garmin_steps)
    print(json.dumps(garmin_json, indent=2))

    print(f"\n{GREEN}{BOLD}All systems go.{RESET} "
          f"Once Garmin sync is implemented, the above JSON gets pushed directly to Garmin Connect.\n")


if __name__ == "__main__":
    main()
