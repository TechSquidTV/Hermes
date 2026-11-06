"""Real database regressions for dispatch failures and sidecar-safe cleanup."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.downloads import (
    _dispatch_download,
    start_batch_download,
    start_download,
)
from app.api.v1.endpoints.files import delete_downloaded_files
from app.api.v1.endpoints.queue import cleanup_orphaned_downloads
from app.core.config import settings
from app.core.security import AuthPrincipal
from app.db.base import async_session_maker
from app.db.models import DownloadFile
from app.db.repositories import DownloadRepository
from app.models.pydantic.download import BatchDownloadRequest, DownloadRequest
from app.models.pydantic.file import DeleteFilesRequest

ADMIN = AuthPrincipal(kind="api_key", subject="test", permissions=["admin"])


async def test_orphan_cleanup_preserves_surviving_deliverables(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path.resolve()
    monkeypatch.setattr(settings, "download_dir", str(root))
    media, subtitle = root / "media.mp4", root / "media.vtt"
    media.write_bytes(b"media")
    subtitle.write_bytes(b"subtitle")
    repo = DownloadRepository(db_session)
    download = await repo.create(
        "https://example.test/video", status="completed", output_path=str(media)
    )
    for path in (media, subtitle):
        db_session.add(
            DownloadFile(
                id=path.name,
                download_id=download.id,
                filename=path.name,
                filepath=str(path),
                file_size=path.stat().st_size,
                file_type="video",
            )
        )
    await db_session.commit()
    await delete_downloaded_files(
        DeleteFilesRequest(files=[str(media)], confirm=True), db_session, ADMIN
    )
    for preview in (True, False):
        result = await cleanup_orphaned_downloads(preview, db_session, ADMIN)
        assert result.orphaned_count == 0
    assert await db_session.get(DownloadFile, subtitle.name) is not None
    assert subtitle.exists()
    subtitle.unlink()
    assert (
        await cleanup_orphaned_downloads(True, db_session, ADMIN)
    ).orphaned_count == 1
    assert (
        await cleanup_orphaned_downloads(False, db_session, ADMIN)
    ).deleted_count == 1
    assert await repo.get_by_id(download.id) is None


async def test_broker_failure_is_explicit_and_late_delivery_cannot_start(
    db_session: AsyncSession,
) -> None:
    with patch("app.api.v1.endpoints.downloads._validate_urls", AsyncMock()), patch(
        "app.api.v1.endpoints.downloads._queue_download",
        side_effect=RuntimeError("broker unavailable"),
    ):
        result = await start_download(
            DownloadRequest(url="https://example.test/video"), db_session, ADMIN
        )
    assert result.status == "failed"
    repo = DownloadRepository(db_session)
    download = await repo.get_by_id(result.download_id)
    assert download is not None and download.completed_at is not None
    assert (
        await repo.update_status(download.id, "downloading", expected_status="pending")
        is None
    )


async def test_partial_batch_reports_failed_ids_and_continues(
    db_session: AsyncSession,
) -> None:
    publish = Mock(side_effect=[None, RuntimeError("broker unavailable"), None])
    with patch("app.api.v1.endpoints.downloads._validate_urls", AsyncMock()), patch(
        "app.api.v1.endpoints.downloads._queue_download", publish
    ):
        result = await start_batch_download(
            BatchDownloadRequest(urls=[f"https://example.test/{i}" for i in range(3)]),
            db_session,
            ADMIN,
        )
    assert result.status == "partial"
    assert result.failed_downloads == [result.downloads[1]]
    repo = DownloadRepository(db_session)
    for index, download_id in enumerate(result.downloads):
        download = await repo.get_by_id(download_id)
        assert download is not None and download.status == (
            "failed" if index == 1 else "pending"
        )
    assert publish.call_count == 3


async def test_ambiguous_broker_error_preserves_an_already_claimed_task(
    db_session: AsyncSession,
) -> None:
    download = await DownloadRepository(db_session).create(
        "https://example.test/video", status="downloading"
    )
    with patch(
        "app.api.v1.endpoints.downloads._queue_download",
        side_effect=RuntimeError("ack lost"),
    ):
        status = await _dispatch_download(
            db_session, download.id, download.url, "best", None, {}
        )
    assert status == "downloading"


async def test_only_one_worker_can_claim_a_pending_download(
    db_session: AsyncSession,
) -> None:
    download = await DownloadRepository(db_session).create("https://example.test/video")

    async def claim() -> bool:
        async with async_session_maker() as session:
            return (
                await DownloadRepository(session).update_status(
                    download.id, "downloading", expected_status="pending"
                )
                is not None
            )

    assert sorted(await asyncio.gather(claim(), claim())) == [False, True]
