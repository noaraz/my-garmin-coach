"""Fetch Garmin activity details + laps for a given date range.

Usage:
    python scripts/fetch_garmin_activity.py                    # today
    python scripts/fetch_garmin_activity.py 2026-04-16         # single date
    python scripts/fetch_garmin_activity.py 2026-04-12 2026-04-16  # range

Credentials are read from ../.env.prod (never hardcoded here).
Output: prints a summary + writes <date>.json and <date>.md to the repo root.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv(Path(__file__).parent.parent.parent / ".env.prod")

DB_URL = os.environ["DATABASE_URL"]
SECRET = os.environ["GARMINCOACH_SECRET_KEY"]
USER_ID = int(os.environ.get("GARMIN_USER_ID", "3"))


def fmt_pace(speed_ms: float | None) -> str:
    if not speed_ms:
        return "--"
    sec_per_km = 1000 / speed_ms
    return f"{int(sec_per_km // 60)}:{int(sec_per_km % 60):02d}/km"


def fmt_dur(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


async def _get_token() -> tuple[str, str]:
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT garmin_oauth_token_encrypted, garmin_auth_version "
                "FROM athleteprofile WHERE user_id = :uid"
            ),
            {"uid": USER_ID},
        )
        result = row.fetchone()
    await engine.dispose()
    return result[0], result[1] or "v1"


def _build_md(activities_data: list[dict]) -> str:
    lines: list[str] = ["# Garmin Activities\n"]
    for a in activities_data:
        s = a["summary"]
        lines += [
            f"## {a['name']}",
            f"**Date:** {a['start']}  ",
            f"**Distance:** {s.get('distance', 0) / 1000:.2f} km  ",
            f"**Duration:** {fmt_dur(s.get('duration', 0))}  ",
            f"**Avg Pace:** {fmt_pace(s.get('averageSpeed'))}  ",
            f"**Avg HR:** {s.get('averageHR', '?')} bpm | **Max HR:** {s.get('maxHR', '?')} bpm  ",
            f"**Cadence:** {round(s.get('averageRunCadence', 0))} spm  ",
            f"**Calories:** {s.get('calories', '?')}  ",
            f"**Elevation Gain:** {s.get('elevationGain', '?')} m  ",
            f"**Training Effect (aerobic):** {round(s.get('trainingEffect', 0), 1)}  ",
            f"**Anaerobic TE:** {round(s.get('anaerobicTrainingEffect', 0), 1)}  ",
            "",
            "### Laps",
            "| # | Dist | Time | Pace | Avg HR | Max HR | Cadence |",
            "|---|------|------|------|--------|--------|---------|",
        ]
        for i, lap in enumerate(a["laps"], 1):
            lines.append(
                f"| {i} | {lap.get('distance', 0) / 1000:.2f} km"
                f" | {fmt_dur(lap.get('duration', 0))}"
                f" | {fmt_pace(lap.get('averageSpeed'))}"
                f" | {lap.get('averageHR', '?')}"
                f" | {lap.get('maxHR', '?')}"
                f" | {round(lap.get('averageRunCadence', 0))} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = sys.argv[1:]
    today = date.today().isoformat()
    start_date = args[0] if args else today
    end_date = args[1] if len(args) > 1 else start_date

    from src.garmin.client_factory import create_adapter
    from src.garmin.encryption import decrypt_token

    encrypted, auth_version = asyncio.run(_get_token())
    adapter = create_adapter(decrypt_token(USER_ID, SECRET, encrypted), auth_version=auth_version)
    client = adapter._client

    raw_activities = adapter.get_activities_by_date(start_date, end_date)
    print(f"Found {len(raw_activities)} activit{'y' if len(raw_activities) == 1 else 'ies'} ({start_date} → {end_date})")

    if not raw_activities:
        print("Nothing to save.")
        return

    activities_data = []
    for act in raw_activities:
        aid = act["activityId"]
        details = client.get_activity(aid)
        try:
            laps = client.get_activity_splits(aid).get("lapDTOs", [])
        except Exception:
            laps = []

        s = details.get("summaryDTO", {})
        entry = {
            "activityId": aid,
            "name": details.get("activityName", act.get("activityName", "?")),
            "start": s.get("startTimeLocal", act.get("startTimeLocal", "?")),
            "summary": s,
            "laps": laps,
        }
        activities_data.append(entry)
        print(
            f"  {aid} | {entry['name']} | {entry['start']} | "
            f"{s.get('distance', 0) / 1000:.2f} km | {fmt_dur(s.get('duration', 0))} | "
            f"avg {fmt_pace(s.get('averageSpeed'))} | HR {s.get('averageHR', '?')}"
        )

    repo_root = Path(__file__).parent.parent.parent
    slug = start_date if start_date == end_date else f"{start_date}_{end_date}"
    json_path = repo_root / f"activities_{slug}.json"
    md_path = repo_root / f"activities_{slug}.md"

    json_path.write_text(json.dumps(activities_data, default=str, indent=2))
    md_path.write_text(_build_md(activities_data))

    print(f"\nSaved:\n  {json_path}\n  {md_path}")


if __name__ == "__main__":
    main()
