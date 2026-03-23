---
name: api-contract-check
description: Audit Pydantic backend response schemas vs TypeScript frontend types.ts for field drift. Run after backend schema changes or before opening a PR to catch silent frontend/backend mismatches.
---

Compare backend API response models to frontend TypeScript types:

## 1. Find backend response schemas
Glob `backend/src/**/*.py` — look for Pydantic `BaseModel` subclasses in `schemas.py` files
and classes explicitly returned from route handlers (not internal models).

## 2. Read frontend types
Read `frontend/src/api/types.ts` — extract all TypeScript interfaces and type aliases.

## 3. Match and compare
For each backend response model, find the matching TS interface by name convention:
- `WorkoutTemplate` (Python) → `WorkoutTemplate` (TS)
- `ScheduledWorkout` (Python) → `ScheduledWorkout` (TS)
- `AthleteProfile` (Python) → `AthleteProfile` (TS)

Compare fields:
- Field in backend model **missing** from TS interface → `[MISSING IN TS]`
- Field in TS interface **not in** backend model → `[EXTRA IN TS]`
- `Optional[X]` backend field mapped to **required** TS field → `[NULL SAFETY BUG]`
- Type mismatch (e.g., backend `int` vs TS `string`) → `[TYPE MISMATCH]`

## 4. Output
One line per finding:
```
[SEVERITY] ModelName.field_name — description
```

If no drift: `"No schema drift detected."`

## Notes
- Skip models not returned from API routes (internal service models, DB models)
- Focus on response schemas — request schemas (inputs) are less critical for runtime safety
- `Optional[str]` in Python → `string | null` in TS (both optional AND nullable)
- Python `datetime` → TS `string` (ISO format) — this is expected, not a mismatch
