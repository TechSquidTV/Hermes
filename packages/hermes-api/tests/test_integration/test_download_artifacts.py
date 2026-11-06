"""Regressions for interrupted outputs and persisted analytics metadata."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DownloadHistory
from app.db.repositories import DownloadRepository
from app.services.yt_dlp_service import DownloadOutputs
from app.tasks import download_tasks


async def test_failed_download_removes_unregistered_partial_outputs(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    media_root, temp_root = tmp_path / "downloads", tmp_path / "temp"
    media_root.mkdir()
    temp_root.mkdir()
    partials: list[Path] = []

    async def fail_download(**kwargs: object) -> DownloadOutputs:
        partial = Path(str(kwargs["output_path"]).replace("%(ext)s", "mp4") + ".part")
        partial.write_bytes(b"partial media")
        partials.append(partial)
        raise RuntimeError("transfer interrupted")

    download = await DownloadRepository(db_session).create("https://example.test/video")
    monkeypatch.setattr(settings, "download_dir", str(media_root))
    monkeypatch.setattr(settings, "temp_dir", str(temp_root))
    monkeypatch.setattr(download_tasks, "redis_progress_service", AsyncMock())
    monkeypatch.setattr(download_tasks, "_trigger_webhooks", AsyncMock())
    monkeypatch.setattr(
        download_tasks.yt_service,
        "extract_info",
        AsyncMock(return_value={"title": "Video", "extractor": "youtube"}),
    )
    monkeypatch.setattr(download_tasks.yt_service, "download_video", fail_download)
    result = await download_tasks._download_video_task(download.id, download.url)
    assert result["success"] is False
    db_session.expire_all()
    failed = await DownloadRepository(db_session).get_by_id(result["download_id"])
    assert failed is not None and failed.status == "failed"
    assert failed.output_path is None and failed.files == []
    assert not partials[0].exists()
    history = await db_session.scalar(
        select(DownloadHistory).where(
            DownloadHistory.download_id == result["download_id"]
        )
    )
    assert history is not None and history.extractor == "youtube"


async def test_completed_download_history_preserves_extractor_metadata(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def finish_download(**kwargs: object) -> DownloadOutputs:
        output = Path(str(kwargs["output_path"]).replace("%(ext)s", "mp4"))
        output.write_bytes(b"final media")
        return DownloadOutputs(str(output))

    download = await DownloadRepository(db_session).create("https://example.test/video")
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    monkeypatch.setattr(download_tasks, "redis_progress_service", AsyncMock())
    monkeypatch.setattr(download_tasks, "_trigger_webhooks", AsyncMock())
    monkeypatch.setattr(
        download_tasks.yt_service,
        "extract_info",
        AsyncMock(return_value={"title": "Video", "extractor": "youtube", "id": "abc"}),
    )
    monkeypatch.setattr(download_tasks.yt_service, "download_video", finish_download)
    result = await download_tasks._download_video_task(download.id, download.url)
    assert result["success"] is True
    db_session.expire_all()
    history = await db_session.scalar(
        select(DownloadHistory).where(
            DownloadHistory.download_id == result["download_id"]
        )
    )
    assert history is not None and history.extractor == "youtube"
    assert (
        history.video_id == "abc" and history.format_used == "bestvideo*+bestaudio/best"
    )
    completed = await DownloadRepository(db_session).get_by_id(result["download_id"])
    assert completed is not None and completed.extractor == "youtube"
