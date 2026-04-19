"""preview db test

Revision ID: i4c5d6e7f890
Revises: h3b4c5d6e789
Create Date: 2026-04-19 12:00:00.000000

Test migration to verify preview DB isolation is working correctly.
Safe to keep — adds a nullable column that has no effect on app behaviour.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "i4c5d6e7f890"
down_revision: str = "h3b4c5d6e789"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scheduledworkout",
        sa.Column(
            "preview_db_test",
            sa.Boolean(),
            nullable=True,
            comment="Temporary column added to test preview DB isolation. Safe to remove.",
        ),
    )


def downgrade() -> None:
    op.drop_column("scheduledworkout", "preview_db_test")
