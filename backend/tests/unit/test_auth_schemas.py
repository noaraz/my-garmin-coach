from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.auth.schemas import (
    BootstrapRequest,
    BootstrapResponse,
    GoogleAuthRequest,
    GoogleAuthResponse,
    TokenResponse,
    UserResponse,
)


class TestBootstrapRequest:
    def test_accepts_valid_google_id_token(self) -> None:
        """BootstrapRequest accepts setup_token + google_id_token."""
        req = BootstrapRequest(
            setup_token="valid-setup-token",
            google_id_token="google.id.token.value",
        )
        assert req.setup_token == "valid-setup-token"
        assert req.google_id_token == "google.id.token.value"

    def test_requires_setup_token(self) -> None:
        """BootstrapRequest raises ValidationError when setup_token is missing."""
        with pytest.raises(ValidationError):
            BootstrapRequest(google_id_token="some.token")  # type: ignore[call-arg]

    def test_requires_google_id_token(self) -> None:
        """BootstrapRequest raises ValidationError when google_id_token is missing."""
        with pytest.raises(ValidationError):
            BootstrapRequest(setup_token="tok")  # type: ignore[call-arg]

    def test_has_no_email_or_password_fields(self) -> None:
        """BootstrapRequest no longer has email or password fields."""
        req = BootstrapRequest(
            setup_token="tok",
            google_id_token="some.id.token",
        )
        assert not hasattr(req, "email")
        assert not hasattr(req, "password")


class TestBootstrapResponse:
    def test_has_invite_codes_field(self) -> None:
        """BootstrapResponse contains invite_codes list."""
        resp = BootstrapResponse(invite_codes=["abc", "def"])
        assert len(resp.invite_codes) == 2
        assert resp.invite_codes == ["abc", "def"]


class TestGoogleAuthRequest:
    def test_accepts_id_token_only(self) -> None:
        """GoogleAuthRequest is valid with just an id_token."""
        req = GoogleAuthRequest(id_token="google.jwt.token")
        assert req.id_token == "google.jwt.token"
        assert req.invite_code is None

    def test_accepts_id_token_and_invite_code(self) -> None:
        """GoogleAuthRequest accepts optional invite_code."""
        req = GoogleAuthRequest(id_token="google.jwt.token", invite_code="INVITE-001")
        assert req.invite_code == "INVITE-001"

    def test_requires_id_token(self) -> None:
        """GoogleAuthRequest raises ValidationError when id_token is missing."""
        with pytest.raises(ValidationError):
            GoogleAuthRequest()  # type: ignore[call-arg]


class TestGoogleAuthResponse:
    def test_is_alias_for_token_response(self) -> None:
        """GoogleAuthResponse is TokenResponse."""
        assert GoogleAuthResponse is TokenResponse

    def test_has_access_and_refresh_token_fields(self) -> None:
        """GoogleAuthResponse carries access_token, refresh_token, and token_type."""
        resp = GoogleAuthResponse(
            access_token="access.jwt",
            refresh_token="refresh.jwt",
        )
        assert resp.access_token == "access.jwt"
        assert resp.refresh_token == "refresh.jwt"
        assert resp.token_type == "bearer"


class TestUserResponse:
    def test_has_is_admin_field(self) -> None:
        """UserResponse includes is_admin boolean field."""
        ur = UserResponse(id=1, email="a@b.com", is_active=True, is_admin=True)
        assert ur.is_admin is True

    def test_is_admin_defaults_to_false(self) -> None:
        """is_admin can be False."""
        ur = UserResponse(id=1, email="a@b.com", is_active=True, is_admin=False)
        assert ur.is_admin is False
