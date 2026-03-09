from __future__ import annotations

import json
from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile, HRZone, PaceZone
from src.repositories.zones import hr_zone_repository, pace_zone_repository
from src.zone_engine.hr_zones import HRZoneCalculator
from src.zone_engine.models import ZoneConfig
from src.zone_engine.pace_zones import PaceZoneCalculator


class ZoneService:
    async def get_hr_zones(self, session: AsyncSession, profile_id: int) -> list[HRZone]:
        return await hr_zone_repository.get_by_profile(session, profile_id)

    async def get_pace_zones(self, session: AsyncSession, profile_id: int) -> list[PaceZone]:
        return await pace_zone_repository.get_by_profile(session, profile_id)

    async def recalculate_hr_zones(
        self, session: AsyncSession, profile: AthleteProfile
    ) -> list[HRZone]:
        """Recalculate HR zones from LTHR (Coggan), then cascade re-resolve."""
        if not profile.lthr:
            return []

        config = ZoneConfig(threshold=float(profile.lthr), method="coggan")
        zone_set = HRZoneCalculator(config).calculate()

        await hr_zone_repository.delete_by_profile(session, profile.id)

        new_zones: list[HRZone] = []
        for z in zone_set.zones:
            hr_zone = HRZone(
                profile_id=profile.id,
                zone_number=z.zone_number,
                name=z.name,
                lower_bpm=z.lower,
                upper_bpm=z.upper,
                calculation_method="coggan",
                pct_lower=z.pct_lower,
                pct_upper=z.pct_upper,
            )
            session.add(hr_zone)
            new_zones.append(hr_zone)
        await session.commit()

        await self._cascade_re_resolve(session, profile.id, profile.user_id)
        return new_zones

    async def recalculate_pace_zones(
        self, session: AsyncSession, profile: AthleteProfile
    ) -> list[PaceZone]:
        """Recalculate pace zones from threshold_pace, then cascade re-resolve."""
        if not profile.threshold_pace:
            return []

        config = ZoneConfig(threshold=float(profile.threshold_pace), method="pct_threshold")
        zone_set = PaceZoneCalculator(config).calculate()

        await pace_zone_repository.delete_by_profile(session, profile.id)

        new_zones: list[PaceZone] = []
        for z in zone_set.zones:
            pace_zone = PaceZone(
                profile_id=profile.id,
                zone_number=z.zone_number,
                name=z.name,
                lower_pace=z.lower,
                upper_pace=z.upper,
                calculation_method="pct_threshold",
                pct_lower=z.pct_lower,
                pct_upper=z.pct_upper,
            )
            session.add(pace_zone)
            new_zones.append(pace_zone)
        await session.commit()

        await self._cascade_re_resolve(session, profile.id, profile.user_id)
        return new_zones

    async def set_hr_zones(
        self, session: AsyncSession, profile_id: int, user_id: int, zones_data: list[dict]
    ) -> list[HRZone]:
        """Replace all HR zones for a profile with custom values."""
        await hr_zone_repository.delete_by_profile(session, profile_id)

        new_zones: list[HRZone] = []
        for data in zones_data:
            hr_zone = HRZone(
                profile_id=profile_id,
                zone_number=data["zone_number"],
                name=data["name"],
                lower_bpm=data["lower_bpm"],
                upper_bpm=data["upper_bpm"],
                calculation_method=data.get("calculation_method", "custom"),
                pct_lower=data["pct_lower"],
                pct_upper=data["pct_upper"],
            )
            session.add(hr_zone)
            new_zones.append(hr_zone)
        await session.commit()

        await self._cascade_re_resolve(session, profile_id, user_id)
        return new_zones

    async def _cascade_re_resolve(self, session: AsyncSession, profile_id: int, user_id: int) -> None:
        """Re-resolve all unfinished ScheduledWorkouts after zone change.

        Includes past workouts (not just future ones) so that a workout scheduled
        for today or yesterday is also re-queued.  Completed workouts are excluded.
        """
        from src.db.models import WorkoutTemplate
        from src.repositories.calendar import scheduled_workout_repository
        from src.workout_resolver.models import WorkoutStep
        from src.workout_resolver.resolver import resolve_workout

        hr_zones_db = await hr_zone_repository.get_by_profile(session, profile_id)
        pace_zones_db = await pace_zone_repository.get_by_profile(session, profile_id)

        hr_zone_map: dict[int, tuple[float, float]] = {
            z.zone_number: (z.lower_bpm, z.upper_bpm) for z in hr_zones_db
        }
        pace_zone_map: dict[int, tuple[float, float]] = {
            z.zone_number: (z.lower_pace, z.upper_pace) for z in pace_zones_db
        }

        future_workouts = await scheduled_workout_repository.get_all_incomplete(session, user_id)

        for sw in future_workouts:
            if sw.workout_template_id is None:
                continue
            template = await session.get(WorkoutTemplate, sw.workout_template_id)
            if template is None or not template.steps:
                continue

            raw_steps = json.loads(template.steps)
            try:
                steps = [WorkoutStep.model_validate(s) for s in raw_steps]
                resolved = resolve_workout(
                    steps, hr_zones=hr_zone_map, pace_zones=pace_zone_map
                )
                sw.resolved_steps = json.dumps([r.model_dump() for r in resolved])
            except Exception:  # noqa: BLE001
                # Builder-format steps can't be validated by WorkoutStep.
                # Leave resolved_steps as None so the sync fallback re-translates
                # them on-the-fly using the freshly calculated zone maps.
                sw.resolved_steps = None

            # Always mark modified so the next sync re-pushes with fresh zone maps.
            sw.sync_status = "modified"
            sw.updated_at = datetime.utcnow()
            session.add(sw)

        await session.commit()


zone_service = ZoneService()

# ---------------------------------------------------------------------------
# Module-level shims for backward compatibility with existing router imports
# ---------------------------------------------------------------------------


async def get_hr_zones(session: AsyncSession, profile_id: int) -> list[HRZone]:
    return await zone_service.get_hr_zones(session, profile_id)


async def get_pace_zones(session: AsyncSession, profile_id: int) -> list[PaceZone]:
    return await zone_service.get_pace_zones(session, profile_id)


async def recalculate_hr_zones(session: AsyncSession, profile: AthleteProfile) -> list[HRZone]:
    return await zone_service.recalculate_hr_zones(session, profile)


async def recalculate_pace_zones(
    session: AsyncSession, profile: AthleteProfile
) -> list[PaceZone]:
    return await zone_service.recalculate_pace_zones(session, profile)


async def set_hr_zones(
    session: AsyncSession, profile_id: int, user_id: int, zones_data: list[dict]
) -> list[HRZone]:
    return await zone_service.set_hr_zones(session, profile_id, user_id, zones_data)
