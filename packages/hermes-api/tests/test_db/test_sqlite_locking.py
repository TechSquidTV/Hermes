"""Real SQLite locks across request lifetimes, task loops and processes."""

import asyncio
import sqlite3
import subprocess
import sys
from contextlib import aclosing, closing
from pathlib import Path
from typing import Literal

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db import base
from app.db.errors import is_sqlite_lock_error
from app.db.migrations import migration_connection
from app.db.session import get_database_session
from app.tasks import runtime

Outcome = Literal["success", "error", "cancel"]


async def prepare_database(path: Path) -> AsyncEngine:
    engine = base.create_database_engine(f"sqlite+aiosqlite:///{path}")
    async with migration_connection(engine):
        pass
    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE probe (value INTEGER NOT NULL)"))
        await connection.execute(text("INSERT INTO probe VALUES (0)"))
    return engine


def independent_write(path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sqlite3,sys; "
            "c=sqlite3.connect(sys.argv[1], timeout=0.1); "
            "c.execute('UPDATE probe SET value=value'); c.commit(); c.close()",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )


@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
async def test_request_dependency_closes_transaction_before_returning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: Outcome
) -> None:
    path = tmp_path / "request.db"
    engine = await prepare_database(path)
    monkeypatch.setattr(base, "async_session_maker", async_sessionmaker(engine))
    sessions: list[AsyncSession] = []

    async def request() -> None:
        async with aclosing(get_database_session()) as dependency:
            session = await anext(dependency)
            sessions.append(session)
            await session.execute(text("UPDATE probe SET value=10"))
            if outcome == "error":
                raise RuntimeError("request failed")
            if outcome == "cancel":
                task = asyncio.current_task()
                assert task is not None
                task.cancel()
                await asyncio.sleep(0)

    try:
        if outcome == "success":
            await request()
        else:
            with pytest.raises(
                RuntimeError if outcome == "error" else asyncio.CancelledError
            ):
                await asyncio.create_task(request())
        assert len(sessions) == 1 and not sessions[0].in_transaction()
        independent_write(path)
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute("SELECT value FROM probe").fetchone() == (0,)
    finally:
        await engine.dispose()


def test_successive_worker_loops_release_failed_and_cancelled_transactions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "worker.db"
    engine = asyncio.run(prepare_database(path))
    monkeypatch.setattr(runtime, "engine", engine)
    factory = async_sessionmaker(engine)

    async def operation(outcome: Outcome) -> None:
        async with factory() as session:
            await session.execute(text("UPDATE probe SET value=value+1"))
            if outcome == "error":
                raise RuntimeError("task failed")
            if outcome == "cancel":
                task = asyncio.current_task()
                assert task is not None
                task.cancel()
                await asyncio.sleep(0)
            await session.commit()

    try:
        outcomes: tuple[Outcome, ...] = ("success", "error", "cancel")
        for _ in range(5):
            for outcome in outcomes:
                if outcome == "success":
                    runtime.run_async_task(operation(outcome))
                else:
                    with pytest.raises(
                        RuntimeError if outcome == "error" else asyncio.CancelledError
                    ):
                        runtime.run_async_task(operation(outcome))
                independent_write(path)
        with closing(sqlite3.connect(path)) as connection:
            assert connection.execute("SELECT value FROM probe").fetchone() == (5,)
    finally:
        asyncio.run(engine.dispose())


@pytest.mark.parametrize("journal_mode", ["delete", "wal"])
async def test_worker_reader_and_api_writer_in_separate_processes(
    tmp_path: Path, journal_mode: str
) -> None:
    from sqlalchemy.exc import OperationalError

    path = tmp_path / "concurrent.db"
    engine = await prepare_database(path)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute(f"PRAGMA journal_mode={journal_mode}").fetchone() == (
            journal_mode,
        )
    # An explicit reader transaction reproduces the worker lock observed in 0.6.0.
    worker = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); "
            "c.execute('BEGIN'); c.execute('SELECT value FROM probe').fetchall(); "
            "print('reader ready', flush=True); sys.stdin.readline(); "
            "c.rollback(); c.close()",
            str(path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert worker.stdout is not None
        assert worker.stdout.readline().strip() == "reader ready"

        async def write() -> None:
            async with engine.begin() as connection:
                await connection.execute(text("UPDATE probe SET value=1"))

        if journal_mode == "delete":
            with pytest.raises(OperationalError) as caught:
                await write()
            assert is_sqlite_lock_error(caught.value)
        else:
            await write()
    finally:
        try:
            _, stderr = worker.communicate("release\n", timeout=10)
            assert worker.returncode == 0, stderr
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=10)
            await engine.dispose()
    independent_write(path)


async def test_auth_reports_contention_without_invalidating_credentials(
    client: AsyncClient,
) -> None:
    if base.engine.dialect.name != "sqlite":
        pytest.skip("SQLite-specific lock regression")
    database = base.engine.url.database
    assert database is not None
    with closing(sqlite3.connect(database)) as blocker:
        blocker.execute("BEGIN EXCLUSIVE")
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "lock-probe", "password": "not-a-real-password"},
            )
            assert response.status_code == 503
            assert response.headers["Retry-After"] == "5"
            assert response.json()["error"]["code"] == "database_busy"
            assert "not-a-real-password" not in response.text
            assert "SELECT" not in response.text
        finally:
            blocker.rollback()
    # No automatic retry or false successful authentication occurred.
    assert (
        await client.post(
            "/api/v1/auth/login",
            json={"username": "lock-probe", "password": "not-a-real-password"},
        )
    ).status_code == 401


async def test_detailed_health_reads_application_tables(
    client: AsyncClient,
) -> None:
    from app.api.v1.endpoints import health

    if base.engine.dialect.name != "sqlite":
        pytest.skip("SQLite-specific lock regression")
    database = base.engine.url.database
    assert database is not None
    assert (await health.get_detailed_health()).dependencies[
        "database"
    ].status == "healthy"
    with closing(sqlite3.connect(database)) as blocker:
        blocker.execute("BEGIN EXCLUSIVE")
        try:
            result = await health.get_detailed_health()
            assert result.status == "unhealthy"
            assert result.dependencies["database"].status == "error"
            assert (await client.get("/api/v1/health/")).status_code == 200
        finally:
            blocker.rollback()
    assert (await health.get_detailed_health()).dependencies[
        "database"
    ].status == "healthy"


def test_non_contention_database_errors_keep_their_error_classification() -> None:
    from sqlalchemy.exc import OperationalError

    with closing(sqlite3.connect(":memory:")) as connection:
        with pytest.raises(sqlite3.OperationalError) as caught:
            connection.execute("SELECT missing_column FROM missing_table")
    assert not is_sqlite_lock_error(OperationalError(None, None, caught.value))
    assert not is_sqlite_lock_error(
        OperationalError(None, None, OSError("unavailable"))
    )
