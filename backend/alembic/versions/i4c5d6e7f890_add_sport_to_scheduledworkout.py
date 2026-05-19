"""add sport column to scheduledworkout

Revision ID: i4c5d6e7f890
Revises: h3b4c5d6e789
Create Date: 2026-05-19 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i4c5d6e7f890"
down_revision: Union[str, None] = "h3b4c5d6e789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("scheduledworkout") as batch_op:
        batch_op.add_column(
            sa.Column("sport", sa.String(length=16), nullable=False, server_default="run")
        )


def downgrade() -> None:
    with op.batch_alter_table("scheduledworkout") as batch_op:
        batch_op.drop_column("sport")
