from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

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
from src.core import cache
from src.core.config import get_settings

_GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def _google_userinfo(access_token: str) -> dict[str, Any]:
    """Fetch and validate user info from Google using an OAuth2 access token.

    Uses the tokeninfo endpoint to validate the token audience (azp claim),
    then the userinfo endpoint for the full profile (sub, email, picture, etc.).
    Token is sent in the POST body — not as a URL query param — to avoid
    leaking it into server access logs.
    """
    settings = get_settings()
    try:
        async with httpx.AsyncClient() as client:
            # Validate token audience via tokeninfo — azp is the OAuth2 client_id
            # that issued the token. The userinfo endpoint does not expose this claim.
            # POST body avoids exposing the token in server access logs.
            if settings.google_client_id:
                ti_resp = await client.post(
                    _GOOGLE_TOKENINFO_URL,
                    data={"access_token": access_token},
                )
                if ti_resp.status_code != 200:
                    raise HTTPException(status_code=401, detail="Invalid Google access token")
                ti = ti_resp.json()
                if ti.get("azp") != settings.google_client_id:
                    raise HTTPException(status_code=401, detail="Google token audience mismatch")

            resp = await client.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Google service unavailable")
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

    # Batch create 5 invite codes (inline to avoid per-invite commit overhead)
    codes: list[str] = []
    for _ in range(5):
        code = secrets.token_urlsafe(16)
        invite = InviteCode(code=code, created_by=admin.id)
        session.add(invite)
        codes.append(code)
    await session.commit()

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
        invite.used_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
    from sqlalchemy import delete

    settings = get_settings()
    if not secrets.compare_digest(request.setup_token, settings.bootstrap_secret):
        raise HTTPException(status_code=403, detail="Invalid setup token")

    # Count users before deletion (for response)
    users = (await session.exec(select(User))).all()
    user_count = len(users)

    # Bulk delete — FK order: invites first, then users
    await session.execute(delete(InviteCode))
    await session.execute(delete(User))
    await session.commit()

    # Invalidate all cached user entries (users are now deleted)
    cache.clear()

    return ResetAdminsResponse(deleted=user_count)


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
