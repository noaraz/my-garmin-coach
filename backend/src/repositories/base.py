from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    """Generic async repository with standard CRUD operations."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, session: AsyncSession, id: int) -> ModelType | None:
        return await session.get(self.model, id)

    async def get_all(self, session: AsyncSession) -> list[ModelType]:
        result = await session.exec(select(self.model))
        return list(result.all())

    async def create(self, session: AsyncSession, obj: ModelType) -> ModelType:
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def update(self, session: AsyncSession, obj: ModelType, data: dict[str, Any]) -> ModelType:
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def delete(self, session: AsyncSession, obj: ModelType) -> None:
        await session.delete(obj)
        await session.commit()
