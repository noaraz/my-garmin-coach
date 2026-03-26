from __future__ import annotations

import asyncio
import logging

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
from src.garmin.client_factory import CHROME_VERSION, create_login_client
from src.garmin.encryption import encrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/garmin", tags=["garmin"])


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

    logger.info("Garmin connect requested for user_id=%s", current_user.id)

    last_exc: Exception | None = None
    for attempt in range(2):
        if attempt > 0:
            await asyncio.sleep(3)
        try:
            use_proxy = attempt > 0 and bool(settings.fixie_url)
            client = create_login_client(
                proxy_url=settings.fixie_url if use_proxy else None
            )
            if use_proxy:
                logger.info(
                    "Garmin login attempt %d/2: %s TLS + Fixie proxy (429 retry)",
                    attempt + 1,
                    CHROME_VERSION,
                )
            else:
                logger.info(
                    "Garmin login attempt %d/2: %s TLS, no proxy",
                    attempt + 1,
                    CHROME_VERSION,
                )
            client.login(email, password)
            token_json: str = client.dumps()
            logger.info(
                "Garmin login succeeded on attempt %d/2 (proxy=%s) for user_id=%s",
                attempt + 1,
                use_proxy,
                current_user.id,
            )
            break
        except (requests.exceptions.HTTPError, GarthHTTPError) as exc:
            last_exc = exc
            # GarthHTTPError wraps requests.HTTPError — get response from either
            response = getattr(exc, "response", None)
            if response is None:
                response = getattr(getattr(exc, "__cause__", None), "response", None)
            if response is not None and response.status_code == 429:
                logger.warning(
                    "Garmin SSO rate-limited (429) on attempt %d/2 — "
                    "Akamai blocked this request (proxy=%s)",
                    attempt + 1,
                    use_proxy,
                )
                continue
            # Don't log exc — garth embeds the PreparedRequest (incl. form body
            # with plaintext credentials) in the exception chain. Log only the
            # exception type, not the object or traceback.
            logger.error(
                "Garmin login rejected (non-429) on attempt %d/2: %s",
                attempt + 1,
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=400,
                detail="Garmin authentication failed. Check your email and password.",
            ) from exc
        except cffi_requests.exceptions.ProxyError as exc:
            last_exc = exc
            # Don't log exc — it contains the proxy URL with credentials
            logger.error(
                "Garmin proxy unreachable on attempt %d/2 — check FIXIE_URL config",
                attempt + 1,
            )
            raise HTTPException(
                status_code=503,
                detail="Garmin connection unavailable. Please try again later.",
            ) from exc
        except Exception as exc:
            last_exc = exc
            # Don't log exc — may contain credentials in the exception chain
            logger.error(
                "Garmin login unexpected error on attempt %d/2: %s",
                attempt + 1,
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=400,
                detail="Garmin authentication failed. Check your email and password.",
            ) from exc
    else:
        logger.error(
            "Garmin login failed after all retries for user_id=%s — "
            "Akamai may have updated detection. Check test_garmin_login.py.",
            current_user.id,
        )
        raise HTTPException(
            status_code=503,
            detail="Garmin is temporarily rate-limiting this server. Please try again in a few minutes.",
        ) from last_exc

    # Encrypt and store token
    logger.info("Storing encrypted Garmin token for user_id=%s", current_user.id)
    encrypted = encrypt_token(current_user.id, settings.garmincoach_secret_key, token_json)

    profile = await _get_or_create_profile(current_user, session)
    profile.garmin_oauth_token_encrypted = encrypted
    profile.garmin_connected = True
    session.add(profile)
    await session.commit()

    logger.info("Garmin connected successfully for user_id=%s", current_user.id)
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
