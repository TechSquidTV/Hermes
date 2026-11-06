"""Canonicalize and index managed file paths.

Revision ID: e7f31a92c604
Revises: d5e92b7f3a1c
"""

from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision = "e7f31a92c604"
down_revision = "d5e92b7f3a1c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Normalize historical paths once, then enable indexed exact lookup."""
    if op.get_context().as_sql:
        raise RuntimeError(
            "Managed path canonicalization requires an online migration on the "
            "API host with its download filesystem mounted; SQL-only migration "
            "generation cannot resolve historical paths or symlinks. Run "
            "alembic upgrade head without --sql."
        )
    files = sa.table(
        "download_files", sa.column("id", sa.String), sa.column("filepath", sa.String)
    )
    connection = op.get_bind()
    last_id = ""
    while True:
        rows = connection.execute(
            sa.select(files.c.id, files.c.filepath)
            .where(files.c.id > last_id)
            .order_by(files.c.id)
            .limit(500)
        ).all()
        if not rows:
            break
        for file_id, filepath in rows:
            canonical = str(Path(filepath).resolve(strict=False))
            connection.execute(
                files.update().where(files.c.id == file_id).values(filepath=canonical)
            )
        last_id = rows[-1].id
    op.create_index("ix_download_files_filepath", "download_files", ["filepath"])


def downgrade() -> None:
    """Remove the lookup index; canonical paths remain valid."""
    op.drop_index("ix_download_files_filepath", table_name="download_files")
