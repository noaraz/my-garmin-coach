from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models import GarminActivity
from src.garmin.adapter_protocol import GarminAdapterError

logger = logging.getLogger(__name__)

_CONCURRENCY = 5


class ExportService:
    async def build_export(
        self,
        session: AsyncSession,
        user_id: int,
        garmin: Any,  # SyncOrchestrator — avoid circular import
        start: date,
        end: date,
    ) -> dict[str, Any]:
        """Build a JSON export of all activities in the given date range.

        Args:
            session: Database session
            user_id: User ID to filter activities
            garmin: SyncOrchestrator instance (has get_activity and get_activity_splits)
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            Dict with exported_at, date_range, and activities list.
            Each activity has summary and laps, or error: "fetch_failed" on failure.
        """
        result = await session.execute(
            select(GarminActivity)
            .where(GarminActivity.user_id == user_id)
            .where(GarminActivity.date >= start)
            .where(GarminActivity.date <= end)
            .order_by(GarminActivity.date)
        )
        activities = result.scalars().all()

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
