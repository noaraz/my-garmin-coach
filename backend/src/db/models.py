from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AthleteProfile(SQLModel, table=True):
    """Singleton athlete profile (id=1)."""

    __tablename__ = "athleteprofile"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="Athlete")
    max_hr: Optional[int] = Field(default=None)
    resting_hr: Optional[int] = Field(default=None)
    lthr: Optional[int] = Field(default=None)
    threshold_pace: Optional[float] = Field(default=None)  # sec/km
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class HRZone(SQLModel, table=True):
    """HR zone linked to an athlete profile."""

    __tablename__ = "hrzone"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="athleteprofile.id")
    zone_number: int  # 1–5
    name: str
    lower_bpm: float
    upper_bpm: float
    calculation_method: str = Field(default="coggan")
    pct_lower: float
    pct_upper: float


class PaceZone(SQLModel, table=True):
    """Pace zone linked to an athlete profile."""

    __tablename__ = "pacezone"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="athleteprofile.id")
    zone_number: int  # 1–5
    name: str
    lower_pace: float  # sec/km (slower boundary)
    upper_pace: float  # sec/km (faster boundary)
    calculation_method: str = Field(default="pct_threshold")
    pct_lower: float
    pct_upper: float


class WorkoutTemplate(SQLModel, table=True):
    """A reusable workout template with zone-referenced steps."""

    __tablename__ = "workouttemplate"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = Field(default=None)
    sport_type: str = Field(default="running")
    estimated_duration_sec: Optional[float] = Field(default=None)
    estimated_distance_m: Optional[float] = Field(default=None)
    tags: Optional[str] = Field(default=None)    # JSON string
    steps: Optional[str] = Field(default=None)   # JSON string of WorkoutStep list
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduledWorkout(SQLModel, table=True):
    """A workout scheduled on a specific date."""

    __tablename__ = "scheduledworkout"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: date
    workout_template_id: Optional[int] = Field(
        default=None, foreign_key="workouttemplate.id"
    )
    resolved_steps: Optional[str] = Field(default=None)  # JSON string
    garmin_workout_id: Optional[str] = Field(default=None)
    sync_status: str = Field(default="pending")  # pending | synced | modified | failed
    completed: bool = Field(default=False)
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
