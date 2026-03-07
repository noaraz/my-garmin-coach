from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel


# ── Profile schemas ────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    max_hr: Optional[int] = None
    resting_hr: Optional[int] = None
    lthr: Optional[int] = None
    threshold_pace: Optional[float] = None


class ProfileRead(BaseModel):
    id: int
    name: str
    max_hr: Optional[int] = None
    resting_hr: Optional[int] = None
    lthr: Optional[int] = None
    threshold_pace: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── HR Zone schemas ────────────────────────────────────────────────────────────

class HRZoneRead(BaseModel):
    id: int
    profile_id: int
    zone_number: int
    name: str
    lower_bpm: float
    upper_bpm: float
    calculation_method: str
    pct_lower: float
    pct_upper: float

    model_config = {"from_attributes": True}


class HRZoneCreate(BaseModel):
    zone_number: int
    name: str
    lower_bpm: float
    upper_bpm: float
    calculation_method: str = "custom"
    pct_lower: float
    pct_upper: float


# ── Pace Zone schemas ──────────────────────────────────────────────────────────

class PaceZoneRead(BaseModel):
    id: int
    profile_id: int
    zone_number: int
    name: str
    lower_pace: float
    upper_pace: float
    calculation_method: str
    pct_lower: float
    pct_upper: float

    model_config = {"from_attributes": True}


# ── Workout Template schemas ───────────────────────────────────────────────────

class WorkoutTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sport_type: str = "running"
    tags: Optional[list[str]] = None
    steps: Optional[list[Any]] = None


class WorkoutTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sport_type: Optional[str] = None
    tags: Optional[list[str]] = None
    steps: Optional[list[Any]] = None


class WorkoutTemplateRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    sport_type: str
    estimated_duration_sec: Optional[float] = None
    estimated_distance_m: Optional[float] = None
    tags: Optional[str] = None
    steps: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Calendar schemas ───────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    template_id: int
    date: date


class RescheduleUpdate(BaseModel):
    date: date


class ScheduledWorkoutRead(BaseModel):
    id: int
    date: date
    workout_template_id: Optional[int] = None
    resolved_steps: Optional[str] = None
    garmin_workout_id: Optional[str] = None
    sync_status: str
    completed: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
