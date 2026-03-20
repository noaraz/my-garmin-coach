"""add training plan table and training_plan_id FK

Revision ID: d4e9a2b1c567
Revises: c5d2e7f4a123
Create Date: 2026-03-20 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e9a2b1c567'
down_revision: Union[str, Sequence[str], None] = 'c5d2e7f4a123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trainingplan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('parsed_workouts', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trainingplan_user_status', 'trainingplan', ['user_id', 'status'])

    with op.batch_alter_table('scheduledworkout', schema=None) as batch_op:
        batch_op.add_column(sa.Column('training_plan_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_scheduledworkout_training_plan',
            'trainingplan',
            ['training_plan_id'],
            ['id'],
        )


def downgrade() -> None:
    with op.batch_alter_table('scheduledworkout', schema=None) as batch_op:
        batch_op.drop_constraint('fk_scheduledworkout_training_plan', type_='foreignkey')
        batch_op.drop_column('training_plan_id')

    op.drop_index('ix_trainingplan_user_status', table_name='trainingplan')
    op.drop_table('trainingplan')
