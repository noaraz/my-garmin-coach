# Workout Resolver — PLAN

## Description

Converts zone-referenced workout steps into steps with absolute targets.
When a workout says "run at HR Zone 2", the resolver looks up zone 2's
boundaries (e.g. 142–156 bpm) and produces a step with those exact values.
Also estimates total duration and distance for a workout.

Pure functions with zero I/O. Depends on zone-engine for zone data structures.

Track progress in **STATUS.md**.

---

## Tasks

- [ ] Write `workout_resolver/models.py` — WorkoutStep + ResolvedStep (Pydantic)
- [ ] Write all tests in `test_workout_resolver.py` (see test table below)
- [ ] Run tests → confirm all RED
- [ ] Implement `workout_resolver/resolver.py` — resolve_step(), resolve_workout()
- [ ] Run tests → confirm all GREEN
- [ ] Write all tests in `test_workout_estimator.py` (see test table below)
- [ ] Run tests → confirm all RED
- [ ] Implement `workout_resolver/estimator.py` — estimate_duration(), estimate_distance()
- [ ] Run tests → confirm all GREEN

---

## Resolution Flow

```
WorkoutStep { target_type: "hr_zone", target_zone: 2 }
  + HRZones where zone 2 = [142, 156]
  → ResolvedStep { target_low: 142, target_high: 156 }
```

For repeat groups, recursively resolve all children.

---

## Tests

### test_workout_resolver.py

| Test | Given | Expect |
|------|-------|--------|
| `test_resolve_hr_zone_step` | hr_zone, zone=2, zones[2]=[142,156] | low=142, high=156 |
| `test_resolve_pace_zone_step` | pace_zone, zone=3, zones[3]=[280,300] | low=280, high=300 |
| `test_resolve_open_unchanged` | target_type="open" | passes through |
| `test_resolve_explicit_range_unchanged` | hr_range, low=140, high=155 | passes through |
| `test_resolve_repeat_children` | repeat(4x) with 2 zone-ref children | children resolved |
| `test_resolve_full_workout` | warmup+4x[interval(z4)+recovery(z1)]+cooldown | all resolved |
| `test_resolve_mixed_targets` | mix of hr_zone, pace_zone, open | each per type |
| `test_resolve_missing_zone_raises` | refs zone 6, only 5 exist | WorkoutResolveError |
| `test_resolve_returns_new_objects` | any resolve | original not mutated |

### test_workout_estimator.py

| Test | Given | Expect |
|------|-------|--------|
| `test_duration_simple` | 600s + 1800s + 300s | 2700s |
| `test_duration_with_repeats` | warmup 600s + 4x(300s+120s) + cooldown 300s | 2580s |
| `test_distance_simple` | 1000m + 8000m + 1000m | 10000m |
| `test_lap_button_returns_none` | lap_button step | duration=None |

---

## Data Model

### WorkoutStep (input)
```json
{
  "order": 1,
  "type": "warmup | active | recovery | rest | cooldown | repeat",
  "duration_type": "time | distance | lap_button",
  "duration_value": 600,
  "duration_unit": "seconds | meters",
  "target_type": "hr_zone | pace_zone | hr_range | pace_range | open",
  "target_zone": 2,
  "target_low": null,
  "target_high": null,
  "notes": "optional",
  "repeat_count": null,
  "steps": []
}
```

---

## Implementation Files

```
backend/src/workout_resolver/
  __init__.py
  models.py       # WorkoutStep, ResolvedStep
  resolver.py     # resolve_step(), resolve_workout()
  estimator.py    # estimate_duration(), estimate_distance()
  exceptions.py   # WorkoutResolveError
```
