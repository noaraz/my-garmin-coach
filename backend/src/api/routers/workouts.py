from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from src.api.dependencies import get_session
from src.api.schemas import WorkoutTemplateCreate, WorkoutTemplateRead, WorkoutTemplateUpdate
from src.services.workout_service import (
    create_template,
    delete_template,
    list_templates,
    update_template,
)

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


@router.post("", response_model=WorkoutTemplateRead, status_code=201)
def post_workout(
    body: WorkoutTemplateCreate,
    session: Session = Depends(get_session),
) -> WorkoutTemplateRead:
    """Create a new workout template."""
    template = create_template(session, body.model_dump())
    return WorkoutTemplateRead.model_validate(template)


@router.get("", response_model=list[WorkoutTemplateRead])
def list_workouts(
    session: Session = Depends(get_session),
) -> list[WorkoutTemplateRead]:
    """List all workout templates."""
    templates = list_templates(session)
    return [WorkoutTemplateRead.model_validate(t) for t in templates]


@router.put("/{template_id}", response_model=WorkoutTemplateRead)
def put_workout(
    template_id: int,
    body: WorkoutTemplateUpdate,
    session: Session = Depends(get_session),
) -> WorkoutTemplateRead:
    """Update a workout template by id."""
    try:
        template = update_template(session, template_id, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return WorkoutTemplateRead.model_validate(template)


@router.delete("/{template_id}", status_code=204)
def delete_workout(
    template_id: int,
    session: Session = Depends(get_session),
) -> Response:
    """Delete a workout template by id."""
    try:
        delete_template(session, template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(status_code=204)
