"""add_user_is_admin_field

Revision ID: c4584c156bdd
Revises: 96e3543c1899
Create Date: 2025-11-09 13:04:00.567491

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4584c156bdd'
down_revision: Union[str, Sequence[str], None] = '96e3543c1899'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_admin column to users table
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0')
    )
    # Create index on is_admin for query performance
    op.create_index(op.f('ix_users_is_admin'), 'users', ['is_admin'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index(op.f('ix_users_is_admin'), table_name='users')
    # Drop is_admin column
    op.drop_column('users', 'is_admin')
