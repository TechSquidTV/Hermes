"""Consistent database snapshots, with an explicit offline restore command."""

import json
import os
import sqlite3
import subprocess
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import URL, make_url

from app.core.config import settings


def postgres_environment(url: URL) -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("PG")
    }
    for key, value in {
        "PGHOST": url.host,
        "PGPORT": str(url.port or 5432),
        "PGUSER": url.username,
        "PGPASSWORD": url.password,
        "PGDATABASE": url.database,
    }.items():
        if value is not None:
            environment[key] = value
    for key, query_value in url.query.items():
        translated = {
            "ssl": "sslmode",
            "sslmode": "sslmode",
            "sslrootcert": "sslrootcert",
            "sslcert": "sslcert",
            "sslkey": "sslkey",
            "connect_timeout": "connect_timeout",
        }.get(key)
        if translated is None or not isinstance(query_value, str):
            raise ValueError(f"Unsupported PostgreSQL backup connection option: {key}")
        environment[f"PG{translated.upper()}"] = query_value
    return environment


def postgres_command(command: list[str], url: URL) -> None:
    # Keep credentials out of command lines and exception output.
    result = subprocess.run(command, env=postgres_environment(url), capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"{command[0]} failed; check connectivity, TLS and client/server versions"
        )


def backup_database(destination: Path) -> Path:
    """Create a new private snapshot directory; never overwrite an earlier backup."""
    url = make_url(settings.database_url)
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    snapshot = destination / (
        "database.sqlite" if url.get_backend_name() == "sqlite" else "database.dump"
    )
    try:
        if url.get_backend_name() == "sqlite":
            source = Path(url.database or "").resolve()
            if not source.is_file():
                raise ValueError("SQLite source database does not exist")
            with closing(
                sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
            ) as original, closing(sqlite3.connect(snapshot)) as target:
                original.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise RuntimeError("Database backup integrity check failed")
                revision = (
                    target.execute("SELECT version_num FROM alembic_version").fetchone()
                    if target.execute(
                        "SELECT name FROM sqlite_master WHERE name='alembic_version'"
                    ).fetchone()
                    else None
                )
        else:
            postgres_command(
                ["pg_dump", "--format=custom", "--file", str(snapshot)], url
            )
            postgres_command(["pg_restore", "--list", str(snapshot)], url)
            revision = None
        snapshot.chmod(0o600)
        (destination / "backup.json").write_text(
            json.dumps(
                {
                    "backend": url.get_backend_name(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "revision": revision[0] if revision else None,
                    "file": snapshot.name,
                },
                indent=2,
            )
            + "\n"
        )
        return snapshot
    except BaseException:
        # Leave an incomplete directory for diagnosis, without a success manifest.
        if snapshot.exists():
            snapshot.chmod(0o600)
        raise


def restore_database(snapshot: Path) -> None:
    """Caller must stop every API, worker and scheduler before restoring."""
    if not snapshot.is_file():
        raise ValueError("Backup file does not exist")
    url = make_url(settings.database_url)
    if url.get_backend_name() == "sqlite":
        target_path = Path(url.database or "").resolve()
        if snapshot.resolve() == target_path:
            raise ValueError("Backup and destination must be different files")
        with closing(
            sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)
        ) as source:
            if source.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise RuntimeError("Backup integrity check failed")
            with closing(sqlite3.connect(target_path)) as target:
                source.backup(target)
    else:
        postgres_command(
            [
                "pg_restore",
                "--exit-on-error",
                "--single-transaction",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--dbname",
                url.database or "",
                str(snapshot),
            ],
            url,
        )
