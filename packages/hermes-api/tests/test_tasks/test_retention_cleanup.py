"""Retention selects terminal records and preserves files it cannot safely remove."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.core.config import settings
from app.db.repositories import DownloadRepository
from app.services.download_files import register_download_file
from app.tasks import cleanup_tasks


async def test_retention_selects_old_terminal_downloads_only(db_session):
    repository = DownloadRepository(db_session)
    old = datetime.now(timezone.utc) - timedelta(days=40)
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    expected = []
    for status in ["completed", "failed", "cancelled"]:
        download = await repository.create(
            url="https://example.test/watch", status=status, completed_at=old
        )
        expected.append(download.id)
    active = await repository.create(
        url="https://example.test/active", status="downloading"
    )
    active.created_at = old
    await db_session.commit()
    await repository.create(
        url="https://example.test/recent", status="completed", completed_at=recent
    )
    assert {
        row["id"] for row in await cleanup_tasks._get_old_downloads(days=30)
    } == set(expected)


async def test_retention_dry_run_and_actual_cleanup(db_session, tmp_path):
    old = datetime.now(timezone.utc) - timedelta(days=40)
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch", status="completed", completed_at=old
    )
    download_id = download.id
    media = tmp_path / "media.mp4"
    media.write_bytes(b"media")
    await register_download_file(db_session, download_id, str(media))
    await db_session.commit()
    preview = await cleanup_tasks._cleanup_old_downloads_async(days=30, dry_run=True)
    assert preview["would_delete_downloads"] == 1 and preview["would_delete_files"] == 1
    assert media.exists()
    result = await cleanup_tasks._cleanup_old_downloads_async(days=30)
    assert result["deleted_downloads"] == 1 and result["deleted_files"] == 1
    assert not media.exists()
    assert await DownloadRepository(db_session).get_by_id(download_id) is None


async def test_retention_preserves_records_if_file_deletion_fails(
    db_session, monkeypatch
):
    old = datetime.now(timezone.utc) - timedelta(days=40)
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch", status="completed", completed_at=old
    )
    download_id = download.id
    monkeypatch.setattr(
        cleanup_tasks,
        "_cleanup_download_files",
        AsyncMock(
            return_value={
                "deleted_files": 0,
                "failed_files": 1,
                "total_freed_bytes": 0,
                "failed_downloads": [download_id],
            }
        ),
    )
    result = await cleanup_tasks._cleanup_old_downloads_async(days=30)
    assert result["deleted_downloads"] == 0
    assert await DownloadRepository(db_session).get_by_id(download_id) is not None


async def test_retention_refuses_symlink_escape(db_session, tmp_path, monkeypatch):
    root = tmp_path / "downloads"
    root.mkdir()
    monkeypatch.setattr(settings, "download_dir", str(root))
    media = root / "media.mp4"
    media.write_bytes(b"original")
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch",
        status="completed",
        completed_at=datetime.now(timezone.utc) - timedelta(days=40),
    )
    await register_download_file(db_session, download.id, str(media))
    await db_session.commit()
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"outside")
    media.unlink()
    media.symlink_to(outside)
    result = await cleanup_tasks._cleanup_old_downloads_async(days=30)
    assert result["deleted_downloads"] == 0 and result["failed_downloads"] == 1
    assert outside.read_bytes() == b"outside"
