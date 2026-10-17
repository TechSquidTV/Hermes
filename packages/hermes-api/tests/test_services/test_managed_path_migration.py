"""Verify the managed-path migration against historical noncanonical rows."""

from __future__ import annotations

from collections.abc import Sequence
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Dialect
from sqlalchemy.schema import CreateIndex

from app.db.models import DownloadFile


def _load_path_migration() -> ModuleType:
    migration_path = (
        Path(__file__).parents[2]
        / "alembic/versions/e7f31a92c604_index_managed_file_paths.py"
    )
    spec = spec_from_file_location("managed_path_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_managed_path_migration_normalizes_batches_and_adds_index(
    tmp_path: Path,
) -> None:
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = _load_path_migration()
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    metadata = MetaData()
    files = Table(
        "download_files",
        metadata,
        Column("id", String, primary_key=True),
        Column("filepath", String, nullable=False),
    )
    metadata.create_all(engine)
    historical = str(tmp_path / "nested/../media.mp4")
    with engine.begin() as connection:
        connection.execute(
            files.insert(),
            [{"id": f"{index:04}", "filepath": historical} for index in range(1001)],
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        rows: Sequence[str] = connection.scalars(select(files.c.filepath)).all()
        assert len(rows) == 1001
        assert set(rows) == {str(tmp_path / "media.mp4")}
        assert "ix_download_files_filepath" in {
            index["name"] for index in inspect(connection).get_indexes("download_files")
        }
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert inspect(connection).get_indexes("download_files") == []
    engine.dispose()


def test_managed_path_index_compiles_for_postgresql() -> None:
    index = next(
        index
        for index in cast(Table, DownloadFile.__table__).indexes
        if index.name == "ix_download_files_filepath"
    )
    assert (
        str(
            CreateIndex(index).compile(
                dialect=cast("type[Dialect]", postgresql.dialect)()
            )
        )
        == "CREATE INDEX ix_download_files_filepath ON download_files (filepath)"
    )


def test_managed_path_migration_rejects_offline_sql_generation() -> None:
    import os
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=Path(__file__).parents[2],
        env={**os.environ, "HERMES_DATABASE_URL": "sqlite+aiosqlite:///offline.db"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Managed path canonicalization requires an online migration" in result.stderr
    assert "without --sql" in result.stderr


@pytest.mark.parametrize("dialect_name", ["sqlite", "postgresql"])
def test_offline_guard_requires_online_path_canonicalization(dialect_name: str) -> None:
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = _load_path_migration()
    context = MigrationContext.configure(
        dialect_name=dialect_name, opts={"as_sql": True}
    )
    with Operations.context(context):
        with pytest.raises(RuntimeError, match="requires an online migration"):
            migration.upgrade()
