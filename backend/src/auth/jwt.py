from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from src.core.config import get_settings


def _settings() -> Any:
    return get_settings()


def create_access_token(user_id: int) -> str:
    """Create a short-lived JWT access token for the given user."""
    settings = _settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived JWT refresh token for the given user."""
    settings = _settings()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Returns the payload dict.
    Raises JWTError on invalid or expired tokens.
    """
    settings = _settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
