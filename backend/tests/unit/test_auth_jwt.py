from __future__ import annotations

from jose import jwt

from src.auth.jwt import create_access_token
from src.core.config import get_settings


class TestCreateAccessToken:
    def test_create_access_token_includes_is_admin_claim_when_true(self) -> None:
        # Arrange
        settings = get_settings()

        # Act
        token = create_access_token(user_id=42, email="a@b.com", is_admin=True)
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )

        # Assert
        assert payload["is_admin"] is True

    def test_create_access_token_defaults_is_admin_false(self) -> None:
        # Arrange
        settings = get_settings()

        # Act
        token = create_access_token(user_id=1, email="a@b.com")
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )

        # Assert
        assert payload["is_admin"] is False
