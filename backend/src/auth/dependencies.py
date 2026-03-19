from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.jwt import decode_token
from src.auth.models import User
from src.core import cache

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/google")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Decode JWT and return the authenticated User.

    Uses an in-memory TTL cache (60s) to avoid hitting the DB on every request.

    Raises:
        HTTPException 401 on invalid/expired token or inactive user.
    """
    credentials_exc = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exc

    if payload.get("type") != "access":
        raise credentials_exc

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exc

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exc

    # Check cache first to save a DB query
    cache_key = f"user:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        # Cached as a dict to avoid DetachedInstanceError across sessions
        if not cached.get("is_active", True):
            raise credentials_exc
        user = User(
            id=cached["id"],
            email=cached["email"],
            is_admin=cached.get("is_admin", False),
            is_active=cached.get("is_active", True),
            google_oauth_sub=cached.get("google_oauth_sub"),
        )
        return user

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exc

    # Cache as dict (not ORM object) to avoid cross-session issues
    cache.set(cache_key, {
        "id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "google_oauth_sub": user.google_oauth_sub,
    })

    return user
