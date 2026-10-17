"""Use 64-bit media sizes and counters on PostgreSQL.

Revision ID: f2a84c6d901b
Revises: d5e92b7f3a1c
"""

import sqlalchemy as sa

from alembic import op

revision: str = "f2a84c6d901b"
down_revision: str = "d5e92b7f3a1c"
branch_labels: None = None
depends_on: None = None

COLUMNS = {
    "downloads": ("downloaded_bytes", "total_bytes", "file_size"),
    "download_files": ("file_size",),
    "download_history": ("file_size",),
    "batch_videos": ("view_count",),
}


def upgrade() -> None:
    # SQLite INTEGER already stores signed 64-bit values; no table rebuild needed.
    if op.get_bind().dialect.name == "postgresql":
        for table, columns in COLUMNS.items():
            for column in columns:
                op.alter_column(
                    table, column, existing_type=sa.Integer(), type_=sa.BigInteger()
                )


def downgrade() -> None:
    # PostgreSQL rejects this narrowing if stored values exceed 32 bits. Operators
    # must archive those records before downgrade; never silently truncate sizes.
    if op.get_bind().dialect.name == "postgresql":
        for table, columns in COLUMNS.items():
            for column in columns:
                op.alter_column(
                    table, column, existing_type=sa.BigInteger(), type_=sa.Integer()
                )
