"""
compare_garmin_workouts.py — Compare workouts on Garmin vs our DB.

Fetches all workout templates from Garmin Connect and all ScheduledWorkouts
from our DB, then outputs a side-by-side comparison table showing:
  - BOTH ✓       — workout exists in both (garmin_workout_id matches)
  - ONLY DB ✗    — DB says "synced" but Garmin doesn't have it (the bug)
  - ONLY DB (…)  — pending/modified/failed, expected not on Garmin yet
  - ONLY GARMIN  — exists on Garmin but not tracked in our DB

Run with:
    docker compose exec backend python scripts/compare_garmin_workouts.py
    cd backend && .venv/bin/python scripts/compare_garmin_workouts.py --future-only
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from sqlmodel import Session, create_engine, select  # noqa: E402

from src.core.config import get_settings  # noqa: E402
from src.db.models import AthleteProfile, ScheduledWorkout, WorkoutTemplate  # noqa: E402
from src.garmin.client_factory import create_api_client  # noqa: E402
from src.garmin.encryption import decrypt_token  # noqa: E402
from src.garmin.sync_service import GarminSyncService  # noqa: E402

# Terminal colours
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Garmin vs DB workouts")
    parser.add_argument("--user-id", type=int, default=1, help="User ID (default: 1)")
    parser.add_argument(
        "--future-only",
        action="store_true",
        help="Only show workouts dated today or later",
    )
    args = parser.parse_args()

    get_settings.cache_clear()
    settings = get_settings()
    db_url = (
        settings.database_url
        .replace("+aiosqlite", "")
        .replace("+asyncpg", "")
        .replace("ssl=require", "sslmode=require")
    )
    engine = create_engine(db_url)
    today = datetime.now(timezone.utc).date()

    # ── 1. Load DB workouts ──────────────────────────────────────────────
    with Session(engine) as session:
        stmt = (
            select(ScheduledWorkout, WorkoutTemplate)
            .join(
                WorkoutTemplate,
                ScheduledWorkout.workout_template_id == WorkoutTemplate.id,
                isouter=True,
            )
            .where(ScheduledWorkout.user_id == args.user_id)
            .where(ScheduledWorkout.completed == False)  # noqa: E712
            .order_by(ScheduledWorkout.date)
        )
        if args.future_only:
            stmt = stmt.where(ScheduledWorkout.date >= today)
        db_rows = session.exec(stmt).all()

        # ── 2. Get Garmin token ──────────────────────────────────────────
        profile = session.exec(
            select(AthleteProfile).where(AthleteProfile.user_id == args.user_id)
        ).first()

    if not profile or not profile.garmin_oauth_token_encrypted:
        print(f"{RED}No Garmin token found for user {args.user_id}.{RESET}")
        print("Connect Garmin in Settings first.")
        return

    # ── 3. Fetch Garmin workouts ─────────────────────────────────────────
    try:
        token_json = decrypt_token(
            user_id=args.user_id,
            secret=settings.garmincoach_secret_key,
            ciphertext=profile.garmin_oauth_token_encrypted,
        )
        adapter = create_api_client(token_json)
        sync_service = GarminSyncService(adapter)
        garmin_workouts = sync_service.get_workouts()
    except Exception as exc:
        print(f"{RED}Failed to fetch Garmin workouts: {type(exc).__name__}: {exc}{RESET}")
        return

    # ── 4. Build lookup maps ─────────────────────────────────────────────
    garmin_by_id: dict[str, dict] = {}
    for gw in garmin_workouts:
        gw_id = str(gw.get("workoutId", ""))
        if gw_id:
            garmin_by_id[gw_id] = gw

    # Track which Garmin IDs are matched to DB workouts
    matched_garmin_ids: set[str] = set()

    # ── 5. Build output rows ─────────────────────────────────────────────
    rows: list[tuple[str, str, str, str, str, str]] = []  # name, date, status, garmin_id, where, colour

    for sw, template in db_rows:
        name = template.name if template else "(no template)"
        date_str = str(sw.date)
        status = sw.sync_status
        gid = sw.garmin_workout_id or "—"

        if sw.garmin_workout_id and sw.garmin_workout_id in garmin_by_id:
            where = "BOTH ✓"
            colour = GREEN
            matched_garmin_ids.add(sw.garmin_workout_id)
        elif sw.sync_status == "synced":
            where = "ONLY DB ✗"
            colour = RED
        else:
            where = f"ONLY DB ({status})"
            colour = YELLOW

        rows.append((name, date_str, status, gid, where, colour))

    # Garmin-only workouts (not tracked in our DB)
    db_garmin_ids = {sw.garmin_workout_id for sw, _ in db_rows if sw.garmin_workout_id}
    for gw_id, gw in garmin_by_id.items():
        if gw_id not in db_garmin_ids:
            name = gw.get("workoutName", "(unknown)")
            rows.append((name, "—", "—", gw_id, "ONLY GARMIN", CYAN))

    # ── 6. Print table ───────────────────────────────────────────────────
    if not rows:
        print(f"{BOLD}No workouts found.{RESET}")
        return

    print(f"\n{BOLD}Garmin vs DB Comparison — user {args.user_id} ({len(rows)} workouts){RESET}\n")
    header = f"{'Name':<30} {'Date':<12} {'Status':<10} {'Garmin ID':<14} {'Where'}"
    print(header)
    print("─" * len(header.expandtabs()))

    # Sort: ONLY DB ✗ first, then ONLY GARMIN, then BOTH, then pending
    priority = {"ONLY DB ✗": 0, "ONLY GARMIN": 1}

    def sort_key(row: tuple) -> tuple:
        where = row[4]
        p = priority.get(where, 2)
        return (p, row[1])  # then by date

    for name, date_str, status, gid, where, colour in sorted(rows, key=sort_key):
        truncated_name = name[:28] + ".." if len(name) > 30 else name
        truncated_gid = gid[:12] + ".." if len(gid) > 14 else gid
        print(
            f"{truncated_name:<30} "
            f"{date_str:<12} "
            f"{status:<10} "
            f"{truncated_gid:<14} "
            f"{colour}{where}{RESET}"
        )

    # ── 7. Summary ───────────────────────────────────────────────────────
    counts: dict[str, int] = {}
    for *_, where, _ in rows:
        base = where.split(" (")[0] if "(" in where else where
        counts[base] = counts.get(base, 0) + 1

    print(f"\n{BOLD}Summary:{RESET}")
    colour_map = {"BOTH ✓": GREEN, "ONLY DB ✗": RED, "ONLY GARMIN": CYAN, "ONLY DB": YELLOW}
    for label, n in sorted(counts.items()):
        c = colour_map.get(label, DIM)
        print(f"  {c}{label}{RESET}: {n}")
    print()


if __name__ == "__main__":
    main()
