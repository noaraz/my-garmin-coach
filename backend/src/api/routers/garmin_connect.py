from __future__ import annotations

import asyncio
import logging

import garth as garth
import requests
from curl_cffi import requests as cffi_requests
from garth.exc import GarthHTTPError
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.schemas import GarminConnectRequest, GarminStatusResponse
from src.core.config import get_settings
from src.db.models import AthleteProfile
from src.garmin.encryption import encrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/garmin", tags=["garmin"])


class _ChromeTLSSession(cffi_requests.Session):
    """curl_cffi session with requests.Session compatibility shims for garth.

    Garmin SSO uses Akamai Bot Manager which blocks Python requests' TLS fingerprint.
    Chrome 120 impersonation bypasses it — no proxy needed (confirmed via test_garmin_login.py).
    garth accesses requests.Session internals (adapters, hooks) so we pre-populate them.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        _rs = requests.Session()
        self.adapters = _rs.adapters
        self.hooks = _rs.hooks


async def _get_or_create_profile(user: User, session: AsyncSession) -> AthleteProfile:
    """Return existing AthleteProfile for user, or create one."""
    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == user.id)
        )
    ).first()
    if profile is None:
        profile = AthleteProfile(user_id=user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


@router.post("/connect", response_model=GarminStatusResponse)
async def connect_garmin(
    request: GarminConnectRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminStatusResponse:
    """Connect Garmin account by authenticating with garth.

    The user's email and password are discarded immediately after use.
    The OAuth token is encrypted at rest using a per-user Fernet key.
    """
    settings = get_settings()

    # Authenticate with Garmin via garth.
    # Garmin rate-limits OAuth requests from cloud/datacenter IPs (429).
    # One retry after a short wait resolves most transient 429s.
    email, password = request.email, request.password
    del request  # Discard credentials as early as possible

    last_exc: Exception | None = None
    for attempt in range(2):
        if attempt > 0:
            await asyncio.sleep(3)
        try:
            client = garth.Client()
            # Use curl_cffi to impersonate Chrome TLS fingerprint — bypasses
            # Akamai Bot Manager which blocks Python requests' known bot fingerprint.
            # garth accesses sess.adapters internally, so we patch it in.
            client.sess = _ChromeTLSSession(impersonate="chrome120")
            # Attempt 1: chrome120 TLS fingerprint only (no proxy) — sufficient in most cases.
            # Attempt 2: add Fixie proxy as fallback in case Akamai updates IP detection.
            use_proxy = attempt > 0 and bool(settings.fixie_url)
            if use_proxy:
                client.sess.proxies = {"https": settings.fixie_url}
                logger.info("Garmin login attempt %d/2 using curl_cffi chrome120 + Fixie proxy", attempt + 1)
            else:
                logger.info("Garmin login attempt %d/2 using curl_cffi chrome120 (no proxy)", attempt + 1)
            client.login(email, password)
            token_json: str = client.dumps()
            break
        except (requests.exceptions.HTTPError, GarthHTTPError) as exc:
            last_exc = exc
            # GarthHTTPError wraps requests.HTTPError — get response from either
            response = getattr(exc, "response", None)
            if response is None:
                response = getattr(getattr(exc, "__cause__", None), "response", None)
            if response is not None and response.status_code == 429:
                logger.warning("Garmin rate-limited (429), attempt %d/2", attempt + 1)
                continue
            logger.exception("Garmin login failed: %s", exc)
            raise HTTPException(
                status_code=400,
                detail="Garmin authentication failed. Check your email and password.",
            ) from exc
        except requests.exceptions.ProxyError as exc:
            last_exc = exc
            # Log without including exc to avoid leaking proxy credentials from the URL
            logger.error("Garmin proxy connection failed (proxy unreachable or misconfigured)")
            raise HTTPException(
                status_code=503,
                detail="Garmin connection unavailable. Please try again later.",
            ) from exc
        except Exception as exc:
            last_exc = exc
            logger.exception("Garmin login failed: %s", exc)
            raise HTTPException(
                status_code=400,
                detail="Garmin authentication failed. Check your email and password.",
            ) from exc
    else:
        logger.error("Garmin login failed after retries: %s", last_exc)
        raise HTTPException(
            status_code=503,
            detail="Garmin is temporarily rate-limiting this server. Please try again in a few minutes.",
        ) from last_exc

    # Encrypt and store token
    encrypted = encrypt_token(current_user.id, settings.garmincoach_secret_key, token_json)

    profile = await _get_or_create_profile(current_user, session)
    profile.garmin_oauth_token_encrypted = encrypted
    profile.garmin_connected = True
    session.add(profile)
    await session.commit()

    return GarminStatusResponse(connected=True)


@router.get("/status", response_model=GarminStatusResponse)
async def garmin_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminStatusResponse:
    """Return whether the current user has a connected Garmin account."""
    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == current_user.id)
        )
    ).first()
    connected = profile is not None and profile.garmin_connected
    return GarminStatusResponse(connected=connected)


@router.post("/disconnect", response_model=GarminStatusResponse)
async def disconnect_garmin(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GarminStatusResponse:
    """Remove stored Garmin token and mark account as disconnected."""
    profile = (
        await session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == current_user.id)
        )
    ).first()
    if profile is not None:
        profile.garmin_oauth_token_encrypted = None
        profile.garmin_connected = False
        session.add(profile)
        await session.commit()

    return GarminStatusResponse(connected=False)
