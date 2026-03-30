from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth import service as auth_service
from src.auth.dependencies import get_current_user
from src.auth.jwt import hash_token
from src.auth.models import User
from src.auth.schemas import (
    AccessTokenResponse,
    BootstrapRequest,
    BootstrapResponse,
    GoogleAuthRequest,
    GoogleAuthResponse,
    InviteResponse,
    LogoutAllResponse,
    LogoutResponse,
    ResetAdminsRequest,
    ResetAdminsResponse,
    UserResponse,
)
from src.core.config import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/google", response_model=GoogleAuthResponse)
async def google_auth(
    request: GoogleAuthRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> GoogleAuthResponse:
    """Authenticate or register via Google OAuth and receive JWT tokens."""
    access_token, raw_refresh_token = await auth_service.google_auth(request, session)
    await session.commit()

    settings = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/v1/auth",
    )

    return GoogleAuthResponse(access_token=access_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AccessTokenResponse:
    """Exchange a refresh token (from httpOnly cookie) for a new access token."""
    refresh_tok = request.cookies.get("refresh_token")
    if not refresh_tok:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    access_token, new_raw_refresh_token = await auth_service.refresh_token(
        refresh_tok, session
    )
    await session.commit()

    settings = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/v1/auth",
    )

    return AccessTokenResponse(access_token=access_token)


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InviteResponse:
    """Create a new invite code (requires admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    invite = await auth_service.create_invite(current_user, session)
    return InviteResponse(code=invite.code)


@router.post("/bootstrap", response_model=BootstrapResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap(
    request: BootstrapRequest,
    session: AsyncSession = Depends(get_session),
) -> BootstrapResponse:
    """Bootstrap the first admin user and generate 5 invite codes."""
    return await auth_service.bootstrap(request, session)


@router.post("/reset-admins", response_model=ResetAdminsResponse)
async def reset_admins(
    request: ResetAdminsRequest,
    session: AsyncSession = Depends(get_session),
) -> ResetAdminsResponse:
    """Remove all admin users and their invite codes (requires setup token).

    WARNING: This endpoint wipes all users and invite codes. It is protected only by
    BOOTSTRAP_SECRET. Add rate limiting (slowapi) or an IP allowlist before any public
    deployment. See CLAUDE.md "Nice to Have" — Rate Limiting on Auth Routes.
    """
    return await auth_service.reset_admins(request, session)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> LogoutResponse:
    """Revoke the current refresh token and clear the cookie."""
    refresh_tok = request.cookies.get("refresh_token")
    if not refresh_tok:
        # Idempotent — no cookie means already logged out
        return LogoutResponse(ok=True)

    token_hash = hash_token(refresh_tok)
    await auth_service.revoke_refresh_token(token_hash, session)
    await session.commit()

    # Delete cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    return LogoutResponse(ok=True)


@router.post("/logout-all", response_model=LogoutAllResponse)
async def logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LogoutAllResponse:
    """Revoke all refresh tokens for the current user (sign out of all devices)."""
    revoked_count = await auth_service.revoke_all_refresh_tokens(
        current_user.id, session
    )
    await session.commit()

    # Delete cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    return LogoutAllResponse(revoked=revoked_count)
