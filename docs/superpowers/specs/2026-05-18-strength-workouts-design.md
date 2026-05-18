# Strength Workouts — Design Spec

**Date**: 2026-05-18
**Status**: Draft
**Author**: brainstorming session

## 1. Summary

Add support for structured strength workouts in GarminCoach. Users author strength sessions through Plan Coach CSV import (the Gemini chat path stays running-only in v1). Sessions push to Garmin Connect as native `STRENGTH_TRAINING` workouts with mapped exercise enums, so the watch shows GIFs and tracks reps/sets during the session. Completed strength activities pair by same-day on the calendar.

Running plans and strength plans are independent: a user can have an active running plan AND an active strength plan concurrently. Re-importing one does not disturb the other.

## 2. Background

GarminCoach today is single-sport (running). Plan Coach produces `WorkoutTemplate` rows with a `steps` JSON that encodes warmup/repeat/cooldown intervals. The Garmin sync formatter converts these into `RUNNING` workout JSON.

**Reference points researched:**

- **TrainingPeaks** explicitly does NOT sync structured strength workouts to Garmin — only run/bike. Their integration documentation calls this out. So TrainingPeaks is not a model to copy for the sync path.
- **LiftTrack** and **Roxfit** are third-party apps that push structured `STRENGTH_TRAINING` workouts into Garmin Connect via the same workout-service endpoint we already use for running. Watch tracks reps natively; activity flows back as a generic strength activity (basic metadata only — Garmin restricts post-workout reps/weights from coming back to third parties).
- **Garmin Connect API** supports `STRENGTH_TRAINING` as a sport type with structured workout steps. Each step has `category` (≈30 enum values: `SQUAT`, `DEADLIFT`, `LUNGE`, `PLANK`, …) and `exerciseName` (e.g. `BARBELL_BACK_SQUAT`).
- **python-garminconnect 0.3.x** has no high-level helper for strength workouts. We push raw JSON via the existing `/workout-service/workout` endpoint already used for runs.

## 3. Goals

- Plan Coach authors strength sessions alongside running, in independent per-sport plans
- Strength templates push to Garmin Connect as structured workouts; watch shows GIFs and counts reps
- Completed strength activities auto-pair to the scheduled session by same-day
- Calendar + library + WorkoutDetailPanel render strength sessions clearly and distinctly from running
- Re-importing a strength plan does not touch the active running plan, and vice versa

## 4. Non-goals (deferred to "Nice to Have")

