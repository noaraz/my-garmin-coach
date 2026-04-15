"""add system_config table and garmin_auth_version

Revision ID: h3b4c5d6e789
Revises: g2a3b4c5d678
Create Date: 2026-04-14 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "h3b4c5d6e789"
down_revision: Union[str, Sequence[str], None] = "460d2c67b829"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "systemconfig",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )

    with op.batch_alter_table("athleteprofile", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("garmin_auth_version", sa.String(), nullable=True, server_default="v1")
        )


def downgrade() -> None:
    with op.batch_alter_table("athleteprofile", schema=None) as batch_op:
        batch_op.drop_column("garmin_auth_version")

    op.drop_table("systemconfig")
