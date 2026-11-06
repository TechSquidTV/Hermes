"""Operator CLI exercises: preflight is read-only and rollback is explicit."""

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from app import manage
from app.core import maintenance
from app.core.config import settings

API = Path(__file__).resolve().parents[2]


def operator(database: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.manage", *arguments],
        env={**os.environ, "HERMES_DATABASE_URL": f"sqlite+aiosqlite:///{database}"},
        capture_output=True,
        text=True,
    )


def test_operator_upgrade_and_explicit_restore_old_schema(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript((API / "tests/fixtures/v0.6.0.sqlite.sql").read_text())
    before = database.read_bytes()
    preflight = operator(database, "preflight")
    assert preflight.returncode == 0, preflight.stderr
    assert json.loads(preflight.stdout)["revision"] == "a7c4e19d82b6"
    assert database.read_bytes() == before
    backup = operator(database, "backup", str(tmp_path / "snapshot"))
    assert backup.returncode == 0, backup.stderr
    snapshot = json.loads(backup.stdout)["snapshot"]
    migrated = operator(database, "migrate")
    assert migrated.returncode == 0, migrated.stderr
    assert operator(database, "check-schema").returncode == 0
    refused = operator(database, "restore", snapshot)
    assert refused.returncode != 0 and "--confirm-stopped" in refused.stderr
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == ("a7c4e19d82b6",)
    restored = operator(database, "restore", snapshot, "--confirm-stopped")
    assert restored.returncode == 0, restored.stderr
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == ("d5e92b7f3a1c",)
        assert connection.execute("SELECT username FROM users").fetchone() == (
            "legacy-admin",
        )
    assert operator(database, "check-schema").returncode != 0


def test_preflight_never_creates_a_missing_database(tmp_path: Path) -> None:
    database = tmp_path / "missing.db"
    result = operator(database, "preflight")
    assert (
        result.returncode != 0 and "Existing SQLite database not found" in result.stderr
    )
    assert not database.exists()


def test_maintenance_cli_is_persistent_and_blocks_another_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flag = tmp_path / "maintenance"
    monkeypatch.setattr(maintenance, "MAINTENANCE_FILE", flag)
    monkeypatch.setattr(sys, "argv", ["manage", "maintenance", "on"])
    manage.main()
    assert flag.exists()
    monkeypatch.setattr(sys, "argv", ["manage", "preflight"])
    with pytest.raises(RuntimeError, match="already in maintenance"):
        manage.main()
    monkeypatch.setattr(sys, "argv", ["manage", "maintenance", "off"])
    manage.main()
    assert not flag.exists()


def test_postgres_preflight_requires_backup_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings, "database_url", "postgresql+asyncpg://owner@database/hermes"
    )
    monkeypatch.setattr("shutil.which", lambda tool: None)
    monkeypatch.setattr(sys, "argv", ["manage", "preflight"])
    with pytest.raises(RuntimeError, match="PostgreSQL client tools"):
        manage.main()
