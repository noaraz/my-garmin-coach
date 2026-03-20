"""Pure step-spec parser for the Plan Coach feature.

Parses the step notation used in CSV imports and Gemini chat output:

    10m@Z1, 6x(400s@Z5 + 200s@Z1), 5m@Z1

Units:
    m  = minutes  (duration_type="time", value in seconds)
    s  = seconds  (duration_type="time", value in seconds)
    K  = km       (duration_type="distance", value in metres)

Zones:
    Z1–Z5  (pace zone numbers)

Returns a list of builder-compatible step dicts ready to be stored as JSON.
Raises StepParseError on any invalid input.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------

class StepParseError(ValueError):
    """Raised when a step spec cannot be parsed."""


# ---------------------------------------------------------------------------
# Regex atoms
# ---------------------------------------------------------------------------

# A single step token:  <value><unit>@Z<zone>
#   value: integer or decimal  (e.g. 10, 0.5, 400)
#   unit:  m | s | K
#   zone:  1-5
_STEP_RE = re.compile(
    r"(?P<value>[0-9]+(?:\.[0-9]+)?)(?P<unit>[msK])@Z(?P<zone>[1-5])",
    re.IGNORECASE,
)

# Repeat group:  <count>x(<inner>)
_REPEAT_RE = re.compile(
    r"(?P<count>[0-9]+)[xX]\((?P<inner>[^)]+)\)",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_single_step(token: str) -> dict:
    """Parse one step token like '10m@Z2' or '2K@Z1'."""
    token = token.strip()
    m = _STEP_RE.fullmatch(token)
    if m is None:
        raise StepParseError(
            f"Invalid step '{token}'. "
            "Expected format: <value><unit>@Z<zone> where unit is m/s/K and zone is 1-5."
        )
    value = float(m.group("value"))
    unit = m.group("unit")
    zone = int(m.group("zone"))

    if unit == "m":
        return {
            "type": "active",
            "duration_type": "time",
            "duration_sec": value * 60,
            "zone": zone,
        }
    elif unit == "s":
        return {
            "type": "active",
            "duration_type": "time",
            "duration_sec": value,
            "zone": zone,
        }
    else:  # K
        return {
            "type": "active",
            "duration_type": "distance",
            "duration_distance_m": value * 1000,
            "zone": zone,
        }


def _parse_repeat(count: int, inner: str) -> dict:
    """Parse the inside of a repeat group: 'step1 + step2 + ...'"""
    inner_tokens = [t.strip() for t in inner.split("+")]
    steps = []
    for tok in inner_tokens:
        tok = tok.strip()
        if not tok:
            continue
        steps.append(_parse_single_step(tok))
    if not steps:
        raise StepParseError(f"Empty repeat group: {count}x()")
    return {
        "type": "repeat",
        "repeat_count": count,
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_steps_spec(spec: str) -> list[dict]:
    """Parse a steps spec string into a list of builder-compatible step dicts.

    Args:
        spec: e.g. "10m@Z1, 6x(400s@Z5 + 200s@Z1), 5m@Z1"

    Returns:
        List of step dicts (time-based, distance-based, or repeat groups).

    Raises:
        StepParseError: if any token is invalid.
    """
    if not spec or not spec.strip():
        raise StepParseError("Step spec must not be empty.")

    # Tokenise: split on commas that are not inside parentheses
    tokens = _split_top_level(spec)

    steps = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Try repeat group first
        rm = _REPEAT_RE.fullmatch(token)
        if rm:
            count = int(rm.group("count"))
            if count < 1:
                raise StepParseError(f"Repeat count must be ≥ 1, got: {count}")
            inner = rm.group("inner")
            steps.append(_parse_repeat(count, inner))
            continue

        # Single step
        steps.append(_parse_single_step(token))

    if not steps:
        raise StepParseError(f"No valid steps found in spec: '{spec}'")

    return steps


def _split_top_level(spec: str) -> list[str]:
    """Split spec on commas that are outside parentheses."""
    tokens: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in spec:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            if depth < 0:
                raise StepParseError(f"Unmatched ')' in spec: '{spec}'")
            current.append(ch)
        elif ch == "," and depth == 0:
            tokens.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if depth != 0:
        raise StepParseError(f"Unmatched '(' in spec: '{spec}'")
    tokens.append("".join(current).strip())
    return tokens
