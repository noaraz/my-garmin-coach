# Workout Resolver — CLAUDE

## Key Pattern

The resolver is a pure function: `(steps, hr_zones, pace_zones) → resolved_steps`.
Never mutate the original step — always create new objects.

## Gotchas

- Repeat groups: recursively resolve all children. Preserve repeat structure.
- Mixed targets in one workout: each step resolved independently per its target_type.
- If a step references a zone that doesn't exist, raise `WorkoutResolveError`
  with a clear message including the zone number and available range.
