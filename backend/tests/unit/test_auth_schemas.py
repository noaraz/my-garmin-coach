from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.auth.schemas import BootstrapRequest, BootstrapResponse, UserResponse


class TestBootstrapRequest:
    def test_validates_password_length_minimum(self) -> None:
        """Password must be at least 8 characters."""
        with pytest.raises(ValidationError):
            BootstrapRequest(setup_token="tok", email="a@b.com", password="short")

    def test_accepts_valid_password(self) -> None:
        """Password with 8+ characters is accepted."""
        req = BootstrapRequest(
            setup_token="valid_token", email="user@example.com", password="ValidPass123"
        )
        assert req.password == "ValidPass123"


class TestBootstrapResponse:
    def test_has_invite_codes_field(self) -> None:
        """BootstrapResponse contains invite_codes list."""
        resp = BootstrapResponse(invite_codes=["abc", "def"])
        assert len(resp.invite_codes) == 2
        assert resp.invite_codes == ["abc", "def"]


class TestUserResponse:
    def test_has_is_admin_field(self) -> None:
        """UserResponse includes is_admin boolean field."""
        ur = UserResponse(id=1, email="a@b.com", is_active=True, is_admin=True)
        assert ur.is_admin is True

    def test_is_admin_defaults_to_false(self) -> None:
        """is_admin can be False."""
        ur = UserResponse(id=1, email="a@b.com", is_active=True, is_admin=False)
        assert ur.is_admin is False
