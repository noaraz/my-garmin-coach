"""strength_sport_columns_and_index

Revision ID: ac94d620adfe
Revises: h3b4c5d6e789
Create Date: 2026-05-18

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ac94d620adfe"
down_revision: str | Sequence[str] | None = "h3b4c5d6e789"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("workouttemplate") as batch_op:
        batch_op.add_column(
            sa.Column("sport", sa.String(length=16), nullable=False, server_default="run")
        )
        batch_op.create_index("ix_workouttemplate_sport", ["sport"])

    with op.batch_alter_table("trainingplan") as batch_op:
        batch_op.add_column(
            sa.Column("sport", sa.String(length=16), nullable=False, server_default="run")
        )
        batch_op.create_index("ix_trainingplan_sport", ["sport"])

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

    with op.batch_alter_table("trainingplan") as batch_op:
        batch_op.drop_index("ix_trainingplan_sport")
        batch_op.drop_column("sport")

    with op.batch_alter_table("workouttemplate") as batch_op:
        batch_op.drop_index("ix_workouttemplate_sport")
        batch_op.drop_column("sport")
