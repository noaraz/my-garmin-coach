"""Plan import service for the Plan Coach feature.

Handles the validate → commit pipeline:
- validate_plan: parse steps, compute diff vs active plan, store draft
- commit_plan: replace active plan, create WorkoutTemplates + ScheduledWorkouts
- delete_plan: remove plan and its ScheduledWorkouts
- get_active_plan: return the current active TrainingPlan for a user
"""
from __future__ import annotations

import json
import logging
from datetime import date as date_type, datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import delete, update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import ScheduledWorkout, TrainingPlan, WorkoutTemplate
from src.services.plan_step_parser import StepParseError, parse_steps_spec
from src.services.workout_description import generate_description_from_steps

logger = logging.getLogger(__name__)


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
    template_status: Literal["new", "existing"] = "new"


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
    past_locked: list[WorkoutDiff] = []


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


def _normalize_steps(steps_str: str | None) -> str:
    """Normalize steps JSON for dedup key comparison.

    Parses and re-serializes with sort_keys=True to ensure byte-identical
    comparison regardless of the original serialization path.
    """
    if not steps_str:
        return ""
    try:
        return json.dumps(json.loads(steps_str), sort_keys=True)
    except (ValueError, TypeError):
        return steps_str


def _compute_diff(
    incoming: list[ParsedWorkout],
    active_parsed: list[dict],
    completed_dates: set[str] | None = None,
    reference_date: date_type | None = None,
) -> DiffResult:
    """Compute added/removed/changed/unchanged/completed_locked/past_locked vs the active plan.

    Priority: completed_locked takes precedence over past_locked — a workout that is both
    past-dated and has a matched activity is classified as completed_locked.

    reference_date: the cutoff for "past" (defaults to UTC today). Inject in tests for
    deterministic results.
    """
    completed_dates = completed_dates or set()
    active_by_date = {w["date"]: w for w in active_parsed}
    incoming_by_date = {w.date: w for w in incoming}
    today = reference_date or datetime.now(timezone.utc).date()

    added: list[WorkoutDiff] = []
    removed: list[WorkoutDiff] = []
    changed: list[WorkoutDiff] = []
    unchanged: list[WorkoutDiff] = []
    completed_locked: list[WorkoutDiff] = []
    past_locked: list[WorkoutDiff] = []

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
            if date_type.fromisoformat(date_str) < today:
                past_locked.append(WorkoutDiff(date=date_str, name=active.get("name", "")))
            else:
                removed.append(WorkoutDiff(date=date_str, name=active.get("name", "")))

    return DiffResult(
        added=added,
        removed=removed,
        changed=changed,
        unchanged=unchanged,
        completed_locked=completed_locked,
        past_locked=past_locked,
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

    # Annotate valid rows with template_status (new vs existing in library).
    # Only runs when all rows are valid — zip(valid_rows, parsed_list) is safe.
    if parsed_list:
        tmpl_result = await session.exec(
            select(WorkoutTemplate).where(WorkoutTemplate.user_id == user_id)
        )
        existing_keys: set[tuple[str, str]] = {
            (t.name, _normalize_steps(t.steps)) for t in tmpl_result.all()
        }
        valid_rows = [r for r in rows if r.valid]
        for vrow, pw in zip(valid_rows, parsed_list):
            steps_json = json.dumps(pw.steps, sort_keys=True) if pw.steps else None
            incoming_key = (pw.name, steps_json or "")
            if incoming_key in existing_keys:
                vrow.template_status = "existing"

    # Compute diff against active plan if one exists
    diff: DiffResult | None = None
    active = await get_active_plan(session, user_id)
    if active and active.parsed_workouts:
        active_parsed = json.loads(active.parsed_workouts)
        # Fetch completed dates — single query, date column only (no full ORM objects)
        completed_result = await session.exec(
            select(ScheduledWorkout.date).where(
                ScheduledWorkout.training_plan_id == active.id,
                ScheduledWorkout.matched_activity_id.isnot(None),  # type: ignore[union-attr]
            )
        )
        completed_dates = {str(row) for row in completed_result.all()}
        diff = _compute_diff(parsed_list, active_parsed, completed_dates)

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
    garmin: Any | None = None,
    reference_date: date_type | None = None,
) -> CommitResult:
    """Commit a draft plan with smart merge.

    - Unchanged workouts (same date, name, steps_spec): kept as-is.
    - Completed workouts (matched_activity_id IS NOT NULL): never touched.
    - Past workouts (date < today, not in incoming, not completed): re-associated to new plan.
    - Changed workouts: old SW deleted (Garmin cleanup), new SW created.
    - Added workouts: new SW created.
    - Removed workouts (date >= today, not in incoming, not completed): old SW deleted.

    reference_date: the cutoff for "past" (defaults to UTC today). Inject in tests for
    deterministic results. Note: validate and commit each compute "today" independently —
    a workout dated exactly today at validate time may be classified differently if commit
    runs after midnight (it will be preserved rather than deleted, which is safe).
    """

    plan = await session.get(TrainingPlan, plan_id)
    if plan is None or plan.status != "draft":
        raise ValueError(f"TrainingPlan {plan_id} not found or not a draft")
    if plan.user_id != user_id:
        raise ValueError(f"TrainingPlan {plan_id} does not belong to user {user_id}")

    parsed_workouts: list[dict] = json.loads(plan.parsed_workouts or "[]")

    active = await get_active_plan(session, user_id)

    # -----------------------------------------------------------------------
    # Smart merge setup: batch-load existing SWs and their templates
    # -----------------------------------------------------------------------
    sw_by_date: dict[str, ScheduledWorkout] = {}
    active_steps_by_date: dict[str, str] = {}
    active_name_by_date: dict[str, str] = {}
    completed_dates: set[str] = set()

    if active is not None:
        # Batch 1: all scheduled workouts for active plan — single query
        sw_result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.training_plan_id == active.id
            )
        )
        all_sws = sw_result.all()
        sw_by_date = {str(sw.date): sw for sw in all_sws}

        # Completed dates: only the date column — no full ORM objects
        completed_result = await session.exec(
            select(ScheduledWorkout.date).where(
                ScheduledWorkout.training_plan_id == active.id,
                ScheduledWorkout.matched_activity_id.isnot(None),  # type: ignore[union-attr]
            )
        )
        completed_dates = {str(row) for row in completed_result.all()}

        # Parse the active plan's steps_spec for comparison
        if active.parsed_workouts:
            for pw_dict in json.loads(active.parsed_workouts):
                d = pw_dict.get("date", "")
                active_steps_by_date[d] = pw_dict.get("steps_spec", "")
                active_name_by_date[d] = pw_dict.get("name", "")

        active.status = "superseded"
        active.updated_at = _now()
        session.add(active)

    # -----------------------------------------------------------------------
    # Classify each incoming workout
    # -----------------------------------------------------------------------
    ids_to_delete: list[int] = []
    kept_sw_ids: list[int] = []
    garmin_ids_to_delete: list[str] = []
    sws_to_create: list[dict] = []
    incoming_dates: set[str] = set()

    for pw_dict in parsed_workouts:
        pw = ParsedWorkout(**pw_dict)
        incoming_dates.add(pw.date)
        existing_sw = sw_by_date.get(pw.date)

        if existing_sw is not None:
            # Completed — never touch content, but re-associate to new plan
            if pw.date in completed_dates:
                kept_sw_ids.append(existing_sw.id)  # type: ignore[arg-type]
                continue

            # Compare using active plan's stored steps_spec (source of truth)
            same_name = active_name_by_date.get(pw.date) == pw.name
            same_steps = active_steps_by_date.get(pw.date) == pw.steps_spec
            if same_name and same_steps:
                kept_sw_ids.append(existing_sw.id)  # type: ignore[arg-type]
                continue  # unchanged — keep existing row, re-associate below

            # Changed: queue old SW for deletion, queue new SW for creation
            ids_to_delete.append(existing_sw.id)  # type: ignore[arg-type]
            if existing_sw.garmin_workout_id:
                garmin_ids_to_delete.append(existing_sw.garmin_workout_id)

        sws_to_create.append(pw_dict)

    # Removed: in active plan, not in incoming, not completed
    # Past workouts (date < today) are re-associated instead of deleted
    today = reference_date or datetime.now(timezone.utc).date()
    for date_str, sw in sw_by_date.items():
        if date_str not in incoming_dates and date_str not in completed_dates:
            if date_type.fromisoformat(date_str) < today:
                kept_sw_ids.append(sw.id)  # type: ignore[arg-type]
            else:
                ids_to_delete.append(sw.id)  # type: ignore[arg-type]
                if sw.garmin_workout_id:
                    garmin_ids_to_delete.append(sw.garmin_workout_id)

    # -----------------------------------------------------------------------
    # Garmin cleanup (must happen before DB delete — one API call per workout)
    # -----------------------------------------------------------------------
    if garmin is not None:
        for garmin_id in garmin_ids_to_delete:
            try:
                garmin.delete_workout(garmin_id)
                logger.info("Smart merge: deleted Garmin workout %s", garmin_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not delete Garmin workout %s: %s", garmin_id, exc)

    # -----------------------------------------------------------------------
    # Bulk delete — single statement
    # -----------------------------------------------------------------------
    if ids_to_delete:
        await session.execute(
            delete(ScheduledWorkout).where(ScheduledWorkout.id.in_(ids_to_delete))
        )

    # Re-associate kept SWs (unchanged + completed_locked + past_locked) to the new plan
    if kept_sw_ids:
        await session.execute(
            update(ScheduledWorkout)
            .where(ScheduledWorkout.id.in_(kept_sw_ids))
            .values(training_plan_id=plan_id)
        )

    # -----------------------------------------------------------------------
    # Garmin dedup: fetch existing Garmin workouts to pre-link new SWs
    # -----------------------------------------------------------------------
    garmin_workout_by_name: dict[str, str] = {}  # lowercase name → garmin_workout_id
    if garmin is not None:
        try:
            raw_garmin_workouts: list[dict[str, Any]] = garmin.get_workouts()
            for gw in raw_garmin_workouts:
                gw_name = gw.get("workoutName", "")
                if isinstance(gw_name, str) and gw_name:
                    garmin_workout_by_name.setdefault(gw_name.lower(), str(gw["workoutId"]))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch Garmin workouts for dedup: %s", exc)

    # -----------------------------------------------------------------------
    # Batch-load/create templates; batch-add new SWs
    # -----------------------------------------------------------------------
    templates_result = await session.exec(
        select(WorkoutTemplate).where(WorkoutTemplate.user_id == user_id)
    )
    existing_templates: dict[tuple[str, str], WorkoutTemplate] = {
        (t.name, _normalize_steps(t.steps)): t for t in templates_result.all()
    }

    now = _now()
    new_sw_count = 0

    for pw_dict in sws_to_create:
        pw = ParsedWorkout(**pw_dict)
        try:
            workout_date = date_type.fromisoformat(pw.date)
        except ValueError:
            continue

        steps_json = json.dumps(pw.steps, sort_keys=True) if pw.steps else None
        dedup_key = (pw.name, steps_json or "")
        if dedup_key in existing_templates:
            template = existing_templates[dedup_key]
        else:
            template = WorkoutTemplate(
                user_id=user_id,
                name=pw.name,
                description=generate_description_from_steps(steps_json),
                sport_type=pw.sport_type,
                steps=steps_json,
                created_at=now,
                updated_at=now,
            )
            session.add(template)
            await session.flush()
            existing_templates[dedup_key] = template

        # Pre-link to existing Garmin workout if name matches (prevents
        # duplicate on next sync — the delete+push cycle will replace it).
        matched_garmin_id = garmin_workout_by_name.get(pw.name.lower())
        sw = ScheduledWorkout(
            user_id=user_id,
            date=workout_date,
            workout_template_id=template.id,
            training_plan_id=plan_id,
            notes=pw.description or None,
            sync_status="modified" if matched_garmin_id else "pending",
            garmin_workout_id=matched_garmin_id,
            created_at=now,
            updated_at=now,
        )
        session.add(sw)
        new_sw_count += 1

    # Total = kept (unchanged + completed_locked + past_locked) + newly created
    kept_count = len(sw_by_date) - len(ids_to_delete)
    total_workout_count = max(0, kept_count) + new_sw_count

    plan.status = "active"
    plan.updated_at = now
    session.add(plan)
    await session.commit()

    return CommitResult(
        plan_id=plan.id,  # type: ignore[arg-type]
        name=plan.name,
        workout_count=total_workout_count,
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
