from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.auth.models import InviteCode, User
from src.auth.passwords import hash_password, verify_password
from src.auth.schemas import (
    AccessTokenResponse,
    BootstrapRequest,
    BootstrapResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from src.core.config import get_settings

_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15


async def bootstrap(
    request: BootstrapRequest,
    session: AsyncSession,
) -> BootstrapResponse:
    """Create the first admin user and 5 invite codes.

    Raises:
        HTTPException 403 if setup_token is wrong.
        HTTPException 409 if any user already exists.
    """
    settings = get_settings()
    if not secrets.compare_digest(request.setup_token, settings.bootstrap_secret):
        raise HTTPException(status_code=403, detail="Invalid setup token")

    existing = (await session.exec(select(User).limit(1))).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Admin already exists")

    admin = User(
        email=request.email,
        password_hash=hash_password(request.password),
        is_admin=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    codes: list[str] = []
    for _ in range(5):
        code = secrets.token_urlsafe(16)
        invite = InviteCode(code=code, created_by=admin.id)
        session.add(invite)
        codes.append(code)
    await session.commit()

    return BootstrapResponse(invite_codes=codes)


async def register(
    request: RegisterRequest,
    session: AsyncSession,
) -> User:
    """Register a new user consuming an invite code.

    Raises:
        HTTPException 403 if invite code is invalid or already used.
        HTTPException 409 if email is already registered.
    """
    # Check for duplicate email first (returns 409 before 403 for better UX)
    existing = (
        await session.exec(select(User).where(User.email == request.email))
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate invite code
    invite = (
        await session.exec(
            select(InviteCode).where(InviteCode.code == request.invite_code)
        )
    ).first()
    if invite is None or invite.used_by is not None:
        raise HTTPException(status_code=403, detail="Invalid or already-used invite code")

    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Mark invite as used
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)
    session.add(invite)
    await session.commit()

    return user


async def login(
    request: LoginRequest,
    session: AsyncSession,
) -> TokenResponse:
    """Authenticate a user and return JWT tokens.

    Raises:
        HTTPException 401 on invalid credentials or account locked.
    """
    user = (
        await session.exec(select(User).where(User.email == request.email))
    ).first()

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check lockout
    if user.locked_until is not None:
        now = datetime.now(timezone.utc)
        locked_until_aware = user.locked_until.replace(tzinfo=timezone.utc) if user.locked_until.tzinfo is None else user.locked_until
        if now < locked_until_aware:
            raise HTTPException(status_code=401, detail="Account locked. Try again later.")

    # Verify password
    if not verify_password(request.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=_LOCKOUT_MINUTES)
        session.add(user)
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Successful login — reset counter
    user.failed_login_attempts = 0
    user.locked_until = None
    session.add(user)
    await session.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.email, user.is_admin),
        refresh_token=create_refresh_token(user.id),
    )


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
