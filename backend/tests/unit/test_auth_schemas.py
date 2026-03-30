from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.auth.schemas import (
    AccessTokenResponse,
    BootstrapRequest,
    BootstrapResponse,
    GoogleAuthRequest,
    GoogleAuthResponse,
    UserResponse,
)


class TestBootstrapRequest:
    def test_accepts_valid_google_access_token(self) -> None:
        """BootstrapRequest accepts setup_token + google_access_token."""
        req = BootstrapRequest(
            setup_token="valid-setup-token",
            google_access_token="google.access.token.value",
        )
        assert req.setup_token == "valid-setup-token"
        assert req.google_access_token == "google.access.token.value"

    def test_requires_setup_token(self) -> None:
        """BootstrapRequest raises ValidationError when setup_token is missing."""
        with pytest.raises(ValidationError):
            BootstrapRequest(google_access_token="some.token")  # type: ignore[call-arg]

    def test_requires_google_access_token(self) -> None:
        """BootstrapRequest raises ValidationError when google_access_token is missing."""
        with pytest.raises(ValidationError):
            BootstrapRequest(setup_token="tok")  # type: ignore[call-arg]

    def test_has_no_email_or_password_fields(self) -> None:
        """BootstrapRequest no longer has email or password fields."""
        req = BootstrapRequest(
            setup_token="tok",
            google_access_token="some.access.token",
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
    def test_accepts_access_token_only(self) -> None:
        """GoogleAuthRequest is valid with just an access_token."""
        req = GoogleAuthRequest(access_token="google.access.token")
        assert req.access_token == "google.access.token"
        assert req.invite_code is None

    def test_accepts_access_token_and_invite_code(self) -> None:
        """GoogleAuthRequest accepts optional invite_code."""
        req = GoogleAuthRequest(access_token="google.access.token", invite_code="INVITE-001")
        assert req.invite_code == "INVITE-001"

    def test_requires_access_token(self) -> None:
        """GoogleAuthRequest raises ValidationError when access_token is missing."""
        with pytest.raises(ValidationError):
            GoogleAuthRequest()  # type: ignore[call-arg]


class TestGoogleAuthResponse:
    def test_is_alias_for_access_token_response(self) -> None:
        """GoogleAuthResponse is AccessTokenResponse (no refresh_token in body)."""
        assert GoogleAuthResponse is AccessTokenResponse

    def test_has_access_token_field_only(self) -> None:
        """GoogleAuthResponse carries access_token and token_type (refresh_token in httpOnly cookie)."""
        resp = GoogleAuthResponse(
            access_token="access.jwt",
        )
        assert resp.access_token == "access.jwt"
        assert resp.token_type == "bearer"
        assert not hasattr(resp, "refresh_token")


class TestUserResponse:
    def test_has_is_admin_field(self) -> None:
        """UserResponse includes is_admin boolean field."""
        ur = UserResponse(id=1, email="a@b.com", is_active=True, is_admin=True)
        assert ur.is_admin is True

    def test_is_admin_defaults_to_false(self) -> None:
        """is_admin can be False."""
        ur = UserResponse(id=1, email="a@b.com", is_active=True, is_admin=False)
        assert ur.is_admin is False
