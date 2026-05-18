# Strength Workouts Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured strength workouts to GarminCoach — authored via Plan Coach (CSV + chat), pushed to Garmin as native `STRENGTH_TRAINING` workouts, paired on completion by same-day, with independent active running and strength plans.

**Architecture:** Three feature branches shipped as separate small PRs. Phase 1 lays the backend foundation (catalog, parser, formatter, migration, API). Phase 2 wires the Plan Coach UI with a Running/Strength tab switcher. Phase 3 finishes the calendar card, the WorkoutDetailPanel strength view, and the Garmin sync push + pair paths.

**Tech Stack:** Python 3.11 + FastAPI + SQLModel + Alembic + python-garminconnect 0.3.x (V2) / garth 0.5.x (V1) on the backend. React 18 + TypeScript + Vitest + React Testing Library on the frontend.

**Reference spec:** `docs/superpowers/specs/2026-05-18-strength-workouts-design.md`. Read it before starting any task — every decision in this plan traces back to a section there.

**Conventions to follow (from root `CLAUDE.md`):**
- TDD: write the failing test first, run RED, implement, run GREEN, commit.
- Per-file commits with `test:`, `feat:`, `fix:`, or `refactor:` prefixes.
- Ruff (with `DTZ` rules — no `datetime.utcnow()`), type hints everywhere, no bare `except`.
- Never commit to `main`. Feature branches only.
- Update `STATUS.md` + `features/plan-coach/PLAN.md` (and `CLAUDE.md` files touched) before each PR opens.

---

## Chunk 1: Phase 1 — Backend foundation

**Branch:** `feature/strength-backend`

**Scope:** Catalog module, parser extension, formatter, DB migration, API schema changes. Strength flow is wired end-to-end at the API layer but not reachable from the frontend yet — so this PR ships safely without UI work.

**File map:**

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/src/garmin/exercise_catalog.py` | Create | `CATALOG`, `ALIASES`, and `resolve(name) -> tuple[str, str] | None` — single resolver, no I/O |
| `backend/src/services/plan_step_parser.py` | Modify | Add `parse_strength_steps(cell: str) -> ParsedStrength` — pure function, returns steps list or structured errors |
| `backend/src/garmin/formatter.py` | Modify | Add `format_strength_workout(template) -> dict` — pure formatter producing Garmin JSON |
| `backend/src/garmin/workout_facade.py` | Modify | Add `format_strength(template) -> dict` — delegates to formatter; same for V1 and V2 |
| `backend/src/db/models.py` | Modify | Add `sport` column to `WorkoutTemplate` and `TrainingPlan` |
| `backend/alembic/versions/<new>.py` | Create | Migration: add columns, swap active-plan unique index |
| `backend/src/services/plan_import_service.py` | Modify | Scope `validate()` / `commit()` / `get_active()` / `delete_plan()` by `sport` |
| `backend/src/api/routers/plans.py` | Modify | Accept `sport` in body + query string on validate, commit, active, delete |
| `backend/src/api/schemas.py` | Modify | Add `sport` to plan request/response models |
| `backend/tests/unit/test_exercise_catalog.py` | Create | Resolver hits, alias hits, lowercase, unknown returns None |
| `backend/tests/unit/test_plan_step_parser_strength.py` | Create | Grammar variants, error cases, EBNF coverage |
| `backend/tests/unit/test_garmin_formatter_strength.py` | Create | Garmin JSON shape, weight units, RPE/bw encoding, per-set variance |
| `backend/tests/integration/test_api_plans_strength.py` | Create | Sport-scoped validate/commit/active/delete; running plan untouched |

---

### Task 1.1: Project scaffolding — branch + STATUS

**Files:**
- Modify: `STATUS.md`
- Modify: `features/plan-coach/PLAN.md`

- [ ] **Step 1: Confirm working in a worktree**

```bash
git rev-parse --show-toplevel
git branch --show-current
```
Expected: working tree is a worktree under `.claude/worktrees/strength-backend/` (or equivalent), branch is `feature/strength-backend`. If on `main`, create the branch first: `git checkout -b feature/strength-backend`.

- [ ] **Step 2: Add Strength entry to STATUS.md**

Open `STATUS.md`, add a new section under "In Progress":

```markdown
### Strength Workouts (Phase 1 — backend)
Spec: docs/superpowers/specs/2026-05-18-strength-workouts-design.md
Plan: docs/superpowers/plans/2026-05-18-strength-workouts.md
Branch: feature/strength-backend
```

- [ ] **Step 3: Reference plan from plan-coach PLAN.md**

Add a line near the top of `features/plan-coach/PLAN.md`:

```markdown
Strength extension: docs/superpowers/plans/2026-05-18-strength-workouts.md
```

- [ ] **Step 4: Commit**

```bash
git add STATUS.md features/plan-coach/PLAN.md
git commit -m "docs: scaffold strength workouts phase 1 status"
```

---

### Task 1.2: Exercise catalog module

**Files:**
- Create: `backend/src/garmin/exercise_catalog.py`
- Test: `backend/tests/unit/test_exercise_catalog.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_exercise_catalog.py
from src.garmin.exercise_catalog import resolve


class TestResolve:
    def test_resolve_returns_garmin_pair_for_catalog_key(self):
        assert resolve("back_squat") == ("SQUAT", "BARBELL_BACK_SQUAT")

    def test_resolve_is_case_insensitive(self):
        assert resolve("BACK_SQUAT") == ("SQUAT", "BARBELL_BACK_SQUAT")
        assert resolve("Back_Squat") == ("SQUAT", "BARBELL_BACK_SQUAT")

    def test_resolve_strips_whitespace(self):
        assert resolve("  back_squat  ") == ("SQUAT", "BARBELL_BACK_SQUAT")

    def test_resolve_handles_alias(self):
        assert resolve("squat") == ("SQUAT", "BARBELL_BACK_SQUAT")
        assert resolve("RDL") == ("DEADLIFT", "ROMANIAN_DEADLIFT")
        assert resolve("plank") == ("PLANK", "FRONT_PLANK")

    def test_resolve_handles_alias_with_spaces(self):
        assert resolve("split squat") == ("LUNGE", "BULGARIAN_SPLIT_SQUAT")
        assert resolve("hip thrust") == ("HIP_RAISE", "BARBELL_HIP_THRUST")

    def test_resolve_returns_none_for_unknown(self):
        assert resolve("nordic curl") is None
        assert resolve("") is None
        assert resolve("   ") is None
```

- [ ] **Step 2: Run tests → RED**

```bash
cd backend && .venv/bin/pytest tests/unit/test_exercise_catalog.py -v --no-cov
```
Expected: `ModuleNotFoundError: No module named 'src.garmin.exercise_catalog'`

- [ ] **Step 3: Implement `exercise_catalog.py`**

Use the full CATALOG + ALIASES dicts from spec Section 5.2 (lines 99-141 of the spec). The module exports exactly one function:

```python
# backend/src/garmin/exercise_catalog.py
from __future__ import annotations

