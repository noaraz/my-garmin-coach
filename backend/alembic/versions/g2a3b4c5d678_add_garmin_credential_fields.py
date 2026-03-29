"""add garmin credential fields for auto-reconnect

Revision ID: g2a3b4c5d678
Revises: f1a2b3c4d567
Create Date: 2026-03-29 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "g2a3b4c5d678"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("athleteprofile", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("garmin_credential_encrypted", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("garmin_credential_stored_at", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("athleteprofile", schema=None) as batch_op:
        batch_op.drop_column("garmin_credential_stored_at")
        batch_op.drop_column("garmin_credential_encrypted")
