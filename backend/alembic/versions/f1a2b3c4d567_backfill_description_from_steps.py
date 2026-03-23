"""backfill description from steps for WorkoutTemplate

Revision ID: f1a2b3c4d567
Revises: e6f3a0b2d891
Create Date: 2026-03-24 00:00:00.000000

Rule: description must always be derived from steps. This migration fixes
existing rows where steps is set but description is null.
"""
from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f1a2b3c4d567'
down_revision: Union[str, Sequence[str], None] = 'e6f3a0b2d891'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Inline port of generate_description (no app imports in migrations)
# ---------------------------------------------------------------------------

def _fmt_dur(step: dict) -> str:
    if step.get("duration_type") == "distance" and step.get("distance_m") is not None:
        km = step["distance_m"] / 1000
        return f"{int(km)}K" if km == int(km) else f"{km:.1f}K"
    if step.get("duration_sec") is not None:
        m = round(step["duration_sec"] / 60)
        return f"{m}m"
    return "?"


def _zone_label(step: dict) -> str:
    if step.get("target_type") == "hr_zone" and step.get("zone") is not None:
        return f"@Z{step['zone']}(HR)"
    if step.get("target_type") == "pace_zone" and step.get("zone") is not None:
        return f"@Z{step['zone']}"
    defaults = {"warmup": "@Z1", "interval": "@Z4", "recovery": "@Z1", "cooldown": "@Z1"}
    return defaults.get(step.get("type", ""), "")


def _step_desc(step: dict) -> str:
    return f"{_fmt_dur(step)}{_zone_label(step)}"


def _generate_description(steps: list[dict]) -> str:
    parts = []
    for step in steps:
        if step.get("type") == "repeat":
            inner = " + ".join(_step_desc(s) for s in step.get("steps", []))
            parts.append(f"{step.get('repeat_count', 1)}x ({inner})")
        else:
            parts.append(_step_desc(step))
    return ", ".join(parts)


def _description_from_steps_json(steps_json: str | None) -> str | None:
    if not steps_json:
        return None
    try:
        steps = json.loads(steps_json)
        if not isinstance(steps, list) or not steps:
            return None
        return _generate_description(steps)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


# ---------------------------------------------------------------------------

def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, steps FROM workouttemplate WHERE steps IS NOT NULL AND (description IS NULL OR description = '')")
    ).fetchall()

    for row in rows:
        desc = _description_from_steps_json(row.steps)
        if desc:
            conn.execute(
                sa.text("UPDATE workouttemplate SET description = :desc WHERE id = :id"),
                {"desc": desc, "id": row.id},
            )


def downgrade() -> None:
    # Description is derived data — downgrade is a no-op
    pass
