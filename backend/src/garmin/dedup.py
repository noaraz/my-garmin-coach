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


def find_missing_from_garmin(
    db_garmin_ids: set[str],
    garmin_workouts: list[dict[str, Any]],
) -> set[str]:
    """Return DB garmin_workout_ids that no longer exist on Garmin.

    Compares the set of IDs our DB thinks are synced against the actual
    Garmin workout list.  Any DB ID not found on Garmin is returned —
    these workouts were externally deleted and need re-pushing.

    Args:
        db_garmin_ids: Set of garmin_workout_id values from ScheduledWorkouts
            with sync_status="synced".
        garmin_workouts: Raw list from Garmin ``get_workouts()`` API.

    Returns:
        Set of garmin_workout_id strings missing from Garmin.
    """
    garmin_ids = {str(gw.get("workoutId", "")) for gw in garmin_workouts}
    return db_garmin_ids - garmin_ids
