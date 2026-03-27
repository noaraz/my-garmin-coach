"""add garmin_schedule_id to scheduledworkout

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d567
Create Date: 2026-03-27 00:00:00.000000

Stores the Garmin schedule entry ID returned by schedule_workout() so that
reconciliation can verify the workout is still on the Garmin calendar
(not just that the template exists in the library).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f1a2b3c4d567"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scheduledworkout") as batch_op:
        batch_op.add_column(
            sa.Column("garmin_schedule_id", sa.String(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("scheduledworkout") as batch_op:
        batch_op.drop_column("garmin_schedule_id")
