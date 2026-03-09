from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routers.auth import router as auth_router
from src.api.routers.calendar import router as calendar_router
from src.api.routers.garmin_connect import router as garmin_connect_router
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

    application.include_router(auth_router)
    application.include_router(garmin_connect_router)
    application.include_router(profile_router)
    application.include_router(zones_router)
    application.include_router(workouts_router)
    application.include_router(calendar_router)
    application.include_router(sync_router)

    # Mount React static build last — must come after all API routers
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        application.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return application


app = create_app()
