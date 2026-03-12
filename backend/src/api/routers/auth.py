from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth import service as auth_service
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.schemas import (
    AccessTokenResponse,
    BootstrapRequest,
    BootstrapResponse,
    InviteResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from src.core.config import Settings, get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    """Register a new user using a valid invite code."""
    user = await auth_service.register(request, session)
    return RegisterResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate with email + password and receive JWT tokens."""
    return await auth_service.login(request, session)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> AccessTokenResponse:
    """Exchange a refresh token for a new access token."""
    return await auth_service.refresh_token(request.refresh_token, session)


@router.post("/bootstrap", response_model=BootstrapResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap(
    request: BootstrapRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BootstrapResponse:
    """Create the first admin user. Locked after first user exists."""
    await auth_service.bootstrap(request, session, settings.bootstrap_secret)
    return BootstrapResponse(message="Bootstrap successful. Admin user created.")


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> InviteResponse:
    """Create a new invite code (requires authentication)."""
    invite, invite_link = await auth_service.create_invite(current_user, session, settings.app_url)
    return InviteResponse(code=invite.code, invite_link=invite_link)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
    )
