# Workout Builder — CLAUDE

## WorkoutTemplate Data Integrity Rule (added 2026-03-24)

**`description` must always be derived from `steps`. Never set them independently.**

- `steps` (JSON) is the single source of truth for workout structure
- `description` (string, e.g. `"10m@Z1, 25m@Z2, 5m@Z3"`) is a human-readable cache computed from `steps`
- **Whenever `steps` is written, `description` must be recomputed and saved in the same operation**
- On the frontend: `generateDescription(steps)` in `frontend/src/utils/generateDescription.ts`
- On the backend: a Python equivalent is needed — do not save `steps` without also saving `description`
- The Garmin sync reads `template.description` directly — if it is stale or null, the wrong description is sent to the watch
- **Never write `steps` without writing `description`.** If you see code that does one without the other, that is a bug.

## Zone Color Mapping

```typescript
const ZONE_COLORS = {
  1: "#3B82F6",  // blue
  2: "#22C55E",  // green
  3: "#EAB308",  // yellow
  4: "#F97316",  // orange
  5: "#EF4444",  // red
};
```

## Nice-to-Have: AI Workout Creation (Future)

Reference: https://github.com/st3v/garmin-workouts-mcp

Could add "Describe your workout" text input that sends natural language to
Anthropic API → gets WorkoutStep JSON → loads into builder for review.
Not core — build after everything else works.
