from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.api.schemas import WorkoutTemplateCreate, WorkoutTemplateRead, WorkoutTemplateUpdate
from src.services.workout_service import (
    create_template,
    delete_template,
    get_template,
    list_templates,
    update_template,
)

router = APIRouter(prefix="/api/v1/workouts", tags=["workouts"])


@router.post("", response_model=WorkoutTemplateRead, status_code=201)
async def post_workout(
    body: WorkoutTemplateCreate,
    session: AsyncSession = Depends(get_session),
) -> WorkoutTemplateRead:
    """Create a new workout template."""
    template = await create_template(session, body.model_dump())
    return WorkoutTemplateRead.model_validate(template)


@router.get("", response_model=list[WorkoutTemplateRead])
async def list_workouts(
    session: AsyncSession = Depends(get_session),
) -> list[WorkoutTemplateRead]:
    """List all workout templates."""
    templates = await list_templates(session)
    return [WorkoutTemplateRead.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=WorkoutTemplateRead)
async def get_workout(
    template_id: int,
    session: AsyncSession = Depends(get_session),
) -> WorkoutTemplateRead:
    """Get a single workout template by id."""
    template = await get_template(session, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"WorkoutTemplate {template_id} not found")
    return WorkoutTemplateRead.model_validate(template)


@router.put("/{template_id}", response_model=WorkoutTemplateRead)
async def put_workout(
    template_id: int,
    body: WorkoutTemplateUpdate,
    session: AsyncSession = Depends(get_session),
) -> WorkoutTemplateRead:
    """Update a workout template by id."""
    try:
        template = await update_template(session, template_id, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return WorkoutTemplateRead.model_validate(template)


@router.delete("/{template_id}", status_code=204)
async def delete_workout(
    template_id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a workout template by id."""
    try:
        await delete_template(session, template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(status_code=204)
