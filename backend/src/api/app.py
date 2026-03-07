from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routers.calendar import router as calendar_router
from src.api.routers.profile import router as profile_router
from src.api.routers.sync import router as sync_router
from src.api.routers.workouts import router as workouts_router
from src.api.routers.zones import router as zones_router
from src.db.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(title="GarminCoach", lifespan=lifespan)

    @application.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    application.include_router(profile_router)
    application.include_router(zones_router)
    application.include_router(workouts_router)
    application.include_router(calendar_router)
    application.include_router(sync_router)

    return application


app = create_app()
