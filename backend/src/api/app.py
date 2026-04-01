from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.routers.auth import router as auth_router
from src.api.routers.calendar import router as calendar_router
from src.api.routers.garmin_connect import router as garmin_connect_router
from src.api.routers.plans import router as plans_router
from src.api.routers.profile import router as profile_router
from src.api.routers.sync import router as sync_router
from src.api.routers.workouts import router as workouts_router
from src.api.routers.zones import router as zones_router
from src.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[arg-type]
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://accounts.google.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://accounts.google.com https://www.googleapis.com; "
            "frame-src 'none'; "
            "object-src 'none'"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Configure app-level logging.  logging.basicConfig(force=True) is
    # unreliable because uvicorn reconfigures the root logger *after*
    # create_app() runs (at import time).  Instead, attach a handler
    # directly to the "src" logger so all src.* loggers propagate to it.
    _app_logger = logging.getLogger("src")
    if not _app_logger.handlers:
        _handler = logging.StreamHandler(sys.stdout)
        _handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        _app_logger.addHandler(_handler)
    _app_logger.setLevel(logging.INFO)
    settings = get_settings()
    application = FastAPI(title="GarminCoach", lifespan=lifespan)

    application.add_middleware(SecurityHeadersMiddleware)
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
    application.include_router(plans_router)

    # Serve React SPA in production — must come after all API routers
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        # Serve hashed JS/CSS assets
        application.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        # Catch-all: serve exact static files (favicon, etc.) or fall back to index.html
        # for SPA routing (/login, /calendar, etc.)
        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            file = static_dir / full_path
            if file.is_file():
                return FileResponse(file)
            return FileResponse(static_dir / "index.html")

    return application


app = create_app()
