"""Plan import service for the Plan Coach feature.

Handles the validate → commit pipeline:
- validate_plan: parse steps, compute diff vs active plan, store draft
- commit_plan: replace active plan, create WorkoutTemplates + ScheduledWorkouts
- delete_plan: remove plan and its ScheduledWorkouts
- get_active_plan: return the current active TrainingPlan for a user
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import ScheduledWorkout, TrainingPlan, WorkoutTemplate
from src.services.plan_step_parser import StepParseError, parse_steps_spec


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ParsedWorkout(BaseModel):
    date: str        # ISO format YYYY-MM-DD
    name: str
    description: str | None = None
    steps_spec: str
    sport_type: str = "running"
    steps: list[dict] | None = None   # populated after parsing


class ValidateRow(BaseModel):
    row: int
    date: str
    name: str
    steps_spec: str
    sport_type: str
    valid: bool
    error: str | None = None


class WorkoutDiff(BaseModel):
    date: str
    name: str
    old_name: str | None = None        # populated for "changed" only
    old_steps_spec: str | None = None  # populated for "changed" only
    new_steps_spec: str | None = None  # populated for "changed" only


class DiffResult(BaseModel):
    added: list[WorkoutDiff]
    removed: list[WorkoutDiff]
    changed: list[WorkoutDiff]
    unchanged: list[WorkoutDiff] = []
    completed_locked: list[WorkoutDiff] = []


class ValidateResult(BaseModel):
    plan_id: int
    rows: list[ValidateRow]
    diff: DiffResult | None = None


class CommitResult(BaseModel):
    plan_id: int
    name: str
    workout_count: int
    start_date: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _compute_diff(
    incoming: list[ParsedWorkout],
    active_parsed: list[dict],
    completed_dates: set[str] | None = None,
) -> DiffResult:
    """Compute added/removed/changed/unchanged/completed_locked vs the active plan."""
    completed_dates = completed_dates or set()
    active_by_date = {w["date"]: w for w in active_parsed}
    incoming_by_date = {w.date: w for w in incoming}

    added: list[WorkoutDiff] = []
    removed: list[WorkoutDiff] = []
    changed: list[WorkoutDiff] = []
    unchanged: list[WorkoutDiff] = []
    completed_locked: list[WorkoutDiff] = []

    for date_str, workout in incoming_by_date.items():
        if date_str in completed_dates:
            completed_locked.append(WorkoutDiff(date=date_str, name=workout.name))
        elif date_str not in active_by_date:
            added.append(WorkoutDiff(date=date_str, name=workout.name))
        else:
            active = active_by_date[date_str]
            same_name = active.get("name") == workout.name
            same_steps = active.get("steps_spec") == workout.steps_spec
            if same_name and same_steps:
                unchanged.append(WorkoutDiff(date=date_str, name=workout.name))
            else:
                changed.append(WorkoutDiff(
                    date=date_str,
                    name=workout.name,
                    old_name=active.get("name"),
                    old_steps_spec=active.get("steps_spec"),
                    new_steps_spec=workout.steps_spec,
                ))

    for date_str, active in active_by_date.items():
        if date_str not in incoming_by_date and date_str not in completed_dates:
            removed.append(WorkoutDiff(date=date_str, name=active.get("name", "")))

    return DiffResult(
        added=added,
        removed=removed,
        changed=changed,
        unchanged=unchanged,
        completed_locked=completed_locked,
    )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

async def get_active_plan(session: AsyncSession, user_id: int) -> TrainingPlan | None:
    """Return the current active TrainingPlan for the user, or None."""
    result = await session.exec(
        select(TrainingPlan).where(
            TrainingPlan.user_id == user_id,
            TrainingPlan.status == "active",
        )
    )
    return result.first()


async def _cleanup_stale_drafts(session: AsyncSession, user_id: int) -> None:
    """Delete all draft TrainingPlans older than 24h for this user.

    Does NOT commit — callers commit once after all mutations.
    """
    cutoff = _now() - timedelta(hours=24)
    await session.execute(
        delete(TrainingPlan).where(
            TrainingPlan.user_id == user_id,
            TrainingPlan.status == "draft",
            TrainingPlan.created_at < cutoff,
        )
    )


async def validate_plan(
    session: AsyncSession,
    user_id: int,
    workouts: list[dict[str, Any]],
    plan_name: str,
    source: str = "csv",
) -> ValidateResult:
    """Parse and validate a list of workout dicts.

    Steps:
    1. Cleanup stale drafts (>24h) for this user.
    2. Parse all steps_spec; collect row-level errors.
    3. If any parse errors: return 422 with rows but NO DB write (no plan_id).
       Callers should raise HTTPException(422) when plan_id is absent.
    4. If user has active plan: compute diff.
    5. Create TrainingPlan(status="draft"), store parsed_workouts.
    6. Return ValidateResult.

    Note: if there are validation errors, plan_id will be -1 (sentinel) and
    the caller must NOT call commit. The caller should surface row errors.
    """
    await _cleanup_stale_drafts(session, user_id)

    rows: list[ValidateRow] = []
    parsed_list: list[ParsedWorkout] = []
    all_valid = True

    for i, w in enumerate(workouts):
        date_str = str(w.get("date", "")).strip()
        name = str(w.get("name", "")).strip()
        steps_spec = str(w.get("steps_spec", "")).strip()
        sport_type = str(w.get("sport_type", "running")).strip() or "running"
        description = w.get("description")

        if not date_str or not name or not steps_spec:
            rows.append(ValidateRow(
                row=i + 1,
                date=date_str,
                name=name,
                steps_spec=steps_spec,
                sport_type=sport_type,
                valid=False,
                error="date, name, and steps_spec are required",
            ))
            all_valid = False
            continue

        try:
            parsed_steps = parse_steps_spec(steps_spec)
            pw = ParsedWorkout(
                date=date_str,
                name=name,
                description=description,
                steps_spec=steps_spec,
                sport_type=sport_type,
                steps=parsed_steps,
            )
            parsed_list.append(pw)
            rows.append(ValidateRow(
                row=i + 1,
                date=date_str,
                name=name,
                steps_spec=steps_spec,
                sport_type=sport_type,
                valid=True,
            ))
        except StepParseError as exc:
            rows.append(ValidateRow(
                row=i + 1,
                date=date_str,
                name=name,
                steps_spec=steps_spec,
                sport_type=sport_type,
                valid=False,
                error=str(exc),
            ))
            all_valid = False

    if not all_valid:
        # Sentinel — no DB write
        return ValidateResult(plan_id=-1, rows=rows, diff=None)

    # Compute diff against active plan if one exists
    diff: DiffResult | None = None
    active = await get_active_plan(session, user_id)
    if active and active.parsed_workouts:
        active_parsed = json.loads(active.parsed_workouts)
        diff = _compute_diff(parsed_list, active_parsed)

    # Determine start_date from the earliest workout date
    from datetime import date as date_type
    dates = []
    for pw in parsed_list:
        try:
            dates.append(date_type.fromisoformat(pw.date))
        except ValueError:
            pass
    start_date = min(dates) if dates else datetime.now(timezone.utc).date()

    # Serialise parsed workouts for storage
    parsed_workouts_json = json.dumps([pw.model_dump() for pw in parsed_list])

    plan = TrainingPlan(
        user_id=user_id,
        name=plan_name,
        source=source,
        status="draft",
        parsed_workouts=parsed_workouts_json,
        start_date=start_date,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    return ValidateResult(plan_id=plan.id, rows=rows, diff=diff)  # type: ignore[arg-type]


async def commit_plan(
    session: AsyncSession,
    user_id: int,
    plan_id: int,
) -> CommitResult:
    """Commit a draft plan: create WorkoutTemplates + ScheduledWorkouts, set active.

    Raises:
        ValueError: if plan not found, not a draft, or belongs to another user.
    """
    plan = await session.get(TrainingPlan, plan_id)
    if plan is None or plan.status != "draft":
        raise ValueError(f"TrainingPlan {plan_id} not found or not a draft")
    if plan.user_id != user_id:
        raise ValueError(f"TrainingPlan {plan_id} does not belong to user {user_id}")

    parsed_workouts: list[dict] = json.loads(plan.parsed_workouts or "[]")

    # Supersede existing active plan and delete its scheduled workouts
    active = await get_active_plan(session, user_id)
    if active is not None:
        await session.execute(
            delete(ScheduledWorkout).where(
                ScheduledWorkout.training_plan_id == active.id
            )
        )
        active.status = "superseded"
        active.updated_at = _now()
        session.add(active)

    # Build name → template map to reuse existing templates per unique name
    # Batch-load templates for this user
    templates_result = await session.exec(
        select(WorkoutTemplate).where(WorkoutTemplate.user_id == user_id)
    )
    existing_templates = {t.name: t for t in templates_result.all()}

    now = _now()
    workout_count = 0

    from datetime import date as date_type
    for pw_dict in parsed_workouts:
        pw = ParsedWorkout(**pw_dict)
        workout_date_str = pw.date

        try:
            workout_date = date_type.fromisoformat(workout_date_str)
        except ValueError:
            continue  # skip malformed dates (shouldn't happen after validate)

        # Reuse or create WorkoutTemplate
        if pw.name in existing_templates:
            template = existing_templates[pw.name]
        else:
            steps_json = json.dumps(pw.steps) if pw.steps else None
            template = WorkoutTemplate(
                user_id=user_id,
                name=pw.name,
                description=pw.description,
                sport_type=pw.sport_type,
                steps=steps_json,
                created_at=now,
                updated_at=now,
            )
            session.add(template)
            await session.flush()  # get template.id
            existing_templates[pw.name] = template

        sw = ScheduledWorkout(
            user_id=user_id,
            date=workout_date,
            workout_template_id=template.id,
            training_plan_id=plan_id,
            sync_status="pending",
            created_at=now,
            updated_at=now,
        )
        session.add(sw)
        workout_count += 1

    plan.status = "active"
    plan.updated_at = now
    session.add(plan)
    await session.commit()

    return CommitResult(
        plan_id=plan.id,  # type: ignore[arg-type]
        name=plan.name,
        workout_count=workout_count,
        start_date=plan.start_date.isoformat(),
    )


async def delete_plan(
    session: AsyncSession,
    user_id: int,
    plan_id: int,
) -> None:
    """Delete a plan and all its ScheduledWorkouts. WorkoutTemplates are kept.

    Raises:
        ValueError: if plan not found or belongs to another user.
    """
    plan = await session.get(TrainingPlan, plan_id)
    if plan is None:
        raise ValueError(f"TrainingPlan {plan_id} not found")
    if plan.user_id != user_id:
        raise ValueError(f"TrainingPlan {plan_id} does not belong to user {user_id}")

    await session.execute(
        delete(ScheduledWorkout).where(
            ScheduledWorkout.training_plan_id == plan_id
        )
    )
    await session.delete(plan)
    await session.commit()
