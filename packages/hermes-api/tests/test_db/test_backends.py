"""Migration and runtime contracts for both supported database backends."""

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.base import Base, create_database_engine
from app.db.models import Download, SystemSettings, User
from app.db.repositories import SystemSettingsRepository
from app.db.types import UTCDateTime

API_ROOT = Path(__file__).resolve().parents[2]


def migrate(url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=API_ROOT,
        env={**os.environ, "HERMES_DATABASE_URL": url},
        text=True,
        capture_output=True,
        check=True,
    )


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://host/db",
        "sqlite:///test.db",
        "mysql+aiomysql://host/db",
        "not-a-url",
    ],
)
def test_reject_unsupported_database_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=url)


def test_postgres_offline_migrations_support_encoded_password() -> None:
    result = migrate(
        "postgresql+asyncpg://hermes:p%25ss%40word@localhost/hermes",
        "upgrade",
        "head",
        "--sql",
    )
    assert "ALTER TABLE downloads ALTER COLUMN file_size TYPE BIGINT" in result.stdout
    assert "false" in result.stdout.lower()
    assert "INSERT INTO system_settings" in result.stdout


async def validate_policy_roundtrip(session: AsyncSession) -> None:
    repository = SystemSettingsRepository(session)
    for enabled in (True, False):
        policy = await repository.update_allow_public_signup(enabled)
        await session.refresh(policy)
        assert policy.allow_public_signup is enabled
        assert isinstance(policy.updated_at, datetime)
        assert policy.updated_at.tzinfo is None


async def validate_migrations(url: str) -> None:
    engine = create_database_engine(url)
    try:
        async with engine.connect() as conn:
            tables = await conn.run_sync(lambda sync: inspect(sync).get_table_names())
        assert (
            tables == []
        ), "Integration migration target must be an empty disposable database"
        migrate(url, "upgrade", "head")

        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            user = User(
                id="user",
                username="postgres-user",
                email="pg@example.com",
                password_hash="hash",
                preferences={"theme": "dark"},
            )
            download = Download(
                id="download",
                url="https://example.com/video",
                file_size=5_000_000_000,
                downloaded_bytes=5_000_000_000,
                total_bytes=5_000_000_000,
            )
            session.add_all([user, download])
            await session.commit()
            await session.refresh(user)
            assert user.preferences == {"theme": "dark"}
            await session.refresh(download)
            assert download.file_size == 5_000_000_000
            assert download.downloaded_bytes == 5_000_000_000
            assert download.total_bytes == 5_000_000_000
            policy = await session.get(SystemSettings, 1)
            assert policy is not None
            assert isinstance(policy.allow_public_signup, bool)
            await validate_policy_roundtrip(session)
            assert download.created_at.tzinfo is None
            await session.delete(download)
            await session.delete(user)
            await session.commit()
        migrate(url, "downgrade", "base")
        migrate(url, "upgrade", "head")
        migrate(url, "downgrade", "base")
        # Startup may create a fresh schema directly. Exercise the same policy
        # writes there to catch model/migration type disagreements.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine)() as session:
            await validate_policy_roundtrip(session)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()


async def test_sqlite_migration_cycle(tmp_path: Path) -> None:
    await validate_migrations(f"sqlite+aiosqlite:///{tmp_path}/nested/hermes.db")


@pytest.mark.integration
async def test_postgresql_migration_cycle() -> None:
    url = os.environ.get("HERMES_TEST_POSTGRES_URL")
    if not url:
        pytest.skip(
            "Set HERMES_TEST_POSTGRES_URL to an empty disposable PostgreSQL database"
        )
    assert url.startswith("postgresql+asyncpg://")
    await validate_migrations(url)


async def test_memory_sqlite_engine() -> None:
    engine = create_database_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.connect() as conn:
            assert await conn.scalar(select(1)) == 1
    finally:
        await engine.dispose()


def test_timestamp_binding_normalizes_offsets() -> None:
    value = datetime(2026, 1, 1, 4, tzinfo=timezone(timedelta(hours=4)))
    timestamp = UTCDateTime()
    dialect = cast("type[Dialect]", postgresql.asyncpg.dialect)()
    assert timestamp.process_bind_param(value, dialect) == datetime(2026, 1, 1)
    assert timestamp.process_bind_param(datetime(2026, 1, 1), dialect) == datetime(
        2026, 1, 1
    )
    assert timestamp.process_bind_param(None, dialect) is None
