"""drop unused password auth columns

Revision ID: b4e2f1a3c789
Revises: a3f8c21e904b
Create Date: 2026-03-19 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4e2f1a3c789'
down_revision: Union[str, Sequence[str], None] = 'a3f8c21e904b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('password_hash')
        batch_op.drop_column('failed_login_attempts')
        batch_op.drop_column('locked_until')


def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('password_hash', sa.String(), nullable=True))
