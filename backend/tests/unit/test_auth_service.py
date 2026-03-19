from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import src.db.models  # noqa: F401 — register all SQLModel tables
import src.auth.models  # noqa: F401 — register User/InviteCode tables
from src.auth import service as auth_service
from src.auth.models import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = sessionmaker(  # type: ignore[call-overload]
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------
# refresh_token
# ---------------------------------------------------------------------------


class TestRefreshToken:
    async def _seed_user(self, db_session: AsyncSession) -> User:
        user = User(email="user@example.com")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    async def test_refresh_token_valid_returns_new_access_token(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange
        user = await self._seed_user(db_session)
        from src.auth.jwt import create_refresh_token
        refresh_tok = create_refresh_token(user.id)

        # Act — lines 123-136
        response = await auth_service.refresh_token(refresh_tok, db_session)

        # Assert
        assert response.access_token
        assert response.token_type == "bearer"

    async def test_refresh_token_with_access_token_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — pass an access token where a refresh token is expected
        user = await self._seed_user(db_session)
        from src.auth.jwt import create_access_token
        access_tok = create_access_token(user.id)

        # Act & Assert — line 129: type != "refresh"
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(access_tok, db_session)

        assert exc_info.value.status_code == 401

    async def test_refresh_token_invalid_token_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — garbage token
        bad_token = "not.a.valid.jwt"

        # Act & Assert — lines 124-126: JWTError
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(bad_token, db_session)

        assert exc_info.value.status_code == 401

    async def test_refresh_token_inactive_user_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — deactivate the user
        user = await self._seed_user(db_session)
        user.is_active = False
        db_session.add(user)
        await db_session.commit()

        from src.auth.jwt import create_refresh_token
        refresh_tok = create_refresh_token(user.id)

        # Act & Assert — line 133-134: user.is_active is False
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(refresh_tok, db_session)

        assert exc_info.value.status_code == 401

    async def test_refresh_token_nonexistent_user_raises_401(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange — create token for user 9999 who doesn't exist
        from src.auth.jwt import create_refresh_token
        refresh_tok = create_refresh_token(9999)

        # Act & Assert — line 133-134: user is None
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(refresh_tok, db_session)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# create_invite
# ---------------------------------------------------------------------------


def _make_httpx_response(status_code: int, json_data: dict) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


class TestGoogleUserinfo:
    """Unit tests for _google_userinfo — mocks httpx so the function body is exercised."""

    from src.auth.service import _google_userinfo  # import at class scope for consistent use

    def _mock_client(self, tokeninfo_resp: MagicMock, userinfo_resp: MagicMock) -> MagicMock:
        client = AsyncMock()
        # tokeninfo uses POST, userinfo uses GET — side_effect covers both in order
        client.post = AsyncMock(return_value=tokeninfo_resp)
        client.get = AsyncMock(return_value=userinfo_resp)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    @pytest.mark.asyncio
    async def test_valid_token_with_matching_audience_succeeds(self) -> None:
        # Arrange
        from src.auth.service import _google_userinfo
        tokeninfo = _make_httpx_response(200, {"azp": "my-client-id", "email": "u@e.com"})
        userinfo = _make_httpx_response(200, {
            "sub": "123", "email": "u@e.com", "email_verified": True,
        })
        with patch("src.auth.service.httpx.AsyncClient", return_value=self._mock_client(tokeninfo, userinfo)):
            with patch("src.auth.service.get_settings") as mock_settings:
                mock_settings.return_value.google_client_id = "my-client-id"
                result = await _google_userinfo("tok")
        assert result["email"] == "u@e.com"

    @pytest.mark.asyncio
    async def test_audience_mismatch_raises_401(self) -> None:
        # Arrange — azp is a different client
        from src.auth.service import _google_userinfo
        tokeninfo = _make_httpx_response(200, {"azp": "other-client-id"})
        userinfo = _make_httpx_response(200, {"sub": "123", "email": "u@e.com", "email_verified": True})
        with patch("src.auth.service.httpx.AsyncClient", return_value=self._mock_client(tokeninfo, userinfo)):
            with patch("src.auth.service.get_settings") as mock_settings:
                mock_settings.return_value.google_client_id = "my-client-id"
                with pytest.raises(HTTPException) as exc:
                    await _google_userinfo("tok")
        assert exc.value.status_code == 401
        assert "mismatch" in exc.value.detail

    @pytest.mark.asyncio
    async def test_tokeninfo_non200_raises_401(self) -> None:
        # Arrange — tokeninfo returns non-200 (invalid/expired token)
        from src.auth.service import _google_userinfo
        tokeninfo = _make_httpx_response(400, {"error": "invalid_token"})
        userinfo = _make_httpx_response(200, {})
        with patch("src.auth.service.httpx.AsyncClient", return_value=self._mock_client(tokeninfo, userinfo)):
            with patch("src.auth.service.get_settings") as mock_settings:
                mock_settings.return_value.google_client_id = "my-client-id"
                with pytest.raises(HTTPException) as exc:
                    await _google_userinfo("bad-token")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_userinfo_non200_raises_401(self) -> None:
        # Arrange — tokeninfo passes but userinfo returns non-200
        # (token revoked between the two calls)
        from src.auth.service import _google_userinfo
        tokeninfo = _make_httpx_response(200, {"azp": "my-client-id"})
        userinfo = _make_httpx_response(401, {"error": "invalid_token"})
        with patch("src.auth.service.httpx.AsyncClient", return_value=self._mock_client(tokeninfo, userinfo)):
            with patch("src.auth.service.get_settings") as mock_settings:
                mock_settings.return_value.google_client_id = "my-client-id"
                with pytest.raises(HTTPException) as exc:
                    await _google_userinfo("tok")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_unverified_email_raises_401(self) -> None:
        # Arrange — email not verified
        from src.auth.service import _google_userinfo
        tokeninfo = _make_httpx_response(200, {"azp": "my-client-id"})
        userinfo = _make_httpx_response(200, {
            "sub": "123", "email": "u@e.com", "email_verified": False,
        })
        with patch("src.auth.service.httpx.AsyncClient", return_value=self._mock_client(tokeninfo, userinfo)):
            with patch("src.auth.service.get_settings") as mock_settings:
                mock_settings.return_value.google_client_id = "my-client-id"
                with pytest.raises(HTTPException) as exc:
                    await _google_userinfo("tok")
        assert exc.value.status_code == 401
        assert "not verified" in exc.value.detail

    @pytest.mark.asyncio
    async def test_network_error_raises_503(self) -> None:
        # Arrange — Google service unreachable
        from src.auth.service import _google_userinfo
        client = AsyncMock()
        client.post = AsyncMock(side_effect=httpx.ConnectError("unreachable"))
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=False)
        with patch("src.auth.service.httpx.AsyncClient", return_value=cm):
            with patch("src.auth.service.get_settings") as mock_settings:
                mock_settings.return_value.google_client_id = "my-client-id"
                with pytest.raises(HTTPException) as exc:
                    await _google_userinfo("tok")
        assert exc.value.status_code == 503
        assert "unavailable" in exc.value.detail

    @pytest.mark.asyncio
    async def test_skips_audience_check_when_client_id_not_configured(self) -> None:
        # Arrange — no google_client_id configured (dev/test env)
        from src.auth.service import _google_userinfo
        userinfo = _make_httpx_response(200, {
            "sub": "123", "email": "u@e.com", "email_verified": True,
        })
        client = AsyncMock()
        client.get = AsyncMock(return_value=userinfo)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=False)
        with patch("src.auth.service.httpx.AsyncClient", return_value=cm):
            with patch("src.auth.service.get_settings") as mock_settings:
                mock_settings.return_value.google_client_id = ""
                result = await _google_userinfo("tok")
        assert result["sub"] == "123"
        # Only one HTTP call (GET userinfo) — POST tokeninfo was skipped
        assert client.get.call_count == 1
        assert client.post.call_count == 0


class TestCreateInvite:
    async def test_create_invite_returns_invite_with_code(
        self, db_session: AsyncSession
    ) -> None:
        # Arrange
        admin = User(email="admin@example.com")
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        # Act — lines 144-149
        invite = await auth_service.create_invite(admin, db_session)

        # Assert
        assert invite.id is not None
        assert invite.code
        assert len(invite.code) > 0
        assert invite.created_by == admin.id
        assert invite.used_by is None
