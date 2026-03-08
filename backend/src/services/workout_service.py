from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import WorkoutTemplate
from src.repositories.workouts import workout_template_repository


class WorkoutService:
    async def create_template(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> WorkoutTemplate:
        """Create a new WorkoutTemplate from the provided data dict."""
        template = WorkoutTemplate(
            name=data["name"],
            description=data.get("description"),
            sport_type=data.get("sport_type", "running"),
            tags=json.dumps(data["tags"]) if data.get("tags") is not None else None,
            steps=json.dumps(data["steps"]) if data.get("steps") is not None else None,
        )
        return await workout_template_repository.create(session, template)

    async def list_templates(self, session: AsyncSession) -> list[WorkoutTemplate]:
        """Return all workout templates."""
        return await workout_template_repository.get_all_ordered(session)

    async def update_template(
        self, session: AsyncSession, template_id: int, data: dict[str, Any]
    ) -> WorkoutTemplate:
        """Update a WorkoutTemplate by id. Raises ValueError if not found."""
        template = await workout_template_repository.get(session, template_id)
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
        await session.commit()
        await session.refresh(template)
        return template

    async def delete_template(self, session: AsyncSession, template_id: int) -> None:
        """Delete a WorkoutTemplate by id. Raises ValueError if not found."""
        template = await workout_template_repository.get(session, template_id)
        if template is None:
            raise ValueError(f"WorkoutTemplate {template_id} not found")
        await workout_template_repository.delete(session, template)


workout_service = WorkoutService()

# ---------------------------------------------------------------------------
# Module-level shims for backward compatibility with existing router imports
# ---------------------------------------------------------------------------


async def create_template(session: AsyncSession, data: dict[str, Any]) -> WorkoutTemplate:
    return await workout_service.create_template(session, data)


async def list_templates(session: AsyncSession) -> list[WorkoutTemplate]:
    return await workout_service.list_templates(session)


async def update_template(
    session: AsyncSession, template_id: int, data: dict[str, Any]
) -> WorkoutTemplate:
    return await workout_service.update_template(session, template_id, data)


async def delete_template(session: AsyncSession, template_id: int) -> None:
    return await workout_service.delete_template(session, template_id)


async def get_template(session: AsyncSession, template_id: int) -> WorkoutTemplate | None:
    return await workout_template_repository.get(session, template_id)
