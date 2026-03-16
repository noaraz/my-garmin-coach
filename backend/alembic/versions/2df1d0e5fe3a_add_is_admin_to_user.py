"""add is_admin to user

Revision ID: 2df1d0e5fe3a
Revises: 7cd1f83b9815
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2df1d0e5fe3a'
down_revision: Union[str, Sequence[str], None] = '7cd1f83b9815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('user', 'is_admin')
