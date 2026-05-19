"""Plans router — validate/commit/delete training plans + Plan Coach chat."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.models import PlanCoachMessage, ScheduledWorkout
from src.garmin.token_persistence import persist_refreshed_token
from src.services.plan_import_service import (
    CommitResult,
    ValidateResult,
    commit_plan,
    delete_plan,
    get_active_plan,
    validate_plan,
)
from src.services.plan_coach_service import (
    get_chat_history,
    send_chat_message,
)
from src.services.profile_service import get_or_create_profile
from src.services.sync_orchestrator import SyncOrchestrator
from src.services.zone_service import get_hr_zones, get_pace_zones
from src.api.routers.sync import get_optional_garmin_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/plans", tags=["plans"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class ValidateRequest(BaseModel):
    name: str = "My Training Plan"
    source: str = "csv"
    workouts: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ActivePlanResponse(BaseModel):
    plan_id: int
    name: str
    source: str
    status: str
    start_date: str
    workout_count: int | None = None


class ChatMessageRequest(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str

    @classmethod
    def from_orm(cls, msg: PlanCoachMessage) -> "ChatMessageResponse":
        return cls(
            id=msg.id,  # type: ignore[arg-type]
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/validate", response_model=ValidateResult)
async def post_validate(
    body: ValidateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ValidateResult:
    """Parse and validate a list of workout dicts; return draft plan_id + per-row results."""
    result = await validate_plan(
        session,
        user_id=current_user.id,  # type: ignore[arg-type]
        workouts=body.workouts,
        plan_name=body.name,
        source=body.source,
    )
    if result.plan_id == -1:
        # Validation errors — return 422
        raise HTTPException(
            status_code=422,
            detail={"rows": [r.model_dump() for r in result.rows]},
        )
    return result


@router.post("/{plan_id}/commit", response_model=CommitResult)
async def post_commit(
    plan_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    garmin: SyncOrchestrator | None = Depends(get_optional_garmin_sync_service),
) -> CommitResult:
    """Commit a draft plan using smart merge.

    Unchanged and completed workouts are preserved. Changed workouts trigger
    Garmin cleanup before replacement. All logic is in commit_plan.
    """
    try:
        result = await commit_plan(
            session,
            user_id=current_user.id,  # type: ignore[arg-type]
            plan_id=plan_id,
            garmin=garmin,
        )
    except ValueError as exc:
        msg = str(exc)
        if "does not belong to" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=404, detail=msg) from exc

    # Persist any OAuth2 token refresh that occurred during Garmin operations
    if garmin:
        await persist_refreshed_token(garmin, current_user.id, session)

    return result


@router.get("/active", response_model=ActivePlanResponse)
async def get_active(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    response: Response = Response(),
) -> ActivePlanResponse | Response:
    """Return the active training plan, or 204 if none exists."""
    plan = await get_active_plan(session, user_id=current_user.id)  # type: ignore[arg-type]
    if plan is None:
        return Response(status_code=204)
    count_result = await session.exec(
        select(func.count()).where(ScheduledWorkout.training_plan_id == plan.id)
    )
    workout_count = count_result.one()
    return ActivePlanResponse(
        plan_id=plan.id,  # type: ignore[arg-type]
        name=plan.name,
        source=plan.source,
        status=plan.status,
        start_date=plan.start_date.isoformat(),
        workout_count=workout_count,
    )


@router.delete("/{plan_id}", status_code=204)
async def delete_plan_endpoint(
    plan_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    garmin: SyncOrchestrator | None = Depends(get_optional_garmin_sync_service),
) -> Response:
    """Delete a plan and all its ScheduledWorkouts.

    Synced workouts that were never paired with a completed Garmin activity
    are also deleted from Garmin Connect. Paired workouts (activity data exists)
    are left on Garmin. WorkoutTemplates are kept locally.
    """
    # Fetch synced-but-unpaired workouts before the DB delete
    if garmin is not None:
        result = await session.exec(
            select(ScheduledWorkout).where(
                ScheduledWorkout.training_plan_id == plan_id,
                ScheduledWorkout.user_id == current_user.id,
                ScheduledWorkout.garmin_workout_id.isnot(None),  # type: ignore[union-attr]
                ScheduledWorkout.matched_activity_id.is_(None),  # type: ignore[union-attr]
            )
        )
        unsynced_workouts = result.all()
        for workout in unsynced_workouts:
            try:
                garmin.delete_workout(workout.garmin_workout_id)  # type: ignore[arg-type]
                logger.info("Deleted Garmin workout %s", workout.garmin_workout_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Could not delete Garmin workout %s: %s",
                    workout.garmin_workout_id,
                    exc,
                )

    try:
        await delete_plan(session, user_id=current_user.id, plan_id=plan_id)  # type: ignore[arg-type]
    except ValueError as exc:
        msg = str(exc)
        if "does not belong to" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=404, detail=msg) from exc

    # Persist any OAuth2 token refresh that occurred during Garmin deletes
    if garmin:
        await persist_refreshed_token(garmin, current_user.id, session)

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Chat endpoints (Phase 4)
# ---------------------------------------------------------------------------


@router.get("/chat/history", response_model=list[ChatMessageResponse])
async def get_history(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessageResponse]:
    """Return full chat history for the current user."""
    messages = await get_chat_history(session, user_id=current_user.id)  # type: ignore[arg-type]
    return [ChatMessageResponse.from_orm(m) for m in messages]


@router.post("/chat/message", response_model=ChatMessageResponse)
async def post_chat_message(
    body: ChatMessageRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    """Append user message, call Gemini Flash, return assistant reply."""
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Message content cannot be empty")

    profile = await get_or_create_profile(session, user_id=current_user.id)
    hr_zones = await get_hr_zones(session, profile_id=profile.id)  # type: ignore[arg-type]
    pace_zones = await get_pace_zones(session, profile_id=profile.id)  # type: ignore[arg-type]

    try:
        assistant_msg = await send_chat_message(
            session,
            user_id=current_user.id,  # type: ignore[arg-type]
            content=body.content,
            profile=profile,
            hr_zones=hr_zones,
            pace_zones=pace_zones,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatMessageResponse.from_orm(assistant_msg)
