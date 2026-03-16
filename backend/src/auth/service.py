from __future__ import annotations

import secrets
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.auth.models import InviteCode, User
from src.auth.schemas import (
    AccessTokenResponse,
    BootstrapRequest,
    BootstrapResponse,
    GoogleAuthRequest,
    ResetAdminsRequest,
    ResetAdminsResponse,
    TokenResponse,
)
from src.core.config import get_settings

_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def _google_userinfo(access_token: str) -> dict:
    """Fetch user info from Google using an OAuth2 access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google access token")
    data = resp.json()
    if not data.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")
    return data


async def bootstrap(
    request: BootstrapRequest,
    session: AsyncSession,
) -> BootstrapResponse:
    """Create the first admin user via Google OAuth and generate 5 invite codes.

    Raises:
        HTTPException 403 if setup_token is wrong.
        HTTPException 409 if any user already exists.
        HTTPException 401 if the Google access token is invalid.
    """
    settings = get_settings()
    if not secrets.compare_digest(request.setup_token, settings.bootstrap_secret):
        raise HTTPException(status_code=403, detail="Invalid setup token")

    existing = (await session.exec(select(User).limit(1))).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Admin already exists")

    userinfo = await _google_userinfo(request.google_access_token)
    admin = User(
        email=userinfo["email"],
        google_oauth_sub=userinfo["sub"],
        is_admin=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    codes: list[str] = []
    for _ in range(5):
        invite = await create_invite(admin, session)
        codes.append(invite.code)

    return BootstrapResponse(invite_codes=codes)


async def google_auth(
    request: GoogleAuthRequest,
    session: AsyncSession,
) -> TokenResponse:
    """Authenticate or register a user via Google OAuth.

    Raises:
        HTTPException 401 if the Google access token is invalid.
        HTTPException 403 if user is unknown and no valid invite code provided.
    """
    userinfo = await _google_userinfo(request.access_token)
    google_sub: str = userinfo["sub"]
    email: str = userinfo["email"]

    # Find existing user by google_oauth_sub only — never fall back to email,
    # as that would allow any Google account with a matching email to take over
    # an existing account.
    user = (
        await session.exec(
            select(User).where(User.google_oauth_sub == google_sub)
        )
    ).first()

    # Existing user -> issue tokens
    if user:
        return _make_token_response(user)

    # New user with invite -> create account
    if request.invite_code:
        invite = (
            await session.exec(
                select(InviteCode).where(InviteCode.code == request.invite_code)
            )
        ).first()
        if invite is None or invite.used_by is not None:
            raise HTTPException(
                status_code=403, detail="Invalid or already-used invite code"
            )

        user = User(
            email=email,
            google_oauth_sub=google_sub,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        invite.used_by = user.id
        invite.used_at = datetime.now(timezone.utc)
        session.add(invite)
        await session.commit()

        return _make_token_response(user)

    # No invite -> 403
    raise HTTPException(
        status_code=403, detail="No account found. Request an invite to join."
    )


def _make_token_response(user: User) -> TokenResponse:
    """Build a TokenResponse with access + refresh tokens for the given user."""
    return TokenResponse(
        access_token=create_access_token(user.id, user.email, user.is_admin),
        refresh_token=create_refresh_token(user.id),
    )


async def reset_admins(
    request: ResetAdminsRequest,
    session: AsyncSession,
) -> ResetAdminsResponse:
    """Delete all users and invite codes (full factory reset).

    Raises:
        HTTPException 403 if setup_token is wrong.
    """
    settings = get_settings()
    if not secrets.compare_digest(request.setup_token, settings.bootstrap_secret):
        raise HTTPException(status_code=403, detail="Invalid setup token")

    # Delete all invite codes first (FK constraint)
    invite_codes = (await session.exec(select(InviteCode))).all()
    for invite in invite_codes:
        await session.delete(invite)
    await session.commit()

    # Delete all users
    users = (await session.exec(select(User))).all()
    for user in users:
        await session.delete(user)
    await session.commit()

    return ResetAdminsResponse(deleted=len(users))


async def refresh_token(
    refresh_tok: str,
    session: AsyncSession,
) -> AccessTokenResponse:
    """Exchange a refresh token for a new access token.

    Raises:
        HTTPException 401 on invalid or expired refresh token.
    """
    from jose import JWTError

    try:
        payload = decode_token(refresh_tok)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return AccessTokenResponse(
        access_token=create_access_token(user.id, user.email, user.is_admin)
    )


async def create_invite(
    created_by_user: User,
    session: AsyncSession,
) -> InviteCode:
    """Create a new invite code for the current user."""
    code = secrets.token_urlsafe(16)
    invite = InviteCode(code=code, created_by=created_by_user.id)
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    return invite
