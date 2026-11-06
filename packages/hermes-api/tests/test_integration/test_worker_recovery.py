"""Worker loss recovers without resetting live work or allowing late completion."""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import async_session_maker
from app.db.models import DownloadFile, DownloadHistory
from app.db.repositories import DownloadRepository
from app.services import worker_health
from app.services.yt_dlp_service import DownloadOutputs
from app.tasks import download_tasks
from app.tasks.cleanup_tasks import _cleanup_temp_files_async
from app.utils.dates import as_utc


@pytest.fixture(autouse=True)
def isolate_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    progress = AsyncMock()
    monkeypatch.setattr(worker_health, "redis_progress_service", progress)
    monkeypatch.setattr(download_tasks, "redis_progress_service", progress)
    monkeypatch.setattr(download_tasks, "_trigger_webhooks", AsyncMock())


async def test_recovery_is_atomic_and_preserves_live_pending_and_terminal_tasks(
    db_session: AsyncSession,
) -> None:
    repo = DownloadRepository(db_session)
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired = []
    for status, heartbeat in (
        ("downloading", old),
        ("processing", None),
        ("downloading", datetime.now(timezone.utc)),
        ("pending", None),
        ("completed", old),
        ("cancelled", old),
    ):
        record = await repo.create(
            "https://example.test/video",
            status=status,
            started_at=old,
            last_heartbeat_at=heartbeat,
        )
        if status == "processing" or (status == "downloading" and heartbeat == old):
            expired.append(record.id)
    results = await asyncio.gather(
        worker_health.recover_abandoned_downloads(),
        worker_health.recover_abandoned_downloads(),
    )
    assert sorted(item for group in results for item in group) == sorted(expired)
    assert (
        await db_session.scalar(select(func.count()).select_from(DownloadHistory)) == 2
    )
    db_session.expire_all()
    for download_id in expired:
        failed_record = await repo.get_by_id(download_id)
        assert (
            failed_record is not None
            and failed_record.status == "failed"
            and failed_record.completed_at
        )
    assert await worker_health.recover_abandoned_downloads() == []


async def test_worker_interruption_becomes_failed_and_partial_can_be_cleaned(
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path / "temp"))
    monkeypatch.setattr(
        download_tasks.yt_service,
        "extract_info",
        AsyncMock(return_value={"title": "Video"}),
    )
    partials: list[Path] = []

    async def interrupted(**kwargs: object) -> None:
        path = Path(str(kwargs["output_path"]).replace("%(ext)s", "mp4") + ".part")
        path.write_bytes(b"interrupted")
        old = (datetime.now(timezone.utc) - timedelta(days=3)).timestamp()
        os.utime(path, (old, old))
        partials.append(path)
        raise asyncio.CancelledError("worker interrupted")

    downloader = AsyncMock(side_effect=interrupted)
    monkeypatch.setattr(download_tasks.yt_service, "download_video", downloader)
    record = await DownloadRepository(db_session).create("https://example.test/video")
    download_id, url = record.id, record.url
    with pytest.raises(asyncio.CancelledError):
        await download_tasks._download_video_task(download_id, url)
    db_session.expire_all()
    stranded = await DownloadRepository(db_session).get_by_id(download_id)
    assert stranded is not None and stranded.status == "downloading"
    stranded.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    await db_session.commit()
    assert await worker_health.recover_abandoned_downloads() == [download_id]
    assert (await download_tasks._download_video_task(download_id, url))[
        "success"
    ] is False
    assert downloader.await_count == 1
    assert (await _cleanup_temp_files_async())["deleted_files"] == 1 and not partials[
        0
    ].exists()
    assert getattr(download_tasks.download_video_task, "acks_late") is True
    assert getattr(download_tasks.download_video_task, "reject_on_worker_lost") is True


async def test_heartbeat_keeps_idle_live_work_and_stops_on_cancellation(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(worker_health, "HEARTBEAT_INTERVAL", 0.01)
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    record = await DownloadRepository(db_session).create(
        "https://example.test/video", status="downloading", last_heartbeat_at=old
    )
    download_id = record.id
    async with worker_health.download_heartbeat(download_id) as stopped:
        for _ in range(50):
            await asyncio.sleep(0.02)
            await db_session.refresh(record)
            if record.last_heartbeat_at and as_utc(record.last_heartbeat_at) > old:
                break
        assert record.last_heartbeat_at and as_utc(record.last_heartbeat_at) > old
        assert await worker_health.recover_abandoned_downloads() == []
        await DownloadRepository(db_session).update_status(download_id, "cancelled")
        for _ in range(50):
            await asyncio.sleep(0.02)
            if stopped.is_set():
                break
        assert stopped.is_set()


async def test_reaper_fences_late_completion_and_preserves_one_history_record(
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = await DownloadRepository(db_session).create("https://example.test/video")
    download_id, url = record.id, record.url
    final = tmp_path / f"{download_id}_video.mp4"
    monkeypatch.setattr(
        download_tasks.yt_service,
        "extract_info",
        AsyncMock(return_value={"title": "Video"}),
    )

    async def expired_download(**kwargs: object) -> DownloadOutputs:
        final.write_bytes(b"media")
        async with async_session_maker() as session:
            active = await DownloadRepository(session).get_by_id(download_id)
            assert active is not None
            active.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(
                minutes=10
            )
            await session.commit()
        assert await worker_health.recover_abandoned_downloads() == [download_id]
        return DownloadOutputs(str(final))

    monkeypatch.setattr(download_tasks.yt_service, "download_video", expired_download)
    assert (await download_tasks._download_video_task(download_id, url))[
        "success"
    ] is False
    assert not final.exists()
    assert await db_session.scalar(select(func.count()).select_from(DownloadFile)) == 0
    assert (
        await db_session.scalar(select(func.count()).select_from(DownloadHistory)) == 1
    )


async def test_api_monitor_stops_its_background_work_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recover = AsyncMock(return_value=[])
    monkeypatch.setattr(worker_health, "recover_abandoned_downloads", recover)
    monkeypatch.setattr(worker_health, "HEARTBEAT_INTERVAL", 0.01)
    async with worker_health.download_monitor():
        for _ in range(50):
            await asyncio.sleep(0.01)
            if recover.await_count:
                break
        assert recover.await_count
    calls = recover.await_count
    await asyncio.sleep(0.03)
    assert recover.await_count == calls
