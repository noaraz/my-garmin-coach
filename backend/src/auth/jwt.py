from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from src.core.config import get_settings


def _settings() -> Any:
    return get_settings()


def create_access_token(
    user_id: int, email: str = "", is_admin: bool = False
) -> str:
    """Create a short-lived JWT access token for the given user."""
    settings = _settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def hash_token(token: str) -> str:
    """Return SHA-256 hex digest of the token string."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Returns the payload dict.
    Raises JWTError on invalid or expired tokens.
    """
    settings = _settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
