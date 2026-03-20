"""Plans router — validate/commit/delete training plans."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.services.plan_import_service import (
    CommitResult,
    ValidateResult,
    commit_plan,
    delete_plan,
    get_active_plan,
    validate_plan,
)

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
) -> CommitResult:
    """Commit a draft plan: create WorkoutTemplates + ScheduledWorkouts, set active."""
    try:
        return await commit_plan(session, user_id=current_user.id, plan_id=plan_id)  # type: ignore[arg-type]
    except ValueError as exc:
        msg = str(exc)
        if "does not belong to" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=404, detail=msg) from exc


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
    return ActivePlanResponse(
        plan_id=plan.id,  # type: ignore[arg-type]
        name=plan.name,
        source=plan.source,
        status=plan.status,
        start_date=plan.start_date.isoformat(),
    )


@router.delete("/{plan_id}", status_code=204)
async def delete_plan_endpoint(
    plan_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete a plan and all its ScheduledWorkouts. WorkoutTemplates are kept."""
    try:
        await delete_plan(session, user_id=current_user.id, plan_id=plan_id)  # type: ignore[arg-type]
    except ValueError as exc:
        msg = str(exc)
        if "does not belong to" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=404, detail=msg) from exc
    return Response(status_code=204)
