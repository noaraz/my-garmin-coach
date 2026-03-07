# Workout Builder — CLAUDE

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
