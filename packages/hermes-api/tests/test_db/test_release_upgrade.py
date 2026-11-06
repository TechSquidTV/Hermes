"""Upgrade a seeded database made with the original 0.6.0 migrations."""

import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.base import create_database_engine
from app.db.models import Download, DownloadFile, SystemSettings, User


async def test_upgrade_from_last_release_preserves_accounts_and_media(
    tmp_path: Path,
) -> None:
    api = Path(__file__).resolve().parents[2]
    database = tmp_path / "legacy.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript((api / "tests/fixtures/v0.6.0.sqlite.sql").read_text())
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    media = downloads / "legacy.mp4"
    media.write_bytes(b"legacy-media")
    url = f"sqlite+aiosqlite:///{database}"
    environment = {
        **os.environ,
        "PYTHONPATH": str(api),
        "HERMES_DATABASE_URL": url,
        "HERMES_DOWNLOAD_DIR": str(downloads),
    }
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(api / "alembic.ini"),
            "upgrade",
            "head",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    engine = create_database_engine(url)
    try:
        async with async_sessionmaker(engine)() as session:
            admin = await session.get(User, "legacy-admin")
            assert admin is not None and admin.is_active and admin.is_admin
            assert admin.password_hash == "unused"
            download = await session.get(Download, "legacy-download")
            assert download is not None and download.status == "completed"
            assert download.file_size == 12
            managed = await session.get(DownloadFile, "legacy-file")
            assert managed is not None and managed.filepath == str(media)
            assert media.read_bytes() == b"legacy-media"
            policy = await session.get(SystemSettings, 1)
            assert policy is not None and policy.allow_public_signup
            assert len((await session.scalars(select(DownloadFile))).all()) == 1
        async with engine.connect() as connection:
            indexes = await connection.run_sync(
                lambda sync: inspect(sync).get_indexes("download_files")
            )
            assert "ix_download_files_filepath" in {index["name"] for index in indexes}
    finally:
        await engine.dispose()
