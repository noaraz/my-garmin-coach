from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.calendar import router as calendar_router
from src.api.routers.profile import router as profile_router
from src.api.routers.sync import router as sync_router
from src.api.routers.workouts import router as workouts_router
from src.api.routers.zones import router as zones_router
from src.core.config import get_settings
from src.db.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    application = FastAPI(title="GarminCoach", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/v1/health")
    async def health() -> dict:
        return {"status": "ok"}

    application.include_router(profile_router)
    application.include_router(zones_router)
    application.include_router(workouts_router)
    application.include_router(calendar_router)
    application.include_router(sync_router)

    return application


app = create_app()
