# Garmin Activity Fetch — Feature Plan

## Overview
Fetch running activity data from Garmin Connect, auto-match to scheduled workouts,
and display TrainingPeaks-style compliance colors on the calendar.

## Design Spec
See `docs/superpowers/specs/2026-03-19-garmin-activity-fetch-design.md`

## Implementation Plan
See `docs/superpowers/plans/2026-03-19-garmin-activity-fetch.md`

## Scope
- New `GarminActivity` DB table + alembic migration
- `ActivityFetchService` for fetch/dedup/match
- Extract `GarminAdapter` to shared module
- Bidirectional sync (push workouts + fetch activities)
- Calendar API returns `CalendarResponse` wrapper with unplanned activities
- Compliance colors on WorkoutCard (green/yellow/red/grey)
- Manual pair/unpair and reschedule actions
- Auto-sync on calendar page mount
- Cleanup: delete Garmin scheduled workout from Garmin's calendar after pairing (idempotent sweep in `sync_all` + best-effort in `pair_activity`)
