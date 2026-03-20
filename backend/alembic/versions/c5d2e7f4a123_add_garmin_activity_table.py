"""add garmin activity table and matched_activity_id FK

Revision ID: c5d2e7f4a123
Revises: b4e2f1a3c789
Create Date: 2026-03-19 22:30:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c5d2e7f4a123'
down_revision: Union[str, Sequence[str], None] = 'b4e2f1a3c789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'garminactivity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('garmin_activity_id', sa.String(), nullable=False),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('duration_sec', sa.Float(), nullable=False),
        sa.Column('distance_m', sa.Float(), nullable=False),
        sa.Column('avg_hr', sa.Float(), nullable=True),
        sa.Column('max_hr', sa.Float(), nullable=True),
        sa.Column('avg_pace_sec_per_km', sa.Float(), nullable=True),
        sa.Column('calories', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('garmin_activity_id'),
    )
    op.create_index('ix_garminactivity_user_date', 'garminactivity', ['user_id', 'date'])

    with op.batch_alter_table('scheduledworkout', schema=None) as batch_op:
        batch_op.add_column(sa.Column('matched_activity_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_scheduledworkout_matched_activity',
            'garminactivity',
            ['matched_activity_id'],
            ['id'],
        )
    op.create_index('ix_scheduledworkout_matched_activity', 'scheduledworkout', ['matched_activity_id'])


def downgrade() -> None:
    op.drop_index('ix_scheduledworkout_matched_activity', table_name='scheduledworkout')
    with op.batch_alter_table('scheduledworkout', schema=None) as batch_op:
        batch_op.drop_constraint('fk_scheduledworkout_matched_activity', type_='foreignkey')
        batch_op.drop_column('matched_activity_id')

    op.drop_index('ix_garminactivity_user_date', table_name='garminactivity')
    op.drop_table('garminactivity')
