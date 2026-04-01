"""Garmin workout deduplication logic.

Pure functions for matching local workouts against Garmin Connect workouts
to prevent orphaned duplicates.
"""
from __future__ import annotations

from typing import Any


def find_matching_garmin_workout(
    workout_name: str,
    garmin_workouts: list[dict[str, Any]],
) -> str | None:
    """Find a Garmin workout matching by name (case-insensitive).

    Returns the workoutId string if a match is found, None otherwise.
    When multiple matches exist, returns the first one.
    """
    target = workout_name.lower()
    for gw in garmin_workouts:
        name = gw.get("workoutName", "")
        if isinstance(name, str) and name.lower() == target:
            return str(gw["workoutId"])
    return None


def find_orphaned_garmin_workouts(
    garmin_workouts: list[dict[str, Any]],
    known_garmin_ids: set[str],
    known_template_names: set[str],
) -> list[str]:
    """Find Garmin workout IDs that are orphaned but match our template names.

    An orphan is a Garmin workout whose ID is not tracked by any
    ScheduledWorkout in our DB, but whose name matches one of our
    WorkoutTemplate names — meaning it was likely created by us.

    User-created Garmin workouts (names not in our library) are never
    returned to avoid accidental deletion.

    Args:
        garmin_workouts: Raw list from Garmin ``get_workouts()`` API.
        known_garmin_ids: Set of garmin_workout_id values currently tracked in DB.
        known_template_names: Set of WorkoutTemplate.name values for this user.

    Returns:
        List of Garmin workoutId strings safe to delete.
    """
    name_lower_set = {n.lower() for n in known_template_names}
    orphans: list[str] = []
    for gw in garmin_workouts:
        gw_id = str(gw.get("workoutId", ""))
        gw_name = gw.get("workoutName", "")
        if not gw_id or gw_id in known_garmin_ids:
            continue
        if isinstance(gw_name, str) and gw_name.lower() in name_lower_set:
            orphans.append(gw_id)
    return orphans


def find_unscheduled_workouts(
    db_workouts: list[dict[str, str]],
    calendar_items: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Return DB workouts not scheduled on the Garmin calendar.

    Compares ``(garmin_workout_id, date)`` pairs from our DB against
    ``(workoutId, date)`` pairs from the Garmin calendar endpoint.
    A workout is "unscheduled" if its (ID, date) pair is not on the calendar.

    Args:
        db_workouts: List of dicts with ``garmin_workout_id`` (str) and
            ``date`` (str YYYY-MM-DD) from ScheduledWorkouts with
            sync_status="synced".
        calendar_items: Raw list from Garmin
            ``/calendar-service/year/{y}/month/{m}`` ``calendarItems``.

    Returns:
        Subset of *db_workouts* not found on the Garmin calendar.
    """
    scheduled: set[tuple[str, str]] = set()
    for item in calendar_items:
        wid = str(item.get("workoutId", ""))
        date = item.get("date", "")
        if wid and date:
            scheduled.add((wid, date))

    return [
        w for w in db_workouts
        if (w["garmin_workout_id"], w["date"]) not in scheduled
    ]
