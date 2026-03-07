from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

StepType = Literal["warmup", "active", "recovery", "rest", "cooldown", "repeat"]
DurationType = Literal["time", "distance", "lap_button"]
DurationUnit = Literal["seconds", "meters"]
TargetType = Literal["hr_zone", "pace_zone", "hr_range", "pace_range", "open"]


class WorkoutStep(BaseModel):
    """A single step in a workout, potentially with zone-referenced targets."""

    order: int
    type: StepType
    duration_type: DurationType
    duration_value: float | None = None
    duration_unit: DurationUnit | None = None
    target_type: TargetType
    target_zone: int | None = None
    target_low: float | None = None
    target_high: float | None = None
    notes: str | None = None
    repeat_count: int | None = None
    steps: list[WorkoutStep] = []

    model_config = {"frozen": False}


# Allow self-referential model
WorkoutStep.model_rebuild()


class ResolvedStep(BaseModel):
    """A workout step with absolute target values populated from zone lookup."""

    order: int
    type: StepType
    duration_type: DurationType
    duration_value: float | None = None
    duration_unit: DurationUnit | None = None
    target_type: TargetType
    target_zone: int | None = None
    target_low: float | None = None
    target_high: float | None = None
    notes: str | None = None
    repeat_count: int | None = None
    steps: list[ResolvedStep] = []

    model_config = {"frozen": False}


# Allow self-referential model
ResolvedStep.model_rebuild()
