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
    # Replace spaces with underscores to match CATALOG keys
    key = key.replace(" ", "_")
    return CATALOG.get(key)
