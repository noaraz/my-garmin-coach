from __future__ import annotations

from datetime import date, datetime, timezone
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
    # Auth / per-user fields
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    # Garmin token storage (Fernet encrypted)
    garmin_oauth_token_encrypted: Optional[str] = Field(default=None)
    garmin_connected: bool = Field(default=False)
    # Garmin credential storage for auto-reconnect (Fernet encrypted)
    garmin_credential_encrypted: Optional[str] = Field(default=None)
    garmin_credential_stored_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class HRZone(SQLModel, table=True):
    """HR zone linked to an athlete profile."""

    __tablename__ = "hrzone"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="athleteprofile.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
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
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
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
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    name: str
    description: Optional[str] = Field(default=None)
    sport_type: str = Field(default="running")
    estimated_duration_sec: Optional[float] = Field(default=None)
    estimated_distance_m: Optional[float] = Field(default=None)
    tags: Optional[str] = Field(default=None)  # JSON string
    steps: Optional[str] = Field(default=None)  # JSON string of WorkoutStep list
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduledWorkout(SQLModel, table=True):
    """A workout scheduled on a specific date."""

    __tablename__ = "scheduledworkout"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    date: date
    workout_template_id: Optional[int] = Field(
        default=None, foreign_key="workouttemplate.id"
    )
    resolved_steps: Optional[str] = Field(default=None)  # JSON string
    garmin_workout_id: Optional[str] = Field(default=None)
    sync_status: str = Field(default="pending")  # pending | synced | modified | failed
    completed: bool = Field(default=False)
    matched_activity_id: Optional[int] = Field(
        default=None, foreign_key="garminactivity.id"
    )
    training_plan_id: Optional[int] = Field(default=None, foreign_key="trainingplan.id")
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TrainingPlan(SQLModel, table=True):
    """A multi-week training plan (draft → active → superseded)."""

    __tablename__ = "trainingplan"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    name: str
    source: str  # "csv" | "chat"
    status: str = "draft"  # "draft" | "active" | "superseded"
    parsed_workouts: Optional[str] = Field(default=None)  # JSON array of ParsedWorkout
    start_date: date
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class PlanCoachMessage(SQLModel, table=True):
    """A single message in the Plan Coach chat thread (one global thread per user)."""

    __tablename__ = "plancoachMessage"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class GarminActivity(SQLModel, table=True):
    """A running activity fetched from Garmin Connect."""

    __tablename__ = "garminactivity"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    garmin_activity_id: str = Field(unique=True)
    activity_type: str
    name: str
    start_time: datetime
    date: date
    duration_sec: float
    distance_m: float
    avg_hr: Optional[float] = Field(default=None)
    max_hr: Optional[float] = Field(default=None)
    avg_pace_sec_per_km: Optional[float] = Field(default=None)
    calories: Optional[int] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
