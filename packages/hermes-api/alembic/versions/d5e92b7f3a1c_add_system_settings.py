"""add_system_settings

Revision ID: d5e92b7f3a1c
Revises: c4584c156bdd
Create Date: 2025-11-10 03:00:00.000000

"""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "d5e92b7f3a1c"
down_revision: Union[str, Sequence[str], None] = "c4584c156bdd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create system_settings table
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "allow_public_signup", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column("updated_by_user_id", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Insert initial singleton row with ID=1
    # Seed new installs from the configured signup policy (disabled by default)
    # In production, this will be seeded from HERMES_ALLOW_PUBLIC_SIGNUP
    op.bulk_insert(
        sa.table(
            "system_settings",
            sa.column("id", sa.Integer()),
            sa.column("allow_public_signup", sa.Boolean()),
            sa.column("updated_at", sa.DateTime()),
        ),
        [
            {
                "id": 1,
                "allow_public_signup": settings.allow_public_signup,
                "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("system_settings")
