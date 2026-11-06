"""Track worker heartbeats for abandoned download recovery.

Revision ID: a7c4e19d82b6
Revises: f2a84c6d901b
"""

import sqlalchemy as sa

from alembic import op

revision: str = "a7c4e19d82b6"
down_revision: str = "f2a84c6d901b"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "downloads", sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True)
    )
    op.create_index(
        "ix_downloads_active_heartbeat", "downloads", ["status", "last_heartbeat_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_downloads_active_heartbeat", table_name="downloads")
    op.drop_column("downloads", "last_heartbeat_at")
