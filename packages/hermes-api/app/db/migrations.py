"""One migration path for native startup, containers and Alembic commands."""

import asyncio
import fcntl
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import BigInteger, Integer, MetaData, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.db.base import Base, engine

API_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_LOCK = 0x4845524D4553


def migration_config() -> Config:
    return Config(str(API_ROOT / "alembic.ini"))


def expected_revision() -> str:
    head = ScriptDirectory.from_config(migration_config()).get_current_head()
    if head is None:
        raise RuntimeError("No database migration head found")
    return head


async def migrate_database() -> None:
    # Alembic owns an event loop and global context; keep it off the API loop.
    await asyncio.to_thread(command.upgrade, migration_config(), "head")


async def check_schema() -> str:
    async with engine.connect() as connection:
        revision = await connection.scalar(
            text("SELECT version_num FROM alembic_version")
        )
    if revision != expected_revision():
        raise RuntimeError(
            "Database schema does not match this release; run migrations first"
        )
    return str(revision)


@asynccontextmanager
async def migration_connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """Serialize migrations across processes and shared-container mounts."""
    deadline = time.monotonic() + 120
    if engine.dialect.name == "sqlite":
        database = engine.url.database
        if not database or database == ":memory:":
            raise RuntimeError("Migrations require a persistent database")
        path = Path(database).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_suffix(path.suffix + ".migration.lock").open("a") as lock:
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            "Timed out waiting for the database migration lock"
                        )
                    await asyncio.sleep(0.1)
            async with engine.connect() as connection:
                yield connection
        return

    async with engine.connect() as connection:
        while not await connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": MIGRATION_LOCK}
        ):
            await connection.rollback()
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for the database migration lock")
            await asyncio.sleep(0.1)
        await connection.commit()
        try:
            yield connection
        finally:
            await connection.rollback()
            await connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK}
            )
            await connection.commit()


def adopt_native_schema(connection: Connection) -> None:
    """Baseline only recognized create_all schemas; never blindly stamp head."""
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if not tables or "alembic_version" in tables:
        return
    from app.db import models  # noqa: F401

    expected = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(expected)
    downloads = expected.tables["downloads"]
    heartbeat = (
        "last_heartbeat_at"
        in {column["name"] for column in inspector.get_columns("downloads")}
        if "downloads" in tables
        else False
    )
    if not heartbeat:
        downloads.indexes = {
            index
            for index in downloads.indexes
            if index.name != "ix_downloads_active_heartbeat"
        }
        downloads._columns.remove(downloads.c.last_heartbeat_at)
    indexes = (
        {index["name"] for index in inspector.get_indexes("download_files")}
        if "download_files" in tables
        else set()
    )
    paths = expected.tables["download_files"]
    if not heartbeat and "ix_download_files_filepath" not in indexes:
        paths.indexes = {
            index
            for index in paths.indexes
            if index.name != "ix_download_files_filepath"
        }
    # Old native schemas used INTEGER counters. SQLite INTEGER is already 64-bit.
    for table in expected.tables.values():
        columns = (
            {column["name"]: column for column in inspector.get_columns(table.name)}
            if table.name in tables
            else {}
        )
        for column in table.columns:
            actual = columns.get(column.name)
            if (
                not heartbeat
                and isinstance(column.type, BigInteger)
                and actual is not None
                and isinstance(actual["type"], Integer)
                and not isinstance(actual["type"], BigInteger)
            ):
                column.type = Integer()
    context = MigrationContext.configure(connection)
    differences = compare_metadata(context, expected)
    if differences:
        raise RuntimeError(
            "Unversioned database schema is not a recognized native installation; "
            "restore a backup and reconcile the schema before migrating"
        )
    # Pre-heartbeat native installations still need path repair and counter widening.
    revision = "a7c4e19d82b6" if heartbeat else "d5e92b7f3a1c"
    if not heartbeat and "ix_download_files_filepath" in indexes:
        connection.execute(text("DROP INDEX ix_download_files_filepath"))
    context.stamp(ScriptDirectory.from_config(migration_config()), revision)
