"""
unsynced_workouts.py — list all non-completed workouts that are not synced to Garmin.

Unsynced = sync_status is 'pending', 'modified', or 'failed' (not 'synced').
Completed workouts are excluded — their Garmin template is removed on pairing.

Run with:
    docker compose exec backend python scripts/unsynced_workouts.py

Options:
    --user-id N     Only show workouts for a specific user (default: all users)
    --future-only   Only show workouts dated today or later
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from sqlmodel import Session, create_engine, select

from src.core.config import get_settings
from src.db.models import ScheduledWorkout, WorkoutTemplate

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"

STATUS_COLOUR = {
    "pending": YELLOW,
    "modified": CYAN,
    "failed": RED,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="List unsynced Garmin workouts")
    parser.add_argument("--user-id", type=int, default=None, help="Filter by user ID")
    parser.add_argument(
        "--future-only",
        action="store_true",
        help="Only show workouts dated today or later",
    )
    args = parser.parse_args()

    settings = get_settings()
    db_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(db_url)

    today = datetime.now(timezone.utc).date()

    with Session(engine) as session:
        stmt = (
            select(ScheduledWorkout, WorkoutTemplate)
            .join(
                WorkoutTemplate,
                ScheduledWorkout.workout_template_id == WorkoutTemplate.id,
                isouter=True,
            )
            .where(ScheduledWorkout.completed == False)  # noqa: E712
            .where(ScheduledWorkout.sync_status != "synced")
            .order_by(ScheduledWorkout.user_id, ScheduledWorkout.date)
        )

        if args.user_id is not None:
            stmt = stmt.where(ScheduledWorkout.user_id == args.user_id)

        if args.future_only:
            stmt = stmt.where(ScheduledWorkout.date >= today)

        rows = session.exec(stmt).all()

    if not rows:
        print(f"{BOLD}No unsynced workouts found.{RESET}")
        return

    print(f"\n{BOLD}Unsynced workouts ({len(rows)} total){RESET}\n")
    print(f"{'Date':<14} {'Status':<10} {'Name':<35} {'User':>6}  {'SW ID':>6}")
    print("─" * 76)

    for sw, template in rows:
        colour = STATUS_COLOUR.get(sw.sync_status, DIM)
        name = template.name if template else "(no template)"
        print(
            f"{str(sw.date):<14} "
            f"{colour}{sw.sync_status:<10}{RESET} "
            f"{name:<35} "
            f"{DIM}{sw.user_id or '?':>6}{RESET}  "
            f"{DIM}{sw.id:>6}{RESET}"
        )

    print()
    counts: dict[str, int] = {}
    for sw, _ in rows:
        counts[sw.sync_status] = counts.get(sw.sync_status, 0) + 1
    for status, n in sorted(counts.items()):
        colour = STATUS_COLOUR.get(status, DIM)
        print(f"  {colour}{status}{RESET}: {n}")
    print()


if __name__ == "__main__":
    main()
