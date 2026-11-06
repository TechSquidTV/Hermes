"""Exercise upgrade failures against disposable databases, not operator data."""

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from threading import Event, Thread

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db.backup import backup_database, postgres_environment, restore_database
from app.db.base import Base, create_database_engine

API = Path(__file__).resolve().parents[2]


def migration_environment(database: Path) -> dict[str, str]:
    return {**os.environ, "HERMES_DATABASE_URL": f"sqlite+aiosqlite:///{database}"}


def migration_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(API / "alembic.ini"),
        "upgrade",
        "head",
    ]


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("empty_version", [False, True])
async def test_adopt_validated_native_schema_preserves_data(
    tmp_path: Path, legacy: bool, empty_version: bool
) -> None:
    database = tmp_path / "native.db"
    if legacy:
        with closing(sqlite3.connect(database)) as connection:
            connection.executescript(
                (API / "tests/fixtures/v0.6.0.sqlite.sql").read_text()
            )
            connection.execute("DROP TABLE alembic_version")
            connection.commit()
    else:
        engine = create_database_engine(f"sqlite+aiosqlite:///{database}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()
    if empty_version:
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
            )
            connection.commit()
    result = subprocess.run(
        migration_command(),
        env=migration_environment(database),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == ("a7c4e19d82b6",)
        assert "last_heartbeat_at" in {
            column[1] for column in connection.execute("PRAGMA table_info(downloads)")
        }
        if legacy:
            assert connection.execute("SELECT username FROM users").fetchone() == (
                "legacy-admin",
            )
            assert connection.execute(
                "SELECT count(*) FROM download_files"
            ).fetchone() == (1,)


def test_refuse_unknown_native_schema_without_stamping(tmp_path: Path) -> None:
    database = tmp_path / "unknown.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "CREATE TABLE users (id TEXT PRIMARY KEY, private_note TEXT)"
        )
        connection.execute("INSERT INTO users VALUES ('owner', 'preserve-me')")
        connection.commit()
    result = subprocess.run(
        migration_command(),
        env=migration_environment(database),
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode != 0
        and "not a recognized native installation" in result.stderr
    )
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT private_note FROM users").fetchone() == (
            "preserve-me",
        )
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='alembic_version'"
            ).fetchone()
            is None
        )


async def test_readonly_alembic_inspection_never_adopts_native_schema(
    tmp_path: Path,
) -> None:
    database = tmp_path / "native-inspection.db"
    engine = create_database_engine(f"sqlite+aiosqlite:///{database}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()
    result = subprocess.run(
        [*migration_command()[:-2], "current"],
        env=migration_environment(database),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='alembic_version'"
            ).fetchone()
            is None
        )


def test_in_process_migration_preserves_application_logging(tmp_path: Path) -> None:
    program = """
import asyncio, logging
from app.core.logging import setup_logging, get_logger
from app.db.migrations import migrate_database
logging.getLogger().handlers.clear()
setup_logging()
root = logging.getLogger()
handlers = list(root.handlers)
logger = get_logger("upgrade_logging_probe")
logger.info("before_upgrade")
asyncio.run(migrate_database())
assert root.level == logging.INFO and root.handlers == handlers
logger.info("after_upgrade")
"""
    result = subprocess.run(
        [sys.executable, "-c", program],
        env=migration_environment(tmp_path / "logging.db"),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    events = [
        json.loads(line)["event"]
        for line in result.stdout.splitlines()
        if line.startswith("{")
    ]
    assert events == ["before_upgrade", "after_upgrade"]


def test_concurrent_migrations_all_succeed(tmp_path: Path) -> None:
    database = tmp_path / "concurrent.db"
    processes = [
        subprocess.Popen(
            migration_command(),
            env=migration_environment(database),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(4)
    ]
    for process in processes:
        _, error = process.communicate(timeout=60)
        assert process.returncode == 0, error
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT count(*) FROM alembic_version"
        ).fetchone() == (1,)


def test_online_backup_stays_consistent_and_restores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "source.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{database}")
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            "CREATE TABLE pair (id INTEGER PRIMARY KEY, version INTEGER); INSERT INTO pair VALUES (1, 0), (2, 0);"
        )
    stopped = Event()
    ready = Event()

    def writer() -> None:
        with closing(sqlite3.connect(database)) as connection:
            ready.set()
            while not stopped.is_set():
                connection.execute("UPDATE pair SET version = version + 1")
                connection.commit()
                stopped.wait(0.001)

    thread = Thread(target=writer)
    thread.start()
    ready.wait(5)
    try:
        snapshot = backup_database(tmp_path / "backup")
    finally:
        stopped.set()
        thread.join(5)
    with closing(sqlite3.connect(snapshot)) as connection:
        original = connection.execute("SELECT version FROM pair ORDER BY id").fetchall()
        assert original[0] == original[1]
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DROP TABLE pair")
        connection.commit()
    restore_database(snapshot)
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute("SELECT version FROM pair ORDER BY id").fetchall()
            == original
        )
    assert snapshot.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        backup_database(snapshot.parent)


def test_postgres_backup_preserves_tls_and_encoded_credentials() -> None:
    environment = postgres_environment(
        make_url(
            "postgresql+asyncpg://owner:p%25ss%40word@database:5433/hermes?ssl=verify-full&sslrootcert=%2Fcerts%2Fca.pem"
        )
    )
    assert environment["PGPASSWORD"] == "p%ss@word"
    assert environment["PGPORT"] == "5433"
    assert environment["PGSSLMODE"] == "verify-full"
    assert environment["PGSSLROOTCERT"] == "/certs/ca.pem"


@pytest.mark.integration
async def test_postgresql_snapshot_restore_and_concurrent_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = os.environ.get("HERMES_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set HERMES_TEST_POSTGRES_URL to a disposable PostgreSQL database")
    monkeypatch.setattr(settings, "database_url", url)
    environment = {**os.environ, "HERMES_DATABASE_URL": url}
    processes = [
        subprocess.Popen(
            migration_command(),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(3)
    ]
    for process in processes:
        _, error = process.communicate(timeout=60)
        assert process.returncode == 0, error
    engine = create_database_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE system_settings SET allow_public_signup = true WHERE id = 1"
                )
            )
        snapshot = backup_database(tmp_path / "postgres-backup")
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE system_settings SET allow_public_signup = false WHERE id = 1"
                )
            )
        await engine.dispose()
        restore_database(snapshot)
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text("SELECT allow_public_signup FROM system_settings WHERE id = 1")
                )
                is True
            )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(API / "alembic.ini"),
                "downgrade",
                "base",
            ],
            env=environment,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        # Reproduce a native installation from immediately before heartbeat
        # tracking: ORM-created BIGINT columns and path index, no version table.
        async with engine.begin() as connection:
            await connection.execute(text("DROP TABLE alembic_version"))
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(
                text("ALTER TABLE downloads DROP COLUMN last_heartbeat_at CASCADE")
            )
        adopted = subprocess.run(
            migration_command(), env=environment, capture_output=True, text=True
        )
        assert adopted.returncode == 0, adopted.stderr
        cleanup = subprocess.run(
            [*migration_command()[:-2], "downgrade", "base"],
            env=environment,
            capture_output=True,
            text=True,
        )
        assert cleanup.returncode == 0, cleanup.stderr
    finally:
        await engine.dispose()