- Drag-drop authoring of strength workouts in Workout Builder
- Compliance scoring for completed strength sessions (Garmin doesn't return post-workout reps/weights)
- `%1RM`-based prescription and 1RM-per-exercise profile UI
- Bodybuilding/powerlifting catalog beyond the runner-focused list
- Mixed-sport single plan (one plan containing both running and strength sessions)

## 5. Design decisions

### 5.1 Data model

**`WorkoutTemplate.sport: 'run' | 'strength'`** — default `'run'` for back-compat. Templates are mono-sport, matching Garmin's `sportType` model.

**`TrainingPlan.sport: 'run' | 'strength'`** — default `'run'`. Active-plan uniqueness changes from `(user_id) WHERE status='active'` to `(user_id, sport) WHERE status='active'`. A user can have one active running plan and one active strength plan simultaneously.

**`steps` JSON: new step kind for strength.** A strength template's `steps` array is a flat list of `strength_exercise` items:

```json
{
  "kind": "strength_exercise",
  "exercise_key": "back_squat",
  "garmin_category": "SQUAT",
  "garmin_name": "BARBELL_BACK_SQUAT",
  "sets": [
    {"reps": 5, "load": {"type": "kg", "value": 80}, "rest_sec": 120},
    {"reps": 5, "load": {"type": "kg", "value": 80}, "rest_sec": 120},
    {"reps": 5, "load": {"type": "kg", "value": 80}, "rest_sec": 120}
  ],
  "note": null
}
```

Load types: `{"type": "kg", "value": N}`, `{"type": "rpe", "value": N}`, `{"type": "bodyweight"}`. Sets can also have `"duration_sec"` instead of `"reps"` (e.g. plank). Running templates keep their existing `warmup`/`repeat`/`cooldown` step shape — no migration of existing data.

**No new tables.** Reusing `WorkoutTemplate`, `TrainingPlan`, `ScheduledWorkout`. Adds two `sport` columns + one unique-constraint change. The Gemini chat path (and `PlanCoachMessage`) is out of scope — strength sessions are authored via CSV only in v1.

**Migration sequence** (single alembic revision, runs against SQLite dev + Neon Postgres prod):

1. Add `sport VARCHAR(16) NOT NULL DEFAULT 'run'` to `workouttemplate` and `trainingplan` (each in its own `op.add_column` inside `with op.batch_alter_table(...)` for SQLite-safety).
2. Drop the existing partial unique index/constraint on `trainingplan` (today: one active plan per user). Index name is captured from `alembic/versions/*` history at migration write time.
3. Create a new partial unique index `ix_trainingplan_active_per_sport` on `(user_id, sport) WHERE status = 'active'`. Postgres supports partial indexes natively. SQLite supports them as of 3.8 (we require 3.30+ in prod). Use `op.create_index(..., postgresql_where=..., sqlite_where=...)` form so both dialects render correctly.
4. No data backfill needed — `DEFAULT 'run'` handles existing rows.

`render_as_batch=True` is already configured in `alembic/env.py` for SQLite (per root CLAUDE.md). Validated by the migration-validator agent before merge.

### 5.2 Exercise catalog

**New module** — `backend/src/garmin/exercise_catalog.py`:

```python
CATALOG: dict[str, tuple[str, str]] = {  # key → (garmin_category, garmin_name)
    "back_squat":              ("SQUAT", "BARBELL_BACK_SQUAT"),
    "front_squat":             ("SQUAT", "BARBELL_FRONT_SQUAT"),
    "goblet_squat":            ("SQUAT", "GOBLET_SQUAT"),
    "wall_sit":                ("SQUAT", "WALL_SIT"),
    "deadlift":                ("DEADLIFT", "BARBELL_DEADLIFT"),
    "romanian_deadlift":       ("DEADLIFT", "ROMANIAN_DEADLIFT"),
    "single_leg_rdl":          ("DEADLIFT", "SINGLE_LEG_ROMANIAN_DEADLIFT"),
    "walking_lunge":           ("LUNGE", "WALKING_LUNGE"),
    "reverse_lunge":           ("LUNGE", "REVERSE_LUNGE"),
    "bulgarian_split_squat":   ("LUNGE", "BULGARIAN_SPLIT_SQUAT"),
    "step_up":                 ("LUNGE", "STEP_UP"),
    "calf_raise":              ("CALF_RAISE", "STANDING_CALF_RAISE"),
    "single_leg_calf_raise":   ("CALF_RAISE", "SINGLE_LEG_CALF_RAISE"),
    "glute_bridge":            ("HIP_RAISE", "GLUTE_BRIDGE"),
    "hip_thrust":              ("HIP_RAISE", "BARBELL_HIP_THRUST"),
    "single_leg_glute_bridge": ("HIP_RAISE", "SINGLE_LEG_GLUTE_BRIDGE"),
    "front_plank":             ("PLANK", "FRONT_PLANK"),
    "side_plank":              ("PLANK", "SIDE_PLANK"),
    "dead_bug":                ("CORE", "DEAD_BUG"),
    "bird_dog":                ("CORE", "BIRD_DOG"),
    "russian_twist":           ("CORE", "RUSSIAN_TWIST"),
    "pushup":                  ("PUSH_UP", "PUSHUP"),
    "pullup":                  ("PULL_UP", "PULLUP"),
    "bent_over_row":           ("ROW", "BARBELL_BENT_OVER_ROW"),
    "dumbbell_row":            ("ROW", "DUMBBELL_ROW"),
    "overhead_press":          ("SHOULDER_PRESS", "BARBELL_OVERHEAD_PRESS"),
    "box_jump":                ("PLYO", "BOX_JUMP"),
    "broad_jump":              ("PLYO", "BROAD_JUMP"),
    "clamshell":               ("HIP_STABILITY", "CLAMSHELL"),
    "monster_walk":            ("HIP_STABILITY", "BANDED_MONSTER_WALK"),
}

ALIASES: dict[str, str] = {  # lowercased input → catalog key
    "squat": "back_squat",
    "barbell squat": "back_squat",
    "rdl": "romanian_deadlift",
    "romanian dl": "romanian_deadlift",
    "lunge": "walking_lunge",
    "lunges": "walking_lunge",
    "split squat": "bulgarian_split_squat",
    "bulgarian": "bulgarian_split_squat",
    "plank": "front_plank",
    "side planks": "side_plank",
    "hip thrust": "hip_thrust",
    "thrusts": "hip_thrust",
    "bridge": "glute_bridge",
    "calves": "calf_raise",
    "push up": "pushup",
    "push-up": "pushup",
    "pull up": "pullup",
    "pull-up": "pullup",
    "row": "bent_over_row",
    "press": "overhead_press",
    "ohp": "overhead_press",
}
```

~30 entries chosen to cover the strength work runners actually do. The catalog module exposes a single resolver: `resolve(name: str) -> tuple[str, str] | None`, which lowercases, strips whitespace, then looks up first in `ALIASES`, then in `CATALOG` keys directly. Returns `None` for unknown names. The parser handles the `None` case by emitting a structured `unknown_exercise` validation error — there is no fallback substitution. Unknown exercises block import (Error, not Warn); the user must edit the CSV or pick a known name from the catalog reference.

**Boundary assertion**: `exercise_catalog.py` contains the dicts and the `resolve()` function only. No parsing, no string-tokenizing, no error-construction. The parser imports the resolver; the catalog module never imports the parser.

### 5.3 Grammar (CSV + chat)

Inline shorthand parsed to the `steps` JSON above. CSV-only in v1 — no chat path.

**Formal grammar (EBNF):**

```
strength_session  := exercise_block ( ";" SP* exercise_block )*
exercise_block    := exercise_name SP+ sets_spec [ "@" load ]
exercise_name     := WORD ( SP WORD )*                       (* matched greedily against catalog + aliases via longest-prefix; remaining tokens belong to sets_spec *)
sets_spec         := INT "x" rep_or_duration                  (* uniform sets *)
                  | INT "x" rep_or_duration "@" load_list     (* uniform reps, variable load *)
rep_or_duration   := INT                                      (* reps, no unit *)
                  | INT "s"                                   (* duration in seconds *)
load              := INT "kg"
                  | "RPE" INT
                  | "bw"
load_list         := load ( "," load ){1,}                    (* one per set; count must equal INT in sets_spec *)
```

**Disambiguation rules:**
- A trailing `s` on the rep token means seconds (duration). `3x5` = 3 sets of 5 reps. `3x45s` = 3 sets of 45 seconds.
- No `@load` allowed on duration steps (planks etc. — Garmin's strength workout JSON encodes timed steps with an implicit bodyweight load).
- No `@load` on reps-mode is an Error (`load_required`). Bodyweight exercises must be explicit: `3x10@bw`.
- Whitespace is required between exercise name and sets_spec but otherwise free; load tokens are case-insensitive.

**Per-set variance (in scope for v1):** `Squat 3x5@60kg,70kg,80kg` — three sets of 5 reps at 60, 70, 80 kg. Load-list count must match sets count, else `load_count_mismatch` Error. This is what the WorkoutDetailPanel's per-set-chip layout (Section 5.6) renders. RPE and bw are also valid in a load_list: `Front Squat 3x5@60kg,RPE7,RPE8`.

**Example CSV cell:**
```
Squat 3x5@80kg; RDL 3x8@RPE8; Walking Lunge 3x10@bw; Plank 3x45s; Front Squat 3x5@60kg,70kg,80kg
```

**Parser**: pure function in `plan_step_parser.py`, zero I/O, 95%+ unit coverage. Returns either a list of `strength_exercise` step dicts or a list of structured per-exercise errors: `unknown_exercise`, `unparseable_load`, `load_required`, `load_count_mismatch`, `duration_with_load`. Catalog lookup goes through `exercise_catalog.resolve()` — the parser does not duplicate the catalog logic.

### 5.4 Plan-coach pipeline

- `plan_step_parser.py` — extended with a `parse_strength_steps(text: str)` function. Existing running parser unchanged.
- `plan_import_service.py` — `validate()` and `commit()` take a `sport` parameter; queries scope to that sport.
- `POST /api/v1/plans/validate` and `POST /api/v1/plans/{id}/commit` accept `sport: 'run' | 'strength'` in the request body.
- `GET /api/v1/plans/active?sport=strength` returns the active strength plan or 204.
- **Gemini chat is out of scope.** Strength sessions are authored via CSV upload only. The chat tab in plan-coach remains running-only; the strength tab has CSV import only.

### 5.5 Garmin sync

**Push.** New `format_strength_workout(template)` in `backend/src/garmin/formatter.py`. Returns a Garmin workout dict with:

```json
{
  "workoutName": "Lower body strength",
  "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
    "workoutSteps": [
      {
        "type": "RepetitionGroupDTO",
        "stepOrder": 1,
        "numberOfIterations": 3,
        "workoutSteps": [
          {
            "type": "ExecutableStepDTO",
            "stepType": {"stepTypeKey": "interval", "stepTypeId": 3},
            "category": "SQUAT",
            "exerciseName": "BARBELL_BACK_SQUAT",
            "weightValue": 80,
            "weightUnit": {"unitKey": "kilogram"},
            "endCondition": {"conditionTypeKey": "reps"},
            "endConditionValue": 5
          },
          {
            "type": "ExecutableStepDTO",
            "stepType": {"stepTypeKey": "rest", "stepTypeId": 5},
            "endCondition": {"conditionTypeKey": "time"},
            "endConditionValue": 120
          }
        ]
      }
    ]
  }]
}
```

`SyncOrchestrator.push_workout()` branches on `template.sport`:
- `'run'` → existing `format_run_workout()`
- `'strength'` → `format_strength_workout()`

**V1 vs V2 adapter handling.** The strength JSON is POSTed to the same `/workout-service/workout` endpoint that running workouts use — Garmin's workout service is a single endpoint that accepts any `sportType`. Both adapters (V1 garth, V2 garminconnect 0.3.x) make raw HTTP calls and are sport-agnostic: they receive a dict and POST it. Neither adapter needs structural changes for strength.

The `WorkoutFacade` (the version-aware formatter bridge — see `2026-04-14-garminconnect-03x-migration-design.md`) is extended with one new method, `format_strength(template) -> dict`, which both adapter versions call. Implementation delegates to `format_strength_workout()` for both V1 and V2 — they produce identical JSON because Garmin's API is the same regardless of which auth path was used to obtain the session.

**Failure modes.** If Garmin rejects a strength workout JSON (4xx), the `sync_status` is set to `failed` with the response body logged. No silent fallback. This is the same handling as running workout failures today.

**Pull / pair.** `match_activities()` in the sync orchestrator is extended:
- For activities where `activityType.typeKey == 'strength_training'`, find a same-day `ScheduledWorkout` with `sport='strength'` and `completed=False`.
- If exactly one match, pair (set `activity_id`, mark `completed=True`).
- No compliance scoring (Garmin doesn't surface post-workout sets/reps to third parties — confirmed by LiftTrack/Roxfit precedent).
- Same calendar cleanup pattern as runs: after pairing, best-effort delete the planned Garmin workout from the calendar so the watch shows only the activity.

### 5.6 UI

**Calendar card** (selected: Option A from brainstorming visuals).
Strength workouts use a purple sport stripe (`#a855f7`) on the left edge of the card, distinct from running's zone-colored stripes. Card body shows `<title>` and `<exercise count> · <estimated duration>`. Same component (`WorkoutCard`) with a sport-aware stripe-color helper.

**WorkoutDetailPanel — strength view** (selected: Option C, hybrid layout).
- Header: purple "Strength" tag, title, date, exercise count, estimated duration
- Body: one row per exercise
  - When all sets within an exercise are identical: compact summary `3 × 5 @ 80kg`
  - When sets vary (pyramid, top-set + back-offs): per-set chips `60 · 70 · 80 kg`
- Same panel works at desktop (slide-out) and mobile (bottom sheet) widths
- "Sync to Garmin" button reuses the existing handler

**Plan Coach UI**: two-tab switcher at the top of `/plan-coach`:
- "Running" tab → existing flow, unchanged behavior (CSV + Gemini chat both available)
- "Strength" tab → strength CSV grammar reference, file upload, validation table. **No chat sub-tab in v1.**

**Validation row** (selected: Option B, exercise pills + Garmin-mapping disclosure).
- Each parsed exercise rendered as a pill: `<exercise name>  3×5 @ 80kg`
- Collapsible "Show Garmin mapping" disclosure exposes catalog matches: `Squat → SQUAT / BARBELL_BACK_SQUAT`, `RDL → DEADLIFT / ROMANIAN_DEADLIFT`, etc.
- Catalog-unknown exercises render with an error tint and an Error-level message: `"Nordic Curl" not in catalog — edit the row or pick a known exercise`. Import is blocked until the user fixes the row (consistent with Section 5.2: no fallback substitution).
- Parse errors render with Error-level row state and a specific message (`unparseable_load`, `load_required`, `load_count_mismatch`, `duration_with_load`).

**Mobile.** Calendar card and WorkoutDetailPanel both support mobile (bottom sheet) layouts identical in structure to desktop, with smaller fonts and tighter padding. Plan-coach validation table is desktop-first for v1 (large tables on mobile are out of scope).

### 5.7 Independence of running and strength plans

Active-plan uniqueness is `(user_id, sport)`, not `(user_id)`. Concretely:

- `commit_plan(plan_id)` runs `UPDATE TrainingPlan SET status='superseded' WHERE user_id=? AND sport=? AND status='active'` — scoped to the same sport
- The diff view before commit compares the draft strength plan against the active **strength** plan only (or no diff if no active strength plan)
- Re-importing a strength plan touches only `ScheduledWorkout` rows belonging to strength plans for that user; running rows are not in the query result set
- Deleting an active plan deletes only its own `ScheduledWorkout` rows (and not the templates, matching existing behavior)

## 6. Phasing

Three feature branches, three small PRs:

### Phase 1 — Backend foundation (`feature/strength-backend`)
- New module: `exercise_catalog.py` with catalog + aliases
- `plan_step_parser.py`: add `parse_strength_steps()`
- `formatter.py`: add `format_strength_workout()`
- DB migration: add `sport` column to `WorkoutTemplate` and `TrainingPlan` (default `'run'`); change active-plan unique constraint
- API schema changes: `sport` parameter on validate/commit/active endpoints
- Tests: parser unit (catalog hits, aliases, errors), formatter unit (Garmin JSON shape), API integration (sport-scoped commit + diff)
- No UI changes; strength flow not reachable from frontend yet

### Phase 2 — Plan Coach UI (`feature/strength-plan-coach`)
- Tab switcher on `/plan-coach`: Running | Strength
- Strength CSV grammar reference card
- Strength validation table with exercise pills + Garmin-mapping disclosure
- RTL tests for tab switching, validation row rendering, catalog warnings
- Strength workouts now appear in the library after commit, but with placeholder calendar rendering

### Phase 3 — Calendar + Garmin sync (`feature/strength-calendar-sync`)
- Calendar card: purple sport stripe
- WorkoutDetailPanel: hybrid strength layout (compact + per-set chips on variance)
- Mobile bottom-sheet variant of the panel
- `SyncOrchestrator.push_workout()`: strength branch wired
- `match_activities()`: strength-training pairing path
- Calendar cleanup after pairing (best-effort delete planned workout)
- E2E test: author → commit → calendar shows card → sync → Garmin push call → pair on completion

Each PR ships independently; Phase 2 can be merged before Phase 3 since strength templates are usable in the library even without Garmin sync wired.

## 7. Risks and open questions

- **Garmin API drift.** Garmin doesn't publish a stable public spec for `STRENGTH_TRAINING` workout JSON; the shape is reverse-engineered from web UI behavior and community projects (LiftTrack, Roxfit). Mitigation: integration test against a Garmin sandbox account (already in place for running) gated on env var; fail loudly if Garmin returns 4xx so we can adapt fast.
- **Watch model coverage.** Older Garmin watches may not support structured strength workouts. Out of scope to detect device capability — if push succeeds, we assume the watch handles it; if the user reports their watch ignores the workout, that's documented as a known limitation.
- **Aliases drift.** Free-text exercise names in user-authored CSVs may not match aliases reliably. Mitigation: the CSV grammar reference shows the canonical names; validation step surfaces unknown names with Error-level feedback so the user must fix the row before committing.
- **Catalog completeness.** ~30 exercises will miss edge cases. Mitigation: structure makes adding entries trivial; first month after launch, log unknown-exercise warnings to find common gaps.
- **Mobile validation table.** Desktop-first for v1; if mobile usage of plan-coach is significant, the validation row may need a mobile-specific layout later.

## 8. References

- `features/plan-coach/CLAUDE.md` — existing plan-coach grammar and pipeline
- `features/garmin-sync/CLAUDE.md` — sync orchestrator, formatter, V1/V2 adapter pattern
- `docs/superpowers/specs/2026-03-17-plan-coach-design.md` — original plan-coach design
- `docs/superpowers/specs/2026-04-14-garminconnect-03x-migration-design.md` — adapter pattern
- Garmin Connect Developer Program — Training API reference (sport types, exercise categories)
- LiftTrack — https://lifttrackapp.com/ — reference implementation
