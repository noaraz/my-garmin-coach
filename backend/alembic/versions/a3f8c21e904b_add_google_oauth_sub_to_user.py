"""add google_oauth_sub to user

Revision ID: a3f8c21e904b
Revises: 2df1d0e5fe3a
Create Date: 2026-03-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3f8c21e904b'
down_revision: Union[str, Sequence[str], None] = '2df1d0e5fe3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_oauth_sub', sa.String(), nullable=True))
        batch_op.alter_column('password_hash', existing_type=sa.String(), nullable=True)
        batch_op.create_unique_constraint('uq_user_google_oauth_sub', ['google_oauth_sub'])


def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_google_oauth_sub', type_='unique')
        batch_op.alter_column('password_hash', existing_type=sa.String(), nullable=False)
        batch_op.drop_column('google_oauth_sub')
