from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from src.db.models import AthleteProfile


def get_or_create_profile(session: Session) -> AthleteProfile:
    """Return the singleton profile (id=1), creating it if it doesn't exist."""
    profile = session.exec(select(AthleteProfile)).first()
    if profile is None:
        profile = AthleteProfile(name="Athlete")
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def update_profile(session: Session, data: dict) -> AthleteProfile:
    """Update the singleton profile with the provided fields."""
    profile = get_or_create_profile(session)

    changed_fields = set()
    for key, value in data.items():
        if value is not None and hasattr(profile, key):
            old_value = getattr(profile, key)
            if old_value != value:
                setattr(profile, key, value)
                changed_fields.add(key)

    profile.updated_at = datetime.utcnow()
    session.add(profile)
    session.commit()
    session.refresh(profile)

    # Trigger zone recalculation if threshold values changed
    if "lthr" in changed_fields or "threshold_pace" in changed_fields:
        from src.services.zone_service import recalculate_hr_zones, recalculate_pace_zones

        if "lthr" in changed_fields and profile.lthr:
            recalculate_hr_zones(session, profile)

        if "threshold_pace" in changed_fields and profile.threshold_pace:
            recalculate_pace_zones(session, profile)

    return profile