CATALOG: dict[str, tuple[str, str]] = {
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

ALIASES: dict[str, str] = {
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


def resolve(name: str) -> tuple[str, str] | None:
    """Lookup an exercise by human input. Returns (garmin_category, garmin_name) or None."""
    if not name:
        return None
    key = name.strip().lower()
    if not key:
        return None
    if key in ALIASES:
        key = ALIASES[key]
    return CATALOG.get(key)
```

- [ ] **Step 4: Run tests → GREEN**

```bash
cd backend && .venv/bin/pytest tests/unit/test_exercise_catalog.py -v --no-cov
```
Expected: all tests pass.

- [ ] **Step 5: Verify lint clean**

```bash
cd backend && .venv/bin/ruff check src/garmin/exercise_catalog.py tests/unit/test_exercise_catalog.py
```
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add backend/src/garmin/exercise_catalog.py backend/tests/unit/test_exercise_catalog.py
git commit -m "feat: add exercise catalog with runner-focused mappings"
```

---

### Task 1.3: Parser — strength grammar

**Files:**
- Modify: `backend/src/services/plan_step_parser.py`
- Test: `backend/tests/unit/test_plan_step_parser_strength.py`

Reference: spec Section 5.3 (formal EBNF + disambiguation rules + error codes).

- [ ] **Step 1: Write the failing tests — uniform sets, simple cases**

```python
# backend/tests/unit/test_plan_step_parser_strength.py
from src.services.plan_step_parser import parse_strength_steps


class TestUniformSets:
    def test_single_exercise_kg(self):
        result = parse_strength_steps("Squat 3x5@80kg")
        assert result.errors == []
        assert len(result.steps) == 1
        step = result.steps[0]
        assert step["kind"] == "strength_exercise"
        assert step["exercise_key"] == "back_squat"
        assert step["garmin_category"] == "SQUAT"
        assert step["garmin_name"] == "BARBELL_BACK_SQUAT"
        assert step["sets"] == [
            {"reps": 5, "load": {"type": "kg", "value": 80}},
            {"reps": 5, "load": {"type": "kg", "value": 80}},
            {"reps": 5, "load": {"type": "kg", "value": 80}},
        ]

    def test_rpe_load(self):
        result = parse_strength_steps("RDL 3x8@RPE8")
        assert result.errors == []
        assert result.steps[0]["sets"][0]["load"] == {"type": "rpe", "value": 8}

    def test_bodyweight_load(self):
        result = parse_strength_steps("Walking Lunge 3x10@bw")
        assert result.errors == []
        assert result.steps[0]["sets"][0]["load"] == {"type": "bodyweight"}

    def test_duration_no_load(self):
        result = parse_strength_steps("Plank 3x45s")
        assert result.errors == []
        assert result.steps[0]["sets"] == [
            {"duration_sec": 45},
            {"duration_sec": 45},
            {"duration_sec": 45},
        ]
```

- [ ] **Step 2: Write the failing tests — multi-exercise + variance**

```python
class TestMultiExercise:
    def test_semicolon_separated(self):
        result = parse_strength_steps("Squat 3x5@80kg; RDL 3x8@RPE8; Plank 3x45s")
        assert result.errors == []
        assert len(result.steps) == 3
        assert result.steps[0]["exercise_key"] == "back_squat"
        assert result.steps[1]["exercise_key"] == "romanian_deadlift"
        assert result.steps[2]["exercise_key"] == "front_plank"


class TestPerSetVariance:
    def test_kg_variance(self):
        result = parse_strength_steps("Squat 3x5@60kg,70kg,80kg")
        assert result.errors == []
        assert [s["load"] for s in result.steps[0]["sets"]] == [
            {"type": "kg", "value": 60},
            {"type": "kg", "value": 70},
            {"type": "kg", "value": 80},
        ]

    def test_mixed_variance(self):
        result = parse_strength_steps("Front Squat 3x5@60kg,RPE7,RPE8")
        assert result.errors == []
        loads = [s["load"] for s in result.steps[0]["sets"]]
        assert loads == [
            {"type": "kg", "value": 60},
            {"type": "rpe", "value": 7},
            {"type": "rpe", "value": 8},
        ]
```

- [ ] **Step 3: Write the failing tests — error cases**

```python
class TestErrors:
    def test_unknown_exercise(self):
        result = parse_strength_steps("Nordic Curl 3x6@bw")
        assert result.steps == []
        assert any(e["code"] == "unknown_exercise" for e in result.errors)
        assert any("Nordic Curl" in e["message"] for e in result.errors)

    def test_unparseable_load(self):
        result = parse_strength_steps("Squat 3x5@???")
        assert any(e["code"] == "unparseable_load" for e in result.errors)

    def test_load_required(self):
        # no @load on reps mode is an error; bw must be explicit
        result = parse_strength_steps("Squat 3x5")
        assert any(e["code"] == "load_required" for e in result.errors)

    def test_load_count_mismatch(self):
        result = parse_strength_steps("Squat 3x5@60kg,70kg")  # 2 loads for 3 sets
        assert any(e["code"] == "load_count_mismatch" for e in result.errors)

    def test_duration_with_load(self):
        result = parse_strength_steps("Plank 3x45s@bw")
        assert any(e["code"] == "duration_with_load" for e in result.errors)
```

- [ ] **Step 4: Run tests → RED**

```bash
cd backend && .venv/bin/pytest tests/unit/test_plan_step_parser_strength.py -v --no-cov
```
Expected: `AttributeError` or `ImportError` — `parse_strength_steps` doesn't exist.

- [ ] **Step 5: Implement `parse_strength_steps`**

Open `backend/src/services/plan_step_parser.py`. Confirm `import re` is at the top of the file — add it if missing. Add at the bottom:

```python
from dataclasses import dataclass, field
from src.garmin.exercise_catalog import CATALOG, resolve

_REVERSE_CATALOG: dict[tuple[str, str], str] = {v: k for k, v in CATALOG.items()}

_SETS_RE = re.compile(r"^(?P<n>\d+)x(?P<rep>\d+)(?P<dur>s?)$", re.IGNORECASE)
_LOAD_KG_RE = re.compile(r"^(?P<v>\d+(?:\.\d+)?)kg$", re.IGNORECASE)
_LOAD_RPE_RE = re.compile(r"^RPE(?P<v>\d+(?:\.\d+)?)$", re.IGNORECASE)


@dataclass
class ParsedStrength:
    steps: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def _parse_load(token: str) -> dict | None:
    token = token.strip()
    if token.lower() == "bw":
        return {"type": "bodyweight"}
    if m := _LOAD_KG_RE.match(token):
        return {"type": "kg", "value": float(m["v"]) if "." in m["v"] else int(m["v"])}
    if m := _LOAD_RPE_RE.match(token):
        return {"type": "rpe", "value": float(m["v"]) if "." in m["v"] else int(m["v"])}
    return None


def _split_name_and_sets(block: str) -> tuple[str, str] | None:
    """Find the rightmost NxR or NxRs token; everything before is the exercise name."""
    tokens = block.strip().split()
    for i in range(len(tokens) - 1, -1, -1):
        if _SETS_RE.match(tokens[i]):
            name = " ".join(tokens[:i]).strip()
            sets_tail = " ".join(tokens[i:])
            if name:
                return name, sets_tail
    return None


def parse_strength_steps(cell: str) -> ParsedStrength:
    out = ParsedStrength()
    if not cell or not cell.strip():
        return out
    for raw_block in cell.split(";"):
        block = raw_block.strip()
        if not block:
            continue
        # Split exercise name from sets spec
        load_part = ""
        if "@" in block:
            head, load_part = block.split("@", 1)
            head = head.strip()
            load_part = load_part.strip()
        else:
            head = block
        split = _split_name_and_sets(head)
        if split is None:
            out.errors.append({"code": "unparseable", "message": f"Cannot parse '{block}'"})
            continue
        name, sets_tail = split
        # Sets count + reps/duration
        m = _SETS_RE.match(sets_tail)
        if not m:
            out.errors.append({"code": "unparseable", "message": f"Bad sets spec in '{block}'"})
            continue
        n_sets = int(m["n"])
        rep_n = int(m["rep"])
        is_duration = bool(m["dur"])
        # Resolve exercise
        catalog = resolve(name)
        if catalog is None:
            out.errors.append({"code": "unknown_exercise", "message": f'"{name}" not in catalog'})
            continue
        category, garmin_name = catalog
        # Loads
        if is_duration:
            if load_part:
                out.errors.append({"code": "duration_with_load", "message": f"Duration step cannot have load in '{block}'"})
                continue
            sets = [{"duration_sec": rep_n} for _ in range(n_sets)]
        else:
            if not load_part:
                out.errors.append({"code": "load_required", "message": f'"{name}" needs @load (kg, RPE, or bw)'})
                continue
            tokens = [t.strip() for t in load_part.split(",")]
            loads: list[dict] = []
            for tok in tokens:
                parsed = _parse_load(tok)
                if parsed is None:
                    out.errors.append({"code": "unparseable_load", "message": f'Cannot parse load "{tok}" on "{name}"'})
                    break
                loads.append(parsed)
            else:
                if len(loads) == 1:
                    sets = [{"reps": rep_n, "load": loads[0]} for _ in range(n_sets)]
                elif len(loads) == n_sets:
                    sets = [{"reps": rep_n, "load": ld} for ld in loads]
                else:
                    out.errors.append({"code": "load_count_mismatch",
                                       "message": f'"{name}" has {n_sets} sets but {len(loads)} loads'})
                    continue
            if any(e["code"] in {"unparseable_load"} for e in out.errors[-1:]):
                continue
        # Resolve catalog key for storage
        exercise_key = _REVERSE_CATALOG.get(catalog)
        out.steps.append({
            "kind": "strength_exercise",
            "exercise_key": exercise_key,
            "garmin_category": category,
            "garmin_name": garmin_name,
            "sets": sets,
            "note": None,
        })
    return out
```

- [ ] **Step 6: Run tests → GREEN**

```bash
cd backend && .venv/bin/pytest tests/unit/test_plan_step_parser_strength.py -v --no-cov
```
Expected: all tests pass. If anything fails, debug per failing case — do not modify the tests.

- [ ] **Step 7: Verify lint + type checks pass**

```bash
cd backend && .venv/bin/ruff check src/services/plan_step_parser.py tests/unit/test_plan_step_parser_strength.py
```
Expected: `All checks passed!`

- [ ] **Step 8: Commit**

```bash
git add backend/src/services/plan_step_parser.py backend/tests/unit/test_plan_step_parser_strength.py
git commit -m "feat: parse strength workout grammar with uniform and per-set variance"
```

---

### Task 1.4: Garmin strength formatter

**Files:**
- Modify: `backend/src/garmin/formatter.py`
- Test: `backend/tests/unit/test_garmin_formatter_strength.py`

Reference: spec Section 5.5 (Garmin JSON shape).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_garmin_formatter_strength.py
import pytest
from src.garmin.formatter import format_strength_workout


@pytest.fixture
def template():
    """Single-exercise template: 3x5 back squat @ 80kg."""
    class T:
        name = "Lower body strength"
        sport = "strength"
        steps = [
            {
                "kind": "strength_exercise",
                "exercise_key": "back_squat",
                "garmin_category": "SQUAT",
                "garmin_name": "BARBELL_BACK_SQUAT",
                "sets": [
                    {"reps": 5, "load": {"type": "kg", "value": 80}},
                    {"reps": 5, "load": {"type": "kg", "value": 80}},
                    {"reps": 5, "load": {"type": "kg", "value": 80}},
                ],
                "note": None,
            }
        ]
    return T()


class TestFormatStrengthWorkout:
    def test_top_level_sport_type(self, template):
        out = format_strength_workout(template)
        assert out["sportType"]["sportTypeKey"] == "strength_training"
        assert out["workoutName"] == "Lower body strength"

    def test_segment_sport_type(self, template):
        out = format_strength_workout(template)
        seg = out["workoutSegments"][0]
        assert seg["sportType"]["sportTypeKey"] == "strength_training"

    def test_uniform_sets_use_repetition_group(self, template):
        out = format_strength_workout(template)
        steps = out["workoutSegments"][0]["workoutSteps"]
        assert steps[0]["type"] == "RepetitionGroupDTO"
        assert steps[0]["numberOfIterations"] == 3
        inner = steps[0]["workoutSteps"][0]
        assert inner["category"] == "SQUAT"
        assert inner["exerciseName"] == "BARBELL_BACK_SQUAT"
        assert inner["weightValue"] == 80
        assert inner["weightUnit"]["unitKey"] == "kilogram"
        assert inner["endCondition"]["conditionTypeKey"] == "reps"
        assert inner["endConditionValue"] == 5

    def test_per_set_variance_emits_individual_steps(self):
        class T:
            name = "Front Squat Day"
            sport = "strength"
            steps = [{
                "kind": "strength_exercise",
                "exercise_key": "front_squat",
                "garmin_category": "SQUAT",
                "garmin_name": "BARBELL_FRONT_SQUAT",
                "sets": [
                    {"reps": 5, "load": {"type": "kg", "value": 60}},
                    {"reps": 5, "load": {"type": "kg", "value": 70}},
                    {"reps": 5, "load": {"type": "kg", "value": 80}},
                ],
                "note": None,
            }]
        out = format_strength_workout(T())
        steps = out["workoutSegments"][0]["workoutSteps"]
        # Variance → flat list of individual steps (not a repetition group)
        non_rest = [s for s in steps if s.get("stepType", {}).get("stepTypeKey") != "rest"]
        assert len(non_rest) == 3
        assert [s["weightValue"] for s in non_rest] == [60, 70, 80]

    def test_rpe_set_omits_weight(self):
        class T:
            name = "RPE day"
            sport = "strength"
            steps = [{
                "kind": "strength_exercise", "exercise_key": "romanian_deadlift",
                "garmin_category": "DEADLIFT", "garmin_name": "ROMANIAN_DEADLIFT",
                "sets": [{"reps": 8, "load": {"type": "rpe", "value": 8}}],
                "note": None,
            }]
        out = format_strength_workout(T())
        inner = out["workoutSegments"][0]["workoutSteps"][0]
        assert "weightValue" not in inner or inner.get("weightValue") is None
        # RPE value goes into a description/note field
        assert "RPE 8" in (inner.get("description") or "")

    def test_bodyweight_set_omits_weight(self):
        class T:
            name = "Lunge day"
            sport = "strength"
            steps = [{
                "kind": "strength_exercise", "exercise_key": "walking_lunge",
                "garmin_category": "LUNGE", "garmin_name": "WALKING_LUNGE",
                "sets": [{"reps": 10, "load": {"type": "bodyweight"}}],
                "note": None,
            }]
        out = format_strength_workout(T())
        inner = out["workoutSegments"][0]["workoutSteps"][0]
        assert inner.get("weightValue") in (None, 0)

    def test_duration_set_uses_time_condition(self):
        class T:
            name = "Plank day"
            sport = "strength"
            steps = [{
                "kind": "strength_exercise", "exercise_key": "front_plank",
                "garmin_category": "PLANK", "garmin_name": "FRONT_PLANK",
                "sets": [{"duration_sec": 45}, {"duration_sec": 45}, {"duration_sec": 45}],
                "note": None,
            }]
        out = format_strength_workout(T())
        inner = out["workoutSegments"][0]["workoutSteps"][0]["workoutSteps"][0]
        assert inner["endCondition"]["conditionTypeKey"] == "time"
        assert inner["endConditionValue"] == 45
```

- [ ] **Step 2: Run tests → RED**

```bash
cd backend && .venv/bin/pytest tests/unit/test_garmin_formatter_strength.py -v --no-cov
```
Expected: `ImportError: cannot import name 'format_strength_workout'`

- [ ] **Step 3: Implement `format_strength_workout` in `backend/src/garmin/formatter.py`**

Add at the bottom of the existing formatter module:

```python
_STRENGTH_SPORT_TYPE = {"sportTypeId": 5, "sportTypeKey": "strength_training"}
_INTERVAL_STEP = {"stepTypeId": 3, "stepTypeKey": "interval"}
_REST_STEP = {"stepTypeId": 5, "stepTypeKey": "rest"}


def _build_strength_step(exercise: dict, set_spec: dict, order: int) -> dict:
    """Build one Garmin ExecutableStepDTO from a parsed set."""
    step: dict = {
        "type": "ExecutableStepDTO",
        "stepOrder": order,
        "stepType": _INTERVAL_STEP,
        "category": exercise["garmin_category"],
        "exerciseName": exercise["garmin_name"],
    }
    if "duration_sec" in set_spec:
        step["endCondition"] = {"conditionTypeKey": "time"}
        step["endConditionValue"] = set_spec["duration_sec"]
        return step
    # Reps mode
    step["endCondition"] = {"conditionTypeKey": "reps"}
    step["endConditionValue"] = set_spec["reps"]
    load = set_spec.get("load") or {}
    if load.get("type") == "kg":
        step["weightValue"] = load["value"]
        step["weightUnit"] = {"unitKey": "kilogram"}
    elif load.get("type") == "rpe":
        step["description"] = f"RPE {load['value']}"
    # bodyweight: no weight fields
    return step


def format_strength_workout(template) -> dict:
    """Format a strength WorkoutTemplate into Garmin Connect JSON."""
    workout_steps: list[dict] = []
    order = 1
    for exercise in template.steps:
        if exercise["kind"] != "strength_exercise":
            continue
        sets = exercise["sets"]
        # Detect uniform sets → wrap in RepetitionGroupDTO
        uniform = len(sets) > 1 and all(s == sets[0] for s in sets)
        if uniform:
            inner = _build_strength_step(exercise, sets[0], 1)
            workout_steps.append({
                "type": "RepetitionGroupDTO",
                "stepOrder": order,
                "numberOfIterations": len(sets),
                "workoutSteps": [inner],
            })
            order += 1
        else:
            for set_spec in sets:
                workout_steps.append(_build_strength_step(exercise, set_spec, order))
                order += 1
    return {
        "workoutName": template.name,
        "sportType": _STRENGTH_SPORT_TYPE,
        "workoutSegments": [{
            "segmentOrder": 1,
            "sportType": _STRENGTH_SPORT_TYPE,
            "workoutSteps": workout_steps,
        }],
    }
```

- [ ] **Step 4: Run tests → GREEN**

```bash
cd backend && .venv/bin/pytest tests/unit/test_garmin_formatter_strength.py -v --no-cov
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/garmin/formatter.py backend/tests/unit/test_garmin_formatter_strength.py
git commit -m "feat: format strength workouts as Garmin STRENGTH_TRAINING JSON"
```

---

### Task 1.5: WorkoutFacade — strength path

**Files:**
- Modify: `backend/src/garmin/workout_facade.py`
- Test: extend an existing `tests/unit/test_workout_facade.py` (if it exists) or create one.

Reference: spec Section 5.5 — both V1 and V2 use the same formatter; no adapter-specific shaping needed.

- [ ] **Step 1: Inspect current WorkoutFacade**

```bash
grep -n "def format" backend/src/garmin/workout_facade.py
```

- [ ] **Step 2: Write the failing test**

```python
# Append to backend/tests/unit/test_workout_facade.py (create if missing)
from src.garmin.workout_facade import WorkoutFacade


def test_format_strength_returns_strength_training_sport_type():
    class T:
        name = "X"; sport = "strength"
        steps = [{
            "kind": "strength_exercise", "exercise_key": "back_squat",
            "garmin_category": "SQUAT", "garmin_name": "BARBELL_BACK_SQUAT",
            "sets": [{"reps": 5, "load": {"type": "kg", "value": 80}}],
            "note": None,
        }]
    facade = WorkoutFacade(version="v2")  # adjust ctor args to match existing
    out = facade.format_strength(T())
    assert out["sportType"]["sportTypeKey"] == "strength_training"


def test_v1_and_v2_produce_identical_strength_json():
    class T:
        name = "X"; sport = "strength"
        steps = [{
            "kind": "strength_exercise", "exercise_key": "back_squat",
            "garmin_category": "SQUAT", "garmin_name": "BARBELL_BACK_SQUAT",
            "sets": [{"reps": 5, "load": {"type": "kg", "value": 80}}],
            "note": None,
        }]
    v1 = WorkoutFacade(version="v1").format_strength(T())
    v2 = WorkoutFacade(version="v2").format_strength(T())
    assert v1 == v2
```

- [ ] **Step 3: Run tests → RED**

```bash
cd backend && .venv/bin/pytest tests/unit/test_workout_facade.py -v --no-cov
```

- [ ] **Step 4: Implement `format_strength` on WorkoutFacade**

In `workout_facade.py`:

```python
from src.garmin.formatter import format_strength_workout


class WorkoutFacade:
    # ... existing __init__ and format_run methods ...

    def format_strength(self, template) -> dict:
        """Format a strength template. Identical output for V1 and V2 — Garmin's
        workout-service endpoint is sport-agnostic at the HTTP layer."""
        return format_strength_workout(template)
```

- [ ] **Step 5: Run tests → GREEN**

```bash
cd backend && .venv/bin/pytest tests/unit/test_workout_facade.py -v --no-cov
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/garmin/workout_facade.py backend/tests/unit/test_workout_facade.py
git commit -m "feat: add strength path to WorkoutFacade (v1+v2 identical)"
```

---

### Task 1.6: DB models — add `sport` columns

**Files:**
- Modify: `backend/src/db/models.py`

Reference: spec Section 5.1.

- [ ] **Step 1: Inspect current models**

```bash
grep -n "class WorkoutTemplate\|class TrainingPlan\|class PlanCoachMessage" backend/src/db/models.py
```

- [ ] **Step 2: Add `sport` field to each model**

In each class, add (preserving the existing field order):

```python
sport: str = Field(default="run", max_length=16, index=True)
```

This applies to: `WorkoutTemplate` and `TrainingPlan` only. `PlanCoachMessage` is not touched — Gemini chat stays running-only in v1.

Update the active-plan uniqueness — if `TrainingPlan` has a `__table_args__` that defines the partial unique constraint, replace it with `(user_id, sport)` partial unique. Otherwise, the index is created in the migration only.

- [ ] **Step 3: Run model unit tests (sanity)**

```bash
cd backend && .venv/bin/pytest tests/unit/ -k "model" -v --no-cov
```
Expected: all existing model tests still pass — no behavioral change yet.

- [ ] **Step 4: Commit**

```bash
git add backend/src/db/models.py
git commit -m "feat: add sport column to plan + template + chat message models"
```

---

### Task 1.7: Alembic migration — sport columns + active-plan index swap

**Files:**
- Create: `backend/alembic/versions/<new-revision>_strength_sport.py`

Reference: spec Section 5.1 migration sequence (steps 1–4).

- [ ] **Step 1: Generate the migration**

```bash
cd backend && .venv/bin/alembic revision --autogenerate -m "strength_sport_columns_and_index"
```
Read the generated file. Confirm it contains the three `add_column` ops + the unique constraint swap. Manually remove any spurious unrelated drift (per root `CLAUDE.md` autogenerate-drift rule).

- [ ] **Step 2: Verify migration uses batch mode for SQLite**

The generated migration must use `with op.batch_alter_table(...):` for each `add_column`. If autogenerate emitted plain `op.add_column`, rewrite each block:

```python
def upgrade() -> None:
    with op.batch_alter_table("workouttemplate") as batch_op:
        batch_op.add_column(sa.Column("sport", sa.String(length=16), nullable=False, server_default="run"))
        batch_op.create_index("ix_workouttemplate_sport", ["sport"])
    with op.batch_alter_table("trainingplan") as batch_op:
        batch_op.add_column(sa.Column("sport", sa.String(length=16), nullable=False, server_default="run"))
        batch_op.create_index("ix_trainingplan_sport", ["sport"])

    # Swap active-plan uniqueness from (user_id) to (user_id, sport)
    # Drop old partial index (name comes from previous migration history)
    op.drop_index("ix_trainingplan_active_unique", table_name="trainingplan")
    # Create new partial unique index — dialect-aware
    op.create_index(
        "ix_trainingplan_active_per_sport",
        "trainingplan",
        ["user_id", "sport"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_trainingplan_active_per_sport", table_name="trainingplan")
    op.create_index(
        "ix_trainingplan_active_unique",
        "trainingplan",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    for table in ("trainingplan", "workouttemplate"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f"ix_{table}_sport")
            batch_op.drop_column("sport")
```

If the old index name is different, find it: `grep -n "ix_trainingplan" backend/alembic/versions/*.py`.

- [ ] **Step 3: Run migration-validator agent**

Dispatch the migration-validator agent (`.claude/agents/migration-validator.md`) on this file. Address any flagged issues before proceeding.

- [ ] **Step 4: Apply migration locally**

```bash
cd backend && .venv/bin/alembic upgrade head
.venv/bin/alembic current
```
Expected: shows the new revision as `(head)`.

- [ ] **Step 5: Verify schema with sqlite3 inspection**

```bash
sqlite3 /tmp/garmincoach-test.db ".schema trainingplan" 2>/dev/null || true
```
Expected: `sport VARCHAR(16) NOT NULL DEFAULT 'run'` visible. (If using in-memory test DB, skip this and rely on integration tests in Task 1.10.)

- [ ] **Step 6: Test downgrade then re-upgrade**

```bash
cd backend && .venv/bin/alembic downgrade -1
.venv/bin/alembic upgrade head
```
Expected: clean down + up.

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(db): add sport column + per-sport active plan index"
```

---

### Task 1.8: Plan import service — scope by sport

**Files:**
- Modify: `backend/src/services/plan_import_service.py`
- Test: add cases to `backend/tests/integration/test_api_plans_strength.py` (created in Task 1.10).

Reference: spec Section 5.4 and 5.7.

- [ ] **Step 1: Read current service signatures**

```bash
grep -n "def validate\|def commit\|def get_active\|def delete_plan\|def cleanup_stale_drafts" backend/src/services/plan_import_service.py
```

- [ ] **Step 2: Add `sport` parameter to each public method**

Default to `"run"` for back-compat. Every DB query that filters on `TrainingPlan.user_id` adds `AND sport = :sport`. The "supersede existing active plan" UPDATE adds `AND sport = :sport`. The draft cleanup query (deletes stale drafts older than N hours for the user) adds `AND sport = :sport`.

- [ ] **Step 3: Wire strength parsing into `validate()`**

In `validate()`, when `sport == "strength"`, route each CSV row through `parse_strength_steps()` (from `plan_step_parser.py`); when `sport == "run"`, keep existing parser. The output shape (template + scheduled workout) is the same.

- [ ] **Step 4: Set `sport` on every created row**

When `validate()` or `commit()` creates a `TrainingPlan`, `WorkoutTemplate`, or `ScheduledWorkout`, set `sport=sport` on each.

- [ ] **Step 5: Run any existing service tests**

```bash
cd backend && .venv/bin/pytest tests/integration/test_api_plans.py -v --no-cov
```
Expected: existing running tests still pass (default `sport='run'` keeps current behavior).

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/plan_import_service.py
git commit -m "feat(plan-coach): scope plan import service by sport"
```

---

### Task 1.9: API router + schemas — accept `sport`

**Files:**
- Modify: `backend/src/api/routers/plans.py`
- Modify: `backend/src/api/schemas.py`

Reference: spec Section 5.4.

- [ ] **Step 1: Add `sport` to request and response schemas**

In `schemas.py`, add `sport: Literal["run", "strength"] = "run"` to:
- `PlanValidateRequest`
- `PlanCommitRequest`
- `PlanResponse` (response model)

- [ ] **Step 2: Wire `sport` through router endpoints**

- `POST /api/v1/plans/validate` — read `sport` from body, pass to `validate(sport=...)`.
- `POST /api/v1/plans/{id}/commit` — read `sport` from body (or look it up on the `TrainingPlan` row by id; prefer the latter to avoid mismatch).
- `GET /api/v1/plans/active` — accept `sport` query param, default `"run"`.
- `DELETE /api/v1/plans/{id}` — no change (id is unique, sport is on the row).

- [ ] **Step 3: Verify existing API tests pass (defaults work)**

```bash
cd backend && .venv/bin/pytest tests/integration/test_api_plans.py -v --no-cov
```

- [ ] **Step 4: Commit**

```bash
git add backend/src/api/routers/plans.py backend/src/api/schemas.py
git commit -m "feat(api): accept sport on plan endpoints"
```

---

### Task 1.10: Integration tests — sport-scoped plan flow

**Files:**
- Create: `backend/tests/integration/test_api_plans_strength.py`

- [ ] **Step 1: Write the failing integration tests**

```python
# backend/tests/integration/test_api_plans_strength.py
# NOTE: Repo convention (root CLAUDE.md): asyncio_mode = "auto" is enabled in
# pyproject.toml, so class-based async tests run without @pytest.mark.asyncio.
# Do not add `import pytest` unless you need a fixture/marker — ruff F401 will
# flag it. Existing fixtures `client`, `auth_headers`, and `db_session` are
# defined in backend/tests/conftest.py and are auto-injected.
from httpx import AsyncClient


class TestStrengthPlanFlow:
    async def test_validate_strength_csv_creates_strength_draft(self, client: AsyncClient, auth_headers):
        csv = (
            "date,name,steps\n"
            "2026-06-01,Lower body,Squat 3x5@80kg; RDL 3x8@RPE8; Plank 3x45s\n"
        )
        r = await client.post(
            "/api/v1/plans/validate",
            json={"sport": "strength", "csv": csv},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["sport"] == "strength"
        assert len(body["rows"]) == 1
        assert body["rows"][0]["status"] == "valid"

    async def test_strength_validate_with_unknown_exercise_is_error(self, client, auth_headers):
        csv = "date,name,steps\n2026-06-01,X,Nordic Curl 3x6@bw\n"
        r = await client.post(
            "/api/v1/plans/validate",
            json={"sport": "strength", "csv": csv},
            headers=auth_headers,
        )
        assert r.status_code == 200
        row = r.json()["rows"][0]
        assert row["status"] == "error"
        assert any(e["code"] == "unknown_exercise" for e in row["errors"])

    async def test_commit_strength_plan_does_not_supersede_running_plan(
        self, client, auth_headers, db_session
    ):
        # Create + commit a running plan
        run_csv = "date,name,steps\n2026-06-01,Easy Run,45m@Z2\n"
        v = await client.post("/api/v1/plans/validate",
                              json={"sport": "run", "csv": run_csv},
                              headers=auth_headers)
        run_plan_id = v.json()["plan_id"]
        await client.post(f"/api/v1/plans/{run_plan_id}/commit",
                          json={"sport": "run"},
                          headers=auth_headers)

        # Create + commit a strength plan
        str_csv = "date,name,steps\n2026-06-02,Lower,Squat 3x5@80kg\n"
        v2 = await client.post("/api/v1/plans/validate",
                               json={"sport": "strength", "csv": str_csv},
                               headers=auth_headers)
        str_plan_id = v2.json()["plan_id"]
        await client.post(f"/api/v1/plans/{str_plan_id}/commit",
                          json={"sport": "strength"},
                          headers=auth_headers)

        # Both plans must be active
        run_active = await client.get("/api/v1/plans/active?sport=run", headers=auth_headers)
        str_active = await client.get("/api/v1/plans/active?sport=strength", headers=auth_headers)
        assert run_active.json()["id"] == run_plan_id
        assert str_active.json()["id"] == str_plan_id

    async def test_reimport_strength_supersedes_only_strength(self, client, auth_headers):
        # Commit initial strength plan
        csv1 = "date,name,steps\n2026-06-02,Lower,Squat 3x5@80kg\n"
        first_id = await _validate_and_commit(client, auth_headers, "strength", csv1)
        # Commit a replacement
        csv2 = "date,name,steps\n2026-06-09,Lower,Squat 3x5@85kg\n"
        second_id = await _validate_and_commit(client, auth_headers, "strength", csv2)
        # First plan is now superseded
        r = await client.get(f"/api/v1/plans/active?sport=strength", headers=auth_headers)
        assert r.json()["id"] == second_id


async def _validate_and_commit(client, auth_headers, sport, csv):
    v = await client.post("/api/v1/plans/validate",
                          json={"sport": sport, "csv": csv},
                          headers=auth_headers)
    plan_id = v.json()["plan_id"]
    await client.post(f"/api/v1/plans/{plan_id}/commit",
                      json={"sport": sport},
                      headers=auth_headers)
    return plan_id
```

- [ ] **Step 2: Run integration tests → RED**

```bash
cd backend && .venv/bin/pytest tests/integration/test_api_plans_strength.py -v --no-cov
```

- [ ] **Step 3: Fix any wiring gaps surfaced by the tests**

Common gaps:
- Validate response missing `sport` field — add to `PlanResponse`.
- Validate response missing per-row `errors` list — already exists for running, ensure same shape for strength.
- Active endpoint missing `sport` query param — added in Task 1.9, double-check default.

- [ ] **Step 4: Run integration tests → GREEN**

```bash
cd backend && .venv/bin/pytest tests/integration/test_api_plans_strength.py -v --no-cov
```

- [ ] **Step 5: Run full backend test suite + coverage**

```bash
cd backend && .venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing
```
Expected: all tests pass; new modules at ≥95% coverage (pure core) / ≥80% (service+API).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/integration/test_api_plans_strength.py
git commit -m "test: sport-scoped plan flow with independent run + strength plans"
```

---

### Task 1.11: Update plan-coach feature docs

**Files:**
- Modify: `features/plan-coach/CLAUDE.md`
- Modify: `features/plan-coach/PLAN.md`

- [ ] **Step 1: Document the strength grammar in plan-coach CLAUDE.md**

Add a new section "Strength Step Format" that references the spec for the canonical grammar but documents the concrete examples and error codes. Include the catalog module reference.

- [ ] **Step 2: Update plan-coach PLAN.md status**

Add a new section "Phase 5 — Strength workouts" with the three sub-phases. Mark Phase 5a (backend) as in-progress.

- [ ] **Step 3: Run the revise-claude-md skill on the plan-coach CLAUDE.md**

Per root `CLAUDE.md` workflow.

- [ ] **Step 4: Commit**

```bash
git add features/plan-coach/CLAUDE.md features/plan-coach/PLAN.md
git commit -m "docs(plan-coach): document strength grammar + phase 5 plan"
```

---

### Task 1.12: Open the Phase 1 PR

- [ ] **Step 1: Run final verification**

```bash
cd backend && .venv/bin/pytest tests/ --cov=src --cov-report=term-missing
.venv/bin/ruff check src/ tests/
```

- [ ] **Step 2: Push branch and open PR**

```bash
git push -u origin feature/strength-backend
gh pr create --title "feat(strength): backend foundation — catalog, parser, formatter, sport-scoped plans" --body "$(cat <<'EOF'
## Summary
- Adds `exercise_catalog.py` with ~30 runner-focused exercises mapped to Garmin enums
- Extends `plan_step_parser.py` with strength grammar (uniform + per-set variance, RPE, bw, duration)
- Adds `format_strength_workout()` to the Garmin formatter; wires `WorkoutFacade.format_strength` for V1+V2
- Migration: `sport` column on `WorkoutTemplate` and `TrainingPlan`; active-plan index becomes `(user_id, sport) WHERE status='active'`
- Plan import service + API endpoints accept `sport` parameter
- No UI changes — strength flow is reachable via API only; Phase 2 ships the UI

Spec: `docs/superpowers/specs/2026-05-18-strength-workouts-design.md`
Plan: `docs/superpowers/plans/2026-05-18-strength-workouts.md`

## Test plan
- [ ] `pytest tests/` green on PR build
- [ ] `alembic upgrade head` succeeds on Render preview DB
- [ ] Manual: hit `/api/v1/plans/validate` with `{"sport": "strength", "csv": "..."}` from a JWT-authed curl; verify response shape
- [ ] Manual: commit a strength plan, commit a running plan, confirm both `/api/v1/plans/active?sport=...` return their own
EOF
)"
```

---

## Chunk 2: Phase 2 — Plan Coach UI

**Branch:** `feature/strength-plan-coach`

**Scope:** Tab switcher (Running / Strength), strength CSV grammar reference, strength CSV import flow, validation row layout (exercise pills + Garmin-mapping disclosure — Option B from brainstorming). **No chat support for strength in v1** — Gemini chat stays running-only.

**File map:**

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/pages/PlanCoachPage.tsx` | Modify | Top-level Running/Strength tab switcher; sport state passed to child tabs |
| `frontend/src/components/plan-coach/StrengthImportTab.tsx` | Create | Strength CSV import flow (upload, validation table, commit) |
| `frontend/src/components/plan-coach/StrengthGrammarReference.tsx` | Create | Reference card showing strength shorthand examples + catalog list |
| `frontend/src/components/plan-coach/StrengthValidationRow.tsx` | Create | Per-row layout: exercise pills + collapsible Garmin mapping |
| `frontend/src/components/plan-coach/ValidationTable.tsx` | Modify | Branch row renderer by sport |
| `frontend/src/api/client.ts` | Modify | Add `sport` to validate / commit / getActivePlan / deletePlan calls |
| `frontend/src/api/types.ts` | Modify | Add `sport` to plan request/response types; add `StrengthExerciseStep` type |
| `frontend/src/pages/__tests__/PlanCoachPage.test.tsx` | Modify | Tab switching + sport routing tests |
| `frontend/src/components/plan-coach/__tests__/StrengthValidationRow.test.tsx` | Create | Pill rendering, mapping disclosure, error states |

---

### Task 2.1: Branch + STATUS update

- [ ] **Step 1: Create branch**

```bash
git checkout main && git pull
git checkout -b feature/strength-plan-coach
```

- [ ] **Step 2: Update STATUS.md to reflect Phase 2**

- [ ] **Step 3: Commit**

```bash
git add STATUS.md
git commit -m "docs: start strength workouts phase 2 (plan-coach UI)"
```

---

### Task 2.2: Frontend types — sport + StrengthExerciseStep

**Files:**
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: Add `sport` to plan types**

```typescript
export type Sport = 'run' | 'strength'

export interface PlanValidateRequest {
  sport: Sport
  csv: string
}

export interface PlanCommitRequest {
  sport: Sport
}

export interface StrengthExerciseStep {
  kind: 'strength_exercise'
  exercise_key: string
  garmin_category: string
  garmin_name: string
  sets: StrengthSet[]
  note: string | null
}

export interface StrengthSet {
  reps?: number
  duration_sec?: number
  load?: { type: 'kg'; value: number } | { type: 'rpe'; value: number } | { type: 'bodyweight' }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/types.ts
git commit -m "feat(frontend): add Sport + StrengthExerciseStep types"
```

---

### Task 2.3: API client — pass sport

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Update each plan-related call to accept and send `sport`**

```typescript
export async function validatePlan(req: PlanValidateRequest): Promise<PlanValidateResponse> { ... }
export async function commitPlan(planId: string, req: PlanCommitRequest): Promise<void> { ... }
export async function getActivePlan(sport: Sport = 'run'): Promise<PlanResponse | null> { ... }
```

`getActivePlan` returns `null` on 204; preserve existing handling.

- [ ] **Step 2: Run frontend tests (existing)**

```bash
cd frontend && npm test -- --run
```
Expected: all pass (defaults keep existing behavior).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(frontend): pass sport through plan API client"
```

---

### Task 2.4: Tab switcher on PlanCoachPage

**Files:**
- Modify: `frontend/src/pages/PlanCoachPage.tsx`
- Test: `frontend/src/pages/__tests__/PlanCoachPage.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import PlanCoachPage from '../PlanCoachPage'

describe('PlanCoachPage tab switcher', () => {
  it('renders Running tab by default', () => {
    render(<MemoryRouter><PlanCoachPage /></MemoryRouter>)
    const running = screen.getByRole('tab', { name: /running/i })
    expect(running).toHaveAttribute('aria-selected', 'true')
  })

  it('switches to Strength tab on click', () => {
    render(<MemoryRouter><PlanCoachPage /></MemoryRouter>)
    fireEvent.click(screen.getByRole('tab', { name: /strength/i }))
    expect(screen.getByRole('tab', { name: /strength/i })).toHaveAttribute('aria-selected', 'true')
    // Strength tab content marker:
    expect(screen.getByText(/strength shorthand|exercise catalog/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test → RED**

```bash
cd frontend && npm test -- --run PlanCoachPage
```

- [ ] **Step 3: Implement the tab UI**

Replace the current single-flow rendering on `PlanCoachPage` with a controlled `sport` state. The tab bar has two tabs: Running (existing flow), Strength (new). Use accessible tab semantics (`role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`).

```tsx
const [sport, setSport] = useState<Sport>('run')
// ...
<div role="tablist" className="...">
  <button role="tab" aria-selected={sport === 'run'} onClick={() => setSport('run')}>Running</button>
  <button role="tab" aria-selected={sport === 'strength'} onClick={() => setSport('strength')}>Strength</button>
</div>
{sport === 'run' ? <RunImportTab /> : <StrengthImportTab />}
```

- [ ] **Step 4: Test → GREEN**

```bash
cd frontend && npm test -- --run PlanCoachPage
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PlanCoachPage.tsx frontend/src/pages/__tests__/PlanCoachPage.test.tsx
git commit -m "feat(plan-coach): add Running/Strength tab switcher"
```

---

### Task 2.5: StrengthGrammarReference component

**Files:**
- Create: `frontend/src/components/plan-coach/StrengthGrammarReference.tsx`

- [ ] **Step 1: Implement the reference card**

Static content. Show:
- Shorthand examples: `Squat 3x5@80kg`, `RDL 3x8@RPE8`, `Plank 3x45s`, `Front Squat 3x5@60kg,70kg,80kg`
- Inline list of catalog keys grouped by Garmin category (Squat, Deadlift, Lunge, …)
- Visual style matches the existing running grammar reference card.

No tests required — pure static content rendered via snapshot test if existing pattern uses snapshots.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/plan-coach/StrengthGrammarReference.tsx
git commit -m "feat(plan-coach): strength grammar reference card"
```

---

### Task 2.6: StrengthValidationRow component (Option B layout)

**Files:**
- Create: `frontend/src/components/plan-coach/StrengthValidationRow.tsx`
- Test: `frontend/src/components/plan-coach/__tests__/StrengthValidationRow.test.tsx`

Reference: spec Section 5.6 — Option B (exercise pills + collapsible Garmin mapping).

- [ ] **Step 1: Write the failing tests**

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import StrengthValidationRow from '../StrengthValidationRow'

const validRow = {
  date: '2026-06-01',
  name: 'Lower body',
  status: 'valid' as const,
  steps: [
    { kind: 'strength_exercise', exercise_key: 'back_squat', garmin_category: 'SQUAT',
      garmin_name: 'BARBELL_BACK_SQUAT', sets: [/* 3 sets */], note: null },
    { kind: 'strength_exercise', exercise_key: 'romanian_deadlift', garmin_category: 'DEADLIFT',
      garmin_name: 'ROMANIAN_DEADLIFT', sets: [/* 3 sets */], note: null },
  ],
  errors: [],
}

describe('StrengthValidationRow', () => {
  it('renders one pill per exercise with summary', () => {
    render(<StrengthValidationRow row={validRow} />)
    expect(screen.getByText(/back squat|squat/i)).toBeInTheDocument()
    expect(screen.getByText(/RDL|romanian deadlift/i)).toBeInTheDocument()
  })

  it('reveals Garmin mapping on disclosure click', () => {
    render(<StrengthValidationRow row={validRow} />)
    fireEvent.click(screen.getByText(/show garmin mapping/i))
    expect(screen.getByText(/BARBELL_BACK_SQUAT/)).toBeInTheDocument()
    expect(screen.getByText(/ROMANIAN_DEADLIFT/)).toBeInTheDocument()
  })

  it('shows error state when unknown_exercise present', () => {
    const errorRow = {
      ...validRow, status: 'error' as const,
      errors: [{ code: 'unknown_exercise', message: '"Nordic Curl" not in catalog' }],
    }
    render(<StrengthValidationRow row={errorRow} />)
    expect(screen.getByText(/Nordic Curl/)).toBeInTheDocument()
    expect(screen.getByText(/edit the row|pick a known exercise/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests → RED**

```bash
cd frontend && npm test -- --run StrengthValidationRow
```

- [ ] **Step 3: Implement the component**

Use CSS variables only (per root CLAUDE.md color rules). Pills use `--bg-surface-2` background and `--text-primary`. Error rows use red text token. Pill content: `<exercise name>  3×5 @ 80kg` (or per-set chips when variance, mirroring the detail panel rendering — but compact). The "Show Garmin mapping" disclosure expands to a list of `name → CATEGORY / NAME` lines.

Reuse summarization logic from `frontend/src/utils/workoutStats.ts` if applicable; otherwise add a small `summarizeStrengthSets(sets) -> string` helper next to the component.

- [ ] **Step 4: Test → GREEN**

```bash
cd frontend && npm test -- --run StrengthValidationRow
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/plan-coach/StrengthValidationRow.tsx \
        frontend/src/components/plan-coach/__tests__/StrengthValidationRow.test.tsx
git commit -m "feat(plan-coach): strength validation row with pills + garmin mapping"
```

---

### Task 2.7: StrengthImportTab — wire everything together

**Files:**
- Create: `frontend/src/components/plan-coach/StrengthImportTab.tsx`

- [ ] **Step 1: Compose the tab**

- Top section: `<StrengthGrammarReference />`
- Middle: file upload + textarea CSV input
- Bottom: validation table rendering `StrengthValidationRow` per row
- Import button gated on `rows.every(r => r.status !== 'error')`
- All API calls pass `sport: 'strength'`

- [ ] **Step 2: Add an integration-style RTL test**

Upload a CSV (use `userEvent.upload`), wait for the validation table to render, assert pill content and Import button enablement.

- [ ] **Step 3: Run tests → GREEN, then commit**

```bash
git add frontend/src/components/plan-coach/StrengthImportTab.tsx
git commit -m "feat(plan-coach): wire StrengthImportTab end-to-end"
```

---

### Task 2.8: Update docs + open the Phase 2 PR

- [ ] **Step 1: Run full test suite + lint + build**

```bash
cd backend && .venv/bin/pytest tests/ -v --cov=src
cd ../frontend && npm test -- --run && npx tsc -b && npx vite build
```

- [ ] **Step 2: Run revise-claude-md skill on `features/plan-coach/CLAUDE.md`**

- [ ] **Step 3: Push + open PR**

```bash
git push -u origin feature/strength-plan-coach
gh pr create --title "feat(strength): plan-coach UI with Running/Strength tab switcher" --body "..."
```

---

## Chunk 3: Phase 3 — Calendar + Garmin sync

**Branch:** `feature/strength-calendar-sync`

**Scope:** Calendar card with purple stripe (Option A), WorkoutDetailPanel hybrid strength layout (Option C), `SyncOrchestrator` push branch, same-day strength activity pairing, calendar cleanup after pair.

**File map:**

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/components/calendar/WorkoutCard.tsx` | Modify | Sport-aware stripe color helper; pick purple for strength |
| `frontend/src/components/calendar/WorkoutDetailPanel.tsx` | Modify | Branch body renderer by sport; render strength sets hybrid |
| `frontend/src/components/calendar/StrengthExerciseRow.tsx` | Create | Compact summary vs per-set chips based on variance |
| `frontend/src/utils/workoutStats.ts` | Modify | Add `summarizeStrengthSets()` + `computeStrengthDuration()` |
| `backend/src/services/sync_orchestrator.py` | Modify | Branch push by template.sport; call `format_strength_workout` |
| `backend/src/services/sync_orchestrator.py` | Modify | `match_activities()` branch for `strength_training` activities |
| `backend/src/api/routers/calendar.py` | Modify | Strength template render fields in response |
| `backend/tests/integration/test_api_sync_strength.py` | Create | Push + pair + calendar cleanup end-to-end with mocked Garmin |
| `frontend/src/components/calendar/__tests__/WorkoutDetailPanel.strength.test.tsx` | Create | RTL — strength panel rendering, variance display |

---

### Task 3.1: Branch + STATUS

- [ ] **Step 1: Create branch**

```bash
git checkout main && git pull
git checkout -b feature/strength-calendar-sync
```

- [ ] **Step 2: Update STATUS.md to Phase 3**

- [ ] **Step 3: Commit**

```bash
git add STATUS.md
git commit -m "docs: start strength workouts phase 3 (calendar + sync)"
```

---

### Task 3.2: Calendar card — sport-aware stripe color

**Files:**
- Modify: `frontend/src/components/calendar/WorkoutCard.tsx`

- [ ] **Step 1: Add a sport→color helper**

```typescript
function stripeColorForSport(sport: Sport, zone?: number): string {
  if (sport === 'strength') return 'var(--color-strength)' // defined in index.css
  return zone ? `var(--color-zone-${zone})` : 'var(--zone-default)'
}
```

Add `--color-strength: #a855f7` (and a `[data-theme="light"]` variant if appropriate) to `frontend/src/index.css`.

- [ ] **Step 2: Snapshot test**

If existing pattern uses snapshots, update; otherwise add an RTL test asserting `style` contains `var(--color-strength)` for a strength card.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/calendar/WorkoutCard.tsx frontend/src/index.css
git commit -m "feat(calendar): purple sport stripe for strength workouts"
```

---

### Task 3.3: StrengthExerciseRow — hybrid set rendering

**Files:**
- Create: `frontend/src/components/calendar/StrengthExerciseRow.tsx`
- Test: same dir, `__tests__/StrengthExerciseRow.test.tsx`

Reference: spec Section 5.6 detail panel — Option C hybrid.

- [ ] **Step 1: Write the failing tests**

```typescript
describe('StrengthExerciseRow', () => {
  it('renders compact "3 × 5 @ 80kg" when all sets identical', () => { ... })
  it('renders per-set chips "60 · 70 · 80 kg" when kg varies', () => { ... })
  it('renders chip list with mixed types: "60kg · RPE7 · RPE8"', () => { ... })
  it('renders duration as "3 × 45s"', () => { ... })
})
```

- [ ] **Step 2: Implement**

```typescript
export function StrengthExerciseRow({ step }: { step: StrengthExerciseStep }) {
  const summary = summarizeStrengthSets(step.sets)  // shared helper
  return (
    <div className="ex-row">
      <div className="ex-name">{prettyName(step.exercise_key)}</div>
      <div className="ex-sets-line">{summary}</div>
    </div>
  )
}
```

`summarizeStrengthSets` lives in `workoutStats.ts` so the validation row can reuse it.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/calendar/StrengthExerciseRow.tsx \
        frontend/src/components/calendar/__tests__/StrengthExerciseRow.test.tsx \
        frontend/src/utils/workoutStats.ts
git commit -m "feat(calendar): strength exercise row with hybrid set rendering"
```

---

### Task 3.4: WorkoutDetailPanel — strength view

**Files:**
- Modify: `frontend/src/components/calendar/WorkoutDetailPanel.tsx`
- Test: `frontend/src/components/calendar/__tests__/WorkoutDetailPanel.strength.test.tsx`

- [ ] **Step 1: Write the failing test**

Mount the panel with a strength workout fixture, assert exercise rows render via `<StrengthExerciseRow>`, assert the purple "Strength" tag is present in the header, assert the Sync to Garmin button is wired.

- [ ] **Step 2: Branch the body renderer**

```tsx
{workout.sport === 'strength'
  ? workout.steps.map(s => <StrengthExerciseRow key={s.exercise_key} step={s} />)
  : <RunningStepsList steps={workout.steps} />}
```

- [ ] **Step 3: Test → GREEN, commit**

```bash
git add frontend/src/components/calendar/WorkoutDetailPanel.tsx \
        frontend/src/components/calendar/__tests__/WorkoutDetailPanel.strength.test.tsx
git commit -m "feat(calendar): WorkoutDetailPanel strength view"
```

---

### Task 3.4b: Mobile — TodayPage + bottom-sheet width

**Files:**
- Modify: `frontend/src/pages/TodayPage.tsx`
- Test: `frontend/src/pages/__tests__/TodayPage.strength.test.tsx`

TodayPage is the mobile equivalent of CalendarPage and lists today's workouts as cards. The same `WorkoutCard` component is used, so the purple stripe from Task 3.2 is inherited automatically. The detail panel renders as a bottom sheet at mobile widths (existing responsive behavior in `WorkoutDetailPanel`).

- [ ] **Step 1: RTL test that TodayPage renders a strength card**

```typescript
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TodayPage from '../TodayPage'

// Mock useCalendar to return a strength workout for today
// (see existing TodayPage tests for the mock pattern)

it('renders strength workout card with purple stripe at mobile width', () => {
  // Set viewport to mobile width (e.g. 375px)
  global.innerWidth = 375
  render(<MemoryRouter><TodayPage /></MemoryRouter>)
  const card = screen.getByText(/lower body/i).closest('[data-testid="workout-card"]')
  // Purple stripe via inline style or computed value
  expect(card?.querySelector('.stripe')).toHaveStyle({ background: expect.stringContaining('var(--color-strength)') })
})

it('opens WorkoutDetailPanel as bottom sheet on tap', () => {
  global.innerWidth = 375
  // ... fireEvent.click on the card, assert sheet visible with strength content
})
```

- [ ] **Step 2: Run test → RED, fix any TodayPage rendering gap**

Most likely no source change needed — `TodayPage` already iterates the calendar's workouts. The mobile bottom-sheet variant of `WorkoutDetailPanel` is the existing layout used at `<768px` widths. Confirm it shows strength exercise rows correctly (verified by the Task 3.4 tests already, just at desktop width).

- [ ] **Step 3: Test → GREEN, commit**

```bash
git add frontend/src/pages/TodayPage.tsx frontend/src/pages/__tests__/TodayPage.strength.test.tsx
git commit -m "feat(mobile): TodayPage renders strength workout cards"
```

---

### Task 3.5: Backend — push branch in SyncOrchestrator

**Files:**
- Modify: `backend/src/services/sync_orchestrator.py`
- Test: append to `backend/tests/integration/test_api_sync_strength.py` (created in Task 3.7)

- [ ] **Step 1: Branch by template.sport**

```python
if template.sport == "strength":
    payload = self.workout_facade.format_strength(template)
else:
    payload = self.workout_facade.format_run(template)
```

POST path is identical — both use the existing `/workout-service/workout` adapter method.

- [ ] **Step 2: Unit test the branching**

Use the existing mocked-adapter pattern from `backend/tests/fixtures/garmin_mocks.py`. Assert that pushing a strength template results in `format_strength` being called once, and the resulting payload has `sportType.sportTypeKey == "strength_training"`.

- [ ] **Step 3: Commit**

```bash
git add backend/src/services/sync_orchestrator.py
git commit -m "feat(sync): branch push by sport in SyncOrchestrator"
```

---

### Task 3.6: Backend — pair strength activities

**Files:**
- Modify: `backend/src/services/sync_orchestrator.py` (in `match_activities`)

- [ ] **Step 1: Inspect current match logic**

```bash
grep -n "def match_activities\|activityType" backend/src/services/sync_orchestrator.py
```

- [ ] **Step 2: Extend the matcher**

The predicate must read from `activityType.typeKey` exactly (Garmin's nested field). Do not infer from other fields.

```python
activity_type_key = activity.get("activityType", {}).get("typeKey")
if activity_type_key == "strength_training":
    matched = await session.exec(
        select(ScheduledWorkout)
        .where(
            ScheduledWorkout.user_id == user_id,
            ScheduledWorkout.sport == "strength",
            ScheduledWorkout.scheduled_date == activity_date,
            ScheduledWorkout.completed.is_(False),
        )
    )
    candidates = matched.all()
    if len(candidates) == 1:
        # Pair: set activity_id, mark completed, session.add(sw)
        sw = candidates[0]
        sw.activity_id = activity["activityId"]
        sw.completed = True
        session.add(sw)
    elif len(candidates) == 0:
        logger.info("strength_training activity on %s has no scheduled match for user %s",
                    activity_date, user_id)
    else:
        logger.warning("strength_training activity on %s has %d candidates for user %s — skipping pair",
                       activity_date, len(candidates), user_id)
```

Explicit handling of the 0-match and >1-match cases is required so behavior is observable in logs. Pairing is skipped (not best-guess) when ambiguous.

- [ ] **Step 3: Cleanup planned workout from Garmin calendar after pairing**

Mirror the existing running cleanup pattern documented in root `CLAUDE.md` ("Garmin Calendar Cleanup After Pairing" section) and the `_is_garmin_404` helper in `src/garmin/sync.py`. When pairing succeeds and the scheduled workout has a `garmin_workout_id`:

1. Best-effort `sync_service.delete_workout(garmin_workout_id)` — wrap in try/except.
2. On success, clear `sw.garmin_workout_id = None` and re-add to session.
3. On `_is_garmin_404(exc)` — also clear (workout already gone). Idempotent.
4. On any other exception — log warning, do NOT clear `garmin_workout_id`; preserve it for retry.

This must happen before the final `session.commit()` in the matcher's caller, not as a separate commit.

- [ ] **Step 4: Integration tests — pair + edge cases**

Create `backend/tests/integration/test_api_sync_strength.py`:

1. **Happy path**: seed a strength `ScheduledWorkout` for date D with `garmin_workout_id` set; mock Garmin activities to return a `strength_training` activity on date D; call `sync_all`; assert `completed=True`, `activity_id` set, `garmin_workout_id` cleared, `delete_workout` called once.
2. **No match**: same as above but no scheduled workout exists for that date. Assert no pairing happened, no exception raised.
3. **Ambiguous match**: seed two strength `ScheduledWorkout` rows for the same date. Assert neither is paired (log line emitted; both remain `completed=False`).
4. **Delete failure preserves garmin_workout_id**: happy path but mock `delete_workout` to raise a non-404 error. Assert pairing still succeeds (`completed=True`, `activity_id` set) but `garmin_workout_id` is preserved (not cleared).
5. **404 on delete clears garmin_workout_id**: mock `delete_workout` to raise a 404. Assert `garmin_workout_id` is cleared.

- [ ] **Step 5: Test → GREEN, commit**

```bash
git add backend/src/services/sync_orchestrator.py \
        backend/tests/integration/test_api_sync_strength.py
git commit -m "feat(sync): same-day pairing for strength_training activities"
```

---

### Task 3.7: End-to-end manual verification

Pre-deploy smoke test using local containers:

- [ ] **Step 1: Run backend + frontend locally**

```bash
docker compose up --build
```

- [ ] **Step 2: Generate a token (root CLAUDE.md helper)**

```bash
docker compose exec backend python3 -c "
from src.auth.jwt import create_access_token
print(create_access_token(user_id=1, email='test@example.com', is_admin=True))
"
```

- [ ] **Step 3: Hit `/plan-coach` → Strength tab → upload a CSV**

```csv
date,name,steps
2026-06-01,Lower body,Squat 3x5@80kg; RDL 3x8@RPE8; Plank 3x45s
2026-06-08,Lower body,Squat 3x5@85kg; RDL 3x8@RPE8; Plank 3x60s
```

- [ ] **Step 4: Verify validation rows render (Option B layout); commit plan**

- [ ] **Step 5: Confirm strength card appears on calendar with purple stripe; click → panel shows hybrid set rendering**

- [ ] **Step 6: Sync to Garmin (manual) — confirm workout appears on watch / Garmin Connect calendar**

If using a real Garmin account, gate this behind the env-flagged live test (see existing pattern in `features/garmin-sync/CLAUDE.md`). Otherwise the mocked integration test in Task 3.6 is the proof.

---

### Task 3.8: Open the Phase 3 PR

- [ ] **Step 1: Run all tests + lint + build**

```bash
cd backend && .venv/bin/pytest tests/ --cov=src
cd ../frontend && npm test -- --run && npx tsc -b && npx vite build
```

- [ ] **Step 2: Update STATUS.md to mark Strength workouts complete**

- [ ] **Step 3: Run revise-claude-md on touched CLAUDE.md files**

- [ ] **Step 4: Push + open PR with `[Render Preview]` in the title**

```bash
git push -u origin feature/strength-calendar-sync
gh pr create --title "feat(strength): calendar + Garmin sync [Render Preview]" --body "..."
```

- [ ] **Step 5: Verify Render preview deploy succeeds and the strength flow works end-to-end against the preview DB**
