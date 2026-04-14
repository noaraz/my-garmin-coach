from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

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
from src.core import cache
from src.core.config import get_settings
from src.db.models import AthleteProfile, SystemConfig
from src.garmin import client_cache
from src.garmin.adapter_protocol import GarminAuthError, GarminRateLimitError
from src.garmin.client_factory import FINGERPRINT_SEQUENCE, create_login_client, login_and_get_token
from src.garmin.encryption import encrypt_credential, encrypt_token

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
    # Rotate through FINGERPRINT_SEQUENCE with 30-45s delays between attempts to
    # bypass Akamai bot detection. Proxy (Fixie) applied only on the last attempt.
    email, password = request.email, request.password
    del request  # Discard credentials as early as possible

    logger.info("Garmin connect requested for user_id=%s", current_user.id)

    # Determine auth version from runtime flag
    auth_version_row = await session.get(SystemConfig, "garmin_auth_version")
    auth_version = auth_version_row.value if auth_version_row else "v1"

    if auth_version == "v2":
        # V2: garminconnect 0.3.x handles retries internally — single call
        try:
            token_json = login_and_get_token(email, password, auth_version="v2")
            logger.info("Garmin V2 login succeeded for user_id=%s", current_user.id)
        except GarminAuthError as exc:
            raise HTTPException(
                status_code=400,
                detail="Garmin authentication failed. Check your email and password.",
            ) from exc
        except GarminRateLimitError as exc:
            raise HTTPException(
                status_code=503,
                detail="Garmin is temporarily rate-limiting this server. Please try again in a few minutes.",
            ) from exc
        except Exception as exc:
            logger.error("Garmin V2 login error: %s", type(exc).__name__)
            raise HTTPException(
                status_code=400,
                detail="Garmin authentication failed. Check your email and password.",
            ) from exc
    else:
        # V1: garth retry loop with fingerprint rotation
        n = len(FINGERPRINT_SEQUENCE)
        last_exc: Exception | None = None
        for attempt in range(n):
            fingerprint = FINGERPRINT_SEQUENCE[attempt]
            if attempt > 0:
                delay = random.uniform(30, 45)
                logger.info(
                    "Garmin login attempt %d/%d: waiting %.0fs before retry (Akamai delay)",
                    attempt + 1, n, delay,
                )
                await asyncio.sleep(delay)
            use_proxy = (attempt == n - 1) and bool(settings.fixie_url)
            client = create_login_client(fingerprint=fingerprint, proxy_url=settings.fixie_url if use_proxy else None)
            logger.info(
                "Garmin login attempt %d/%d: %s TLS%s",
                attempt + 1, n, fingerprint, " + Fixie proxy" if use_proxy else ", no proxy",
            )
            try:
                client.login(email, password)
                token_json: str = client.dumps()
                logger.info(
                    "Garmin login succeeded on attempt %d/%d (fingerprint=%s proxy=%s) for user_id=%s",
                    attempt + 1, n, fingerprint, use_proxy, current_user.id,
                )
                break
            except (requests.exceptions.HTTPError, cffi_requests.exceptions.HTTPError, GarthHTTPError) as exc:
                last_exc = exc
                response = getattr(exc, "response", None)
                if response is None:
                    response = getattr(getattr(exc, "__cause__", None), "response", None)
                if response is not None and response.status_code == 429:
                    logger.warning(
                        "Garmin SSO rate-limited (429) on attempt %d/%d — "
                        "Akamai blocked %s (proxy=%s)",
                        attempt + 1, n, fingerprint, use_proxy,
                    )
                    continue
                logger.error(
                    "Garmin login rejected (non-429) on attempt %d/%d: %s",
                    attempt + 1, n, type(exc).__name__,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Garmin authentication failed. Check your email and password.",
                ) from exc
            except cffi_requests.exceptions.ProxyError as exc:
                last_exc = exc
                logger.error(
                    "Garmin proxy unreachable on attempt %d/%d — check FIXIE_URL config",
                    attempt + 1, n,
                )
                raise HTTPException(
                    status_code=503,
                    detail="Garmin connection unavailable. Please try again later.",
                ) from exc
            except Exception as exc:
                last_exc = exc
                logger.error(
                    "Garmin login unexpected error on attempt %d/%d: %s",
                    attempt + 1, n, type(exc).__name__,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Garmin authentication failed. Check your email and password.",
                ) from exc
        else:
            logger.error(
                "Garmin login failed after all %d retries for user_id=%s — "
                "all fingerprints blocked. Check test_garmin_login.py.",
                n, current_user.id,
            )
            raise HTTPException(
                status_code=503,
                detail="Garmin is temporarily rate-limiting this server. Please try again in a few minutes.",
            ) from last_exc

    # Encrypt and store token + credentials for auto-reconnect
    logger.info("Storing encrypted Garmin token for user_id=%s", current_user.id)
    encrypted = encrypt_token(current_user.id, settings.garmincoach_secret_key, token_json)
    encrypted_cred = encrypt_credential(
        current_user.id, settings.garmin_credential_key, email, password
    )
    del email, password  # Discard credentials from memory after encryption

    profile = await _get_or_create_profile(current_user, session)
    profile.garmin_oauth_token_encrypted = encrypted
    profile.garmin_connected = True
    profile.garmin_credential_encrypted = encrypted_cred
    profile.garmin_credential_stored_at = datetime.now(timezone.utc).replace(tzinfo=None)
    profile.garmin_auth_version = auth_version
    session.add(profile)
    await session.commit()
    cache.invalidate(f"profile:{current_user.id}")
    client_cache.invalidate(current_user.id)

    # Clear exchange cooldown — fresh tokens don't need the 30-min pause
    from src.api.routers.sync import clear_exchange_cooldown
    clear_exchange_cooldown(current_user.id)

    logger.info("Garmin connected successfully for user_id=%s", current_user.id)
    return GarminStatusResponse(connected=True, credentials_stored=True)


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
    credentials_stored = (
        profile is not None
        and profile.garmin_credential_encrypted is not None
    )
    return GarminStatusResponse(connected=connected, credentials_stored=credentials_stored)


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
        profile.garmin_credential_encrypted = None
        profile.garmin_credential_stored_at = None
        session.add(profile)
        await session.commit()
        cache.invalidate(f"profile:{current_user.id}")
        client_cache.invalidate(current_user.id)

    return GarminStatusResponse(connected=False)
