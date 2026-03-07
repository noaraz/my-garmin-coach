from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session, select

from src.db.models import WorkoutTemplate


def create_template(session: Session, data: dict[str, Any]) -> WorkoutTemplate:
    """Create a new WorkoutTemplate from the provided data dict."""
    template = WorkoutTemplate(
        name=data["name"],
        description=data.get("description"),
        sport_type=data.get("sport_type", "running"),
        tags=json.dumps(data["tags"]) if data.get("tags") is not None else None,
        steps=json.dumps(data["steps"]) if data.get("steps") is not None else None,
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


def list_templates(session: Session) -> list[WorkoutTemplate]:
    """Return all workout templates, ordered by created_at descending."""
    return list(session.exec(select(WorkoutTemplate)).all())


def update_template(
    session: Session, template_id: int, data: dict[str, Any]
) -> WorkoutTemplate:
    """Update a WorkoutTemplate by id. Returns the updated template.

    Raises ValueError if the template is not found.
    """
    template = session.get(WorkoutTemplate, template_id)
    if template is None:
        raise ValueError(f"WorkoutTemplate {template_id} not found")

    if "name" in data and data["name"] is not None:
        template.name = data["name"]
    if "description" in data and data["description"] is not None:
        template.description = data["description"]
    if "sport_type" in data and data["sport_type"] is not None:
        template.sport_type = data["sport_type"]
    if "tags" in data and data["tags"] is not None:
        template.tags = json.dumps(data["tags"])
    if "steps" in data and data["steps"] is not None:
        template.steps = json.dumps(data["steps"])

    template.updated_at = datetime.utcnow()
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


def delete_template(session: Session, template_id: int) -> None:
    """Delete a WorkoutTemplate by id.

    Raises ValueError if the template is not found.
    """
    template = session.get(WorkoutTemplate, template_id)
    if template is None:
        raise ValueError(f"WorkoutTemplate {template_id} not found")
    session.delete(template)
    session.commit()
