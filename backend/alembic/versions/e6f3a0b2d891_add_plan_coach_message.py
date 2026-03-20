"""add plan_coach_message table

Revision ID: e6f3a0b2d891
Revises: d4e9a2b1c567
Create Date: 2026-03-20 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e6f3a0b2d891'
down_revision: Union[str, Sequence[str], None] = 'd4e9a2b1c567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'plancoachMessage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_plancoachMessage_user_id', 'plancoachMessage', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_plancoachMessage_user_id', table_name='plancoachMessage')
    op.drop_table('plancoachMessage')
