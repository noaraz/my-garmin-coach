from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import GarminActivity
from src.garmin.adapter_protocol import GarminAdapterError

if TYPE_CHECKING:
    from src.services.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)

_CONCURRENCY = 5


class ExportService:
    async def build_export(
        self,
        session: AsyncSession,
        user_id: int,
        garmin: SyncOrchestrator,
        start: date,
        end: date,
    ) -> dict[str, Any]:
        result = await session.execute(
            select(GarminActivity)
            .where(GarminActivity.user_id == user_id)
            .where(GarminActivity.date >= start)
            .where(GarminActivity.date <= end)
            .order_by(GarminActivity.date)
        )
        activities = result.scalars().all()
        await session.close()

        sem = asyncio.Semaphore(_CONCURRENCY)

        async def fetch_one(act: GarminActivity) -> dict[str, Any]:
            async with sem:
                try:
                    summary, splits = await asyncio.gather(
                        asyncio.to_thread(garmin.get_activity, act.garmin_activity_id),
                        asyncio.to_thread(garmin.get_activity_splits, act.garmin_activity_id),
                    )
                    return {
                        "garmin_activity_id": act.garmin_activity_id,
                        "name": act.name,
                        "date": act.date.isoformat(),
                        "activity_type": act.activity_type,
                        "summary": summary,
                        "laps": splits,
                    }
                except GarminAdapterError as exc:
                    logger.warning("Export: failed to fetch %s: %s", act.garmin_activity_id, exc)
                    return {
                        "garmin_activity_id": act.garmin_activity_id,
                        "name": act.name,
                        "date": act.date.isoformat(),
                        "activity_type": act.activity_type,
                        "error": "fetch_failed",
                    }

        items = await asyncio.gather(*[fetch_one(a) for a in activities])

        return {
            "exported_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "activities": list(items),
        }


export_service = ExportService()
