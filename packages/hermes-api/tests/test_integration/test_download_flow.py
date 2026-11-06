"""Exercise worker completion and repair against the real database and file API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.yt_dlp_service import DownloadOutputs

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.base import async_session_maker
from app.db.models import Download, DownloadFile
from app.db.repositories import DownloadFileRepository, DownloadRepository
from app.services.download_files import backfill_download_files
from app.tasks import download_tasks


@pytest.fixture
def worker_boundaries(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock]:
    """Mock network services while keeping all worker database writes real."""
    yt_service = AsyncMock()
    yt_service.extract_info.return_value = {"title": "Completed video", "duration": 12}
    progress_service = AsyncMock()
    progress_service.revoke_user_sse_tokens.return_value = 0
    monkeypatch.setattr(download_tasks, "yt_service", yt_service)
    monkeypatch.setattr(download_tasks, "redis_progress_service", progress_service)
    monkeypatch.setattr(download_tasks, "_trigger_webhooks", AsyncMock())
    return yt_service, progress_service


@pytest.mark.parametrize(
    ("extension", "file_type"),
    [("mp4", "video"), ("m4a", "audio"), ("opus", "audio")],
)
async def test_worker_completion_registers_retrievable_file(
    client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker_boundaries: tuple[AsyncMock, AsyncMock],
    extension: str,
    file_type: str,
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch"
    )
    download_id = download.id
    yt_service, progress_service = worker_boundaries
    final_path = tmp_path / f"Completed_video.{extension}"
    content = b"postprocessed media bytes"

    async def write_output(**kwargs: object) -> DownloadOutputs:
        # The worker must use the same configured directory as the file API.
        assert kwargs["output_path"] == str(
            tmp_path / f"{download_id}_Completed_video.%(ext)s"
        )
        final_path.write_bytes(content)
        return DownloadOutputs(str(final_path))

    yt_service.download_video.side_effect = write_output

    async def verify_completion_visible(
        *, download_id: str, progress_data: dict[str, object]
    ) -> None:
        if progress_data["status"] == "completed":
            async with async_session_maker() as session:
                completed = await DownloadRepository(session).get_by_id(download_id)
                assert completed is not None
                assert completed.status == "completed"
                assert len(completed.files) == 1
            response = await client.get(
                "/api/v1/files/download", params={"path": str(final_path)}
            )
            assert response.status_code == 200
            assert response.content == content

    progress_service.publish_download_progress.side_effect = verify_completion_visible

    result = await download_tasks._download_video_task(download_id, download.url)
    assert result["success"] is True

    async with async_session_maker() as session:
        completed = await DownloadRepository(session).get_by_id(download_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.output_path == str(final_path.resolve())
        assert completed.file_size == len(content)
        assert len(completed.files) == 1
        file_record = completed.files[0]
        assert file_record.download_id == download_id
        assert file_record.filepath == str(final_path.resolve())
        assert file_record.filename == final_path.name
        assert file_record.file_size == len(content)
        assert file_record.file_type == file_type
        file_id = file_record.id

    # Replaying completion must reuse the worker's record, including an aliased path.
    await download_tasks._update_download_status(
        download_id,
        "completed",
        outputs=DownloadOutputs(str(tmp_path / "subdir" / ".." / final_path.name)),
    )
    async with async_session_maker() as session:
        files = await DownloadFileRepository(session).get_by_download_id(download_id)
        assert [file.id for file in files] == [file_id]

    response = await client.get(
        "/api/v1/files/download", params={"path": str(final_path)}
    )
    assert response.status_code == 200
    assert response.content == content
    assert final_path.name in response.headers["content-disposition"]


async def test_completion_rolls_back_file_registration_when_status_write_fails(
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    final_path = tmp_path / "video.mp4"
    final_path.write_bytes(b"video")
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch", status="downloading"
    )

    # Violating the existing NOT NULL constraint fails the completion commit
    # after the registration SQL has run, so both writes must roll back.
    with pytest.raises(IntegrityError):
        await download_tasks._update_download_status(
            download.id, "completed", outputs=DownloadOutputs(str(final_path)), url=None
        )

    async with async_session_maker() as session:
        unchanged = await DownloadRepository(session).get_by_id(download.id)
        assert unchanged is not None
        assert unchanged.status == "downloading"
        assert unchanged.files == []
    worker_boundaries[1].publish_download_progress.assert_not_awaited()


async def test_simultaneous_completion_retries_create_one_file_record(
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    final_path = tmp_path / "video.mp4"
    final_path.write_bytes(b"video")
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch", status="downloading"
    )

    await asyncio.gather(
        *(
            download_tasks._update_download_status(
                download.id, "completed", outputs=DownloadOutputs(str(final_path))
            )
            for _ in range(4)
        )
    )
    async with async_session_maker() as session:
        completed = await DownloadRepository(session).get_by_id(download.id)
        assert completed is not None
        assert completed.status == "completed"
        assert len(completed.files) == 1


async def test_completion_does_not_commit_when_registration_fails(
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch", status="downloading"
    )
    with pytest.raises(FileNotFoundError):
        await download_tasks._update_download_status(
            download.id,
            "completed",
            outputs=DownloadOutputs(str(tmp_path / "missing.mp4")),
        )
    async with async_session_maker() as session:
        unchanged = await DownloadRepository(session).get_by_id(download.id)
        assert unchanged is not None
        assert unchanged.status == "downloading"
        assert unchanged.files == []
    worker_boundaries[1].publish_download_progress.assert_not_awaited()


async def test_startup_repairs_completed_download_without_redownloading(
    client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    from app.main import app, lifespan

    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path / "temp"))
    final_path = tmp_path / "existing.mp4"
    final_path.write_bytes(b"already downloaded")
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch",
        status="completed",
        output_path=str(final_path),
        file_size=1,
    )

    response = await client.get(
        "/api/v1/files/download", params={"path": str(final_path)}
    )
    assert response.status_code == 404

    async with lifespan(app):
        response = await client.get(
            "/api/v1/files/download", params={"path": str(final_path)}
        )
        assert response.status_code == 200
        assert response.content == b"already downloaded"

    async with async_session_maker() as session:
        assert await backfill_download_files(session) == 0
        files = await DownloadFileRepository(session).get_by_download_id(download.id)
        assert len(files) == 1
        assert files[0].file_size == final_path.stat().st_size
    worker_boundaries[0].download_video.assert_not_awaited()


async def test_repair_skips_unsafe_missing_and_incomplete_outputs(
    client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "downloads"
    root.mkdir()
    monkeypatch.setattr(settings, "download_dir", str(root))
    outside = tmp_path / "downloads-other" / "secret.mp4"
    outside.parent.mkdir()
    outside.write_bytes(b"private")
    escaped = root / "escaped.mp4"
    escaped.symlink_to(outside)
    dangling = root / "dangling.mp4"
    dangling.symlink_to(root / "missing.mp4")
    pending = root / "pending.mp4"
    pending.write_bytes(b"partial")
    untracked = root / "untracked.mp4"
    untracked.write_bytes(b"untracked")
    for path, status in [
        (outside, "completed"),
        (escaped, "completed"),
        (dangling, "completed"),
        (root / "missing.mp4", "completed"),
        (root, "completed"),
        (pending, "downloading"),
    ]:
        await DownloadRepository(db_session).create(
            url="https://example.test/watch", status=status, output_path=str(path)
        )

    assert await backfill_download_files(db_session) == 0
    assert list(await db_session.scalars(select(DownloadFile))) == []
    for path in [outside, escaped, dangling, pending, untracked]:
        response = await client.get(
            "/api/v1/files/download", params={"path": str(path)}
        )
        assert response.status_code == 404
    assert outside.read_bytes() == b"private"


async def test_managed_file_symlink_escape_is_rejected_after_registration(
    client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    root = tmp_path / "downloads"
    root.mkdir()
    monkeypatch.setattr(settings, "download_dir", str(root))
    final_path = root / "video.mp4"
    final_path.write_bytes(b"video")
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch"
    )
    await download_tasks._update_download_status(
        download.id, "completed", outputs=DownloadOutputs(str(final_path))
    )
    outside = tmp_path / "secret.mp4"
    outside.write_bytes(b"private")
    final_path.unlink()
    final_path.symlink_to(outside)

    response = await client.get(
        "/api/v1/files/download", params={"path": str(final_path)}
    )
    assert response.status_code == 404
    response = await client.request(
        "DELETE", "/api/v1/files/", json={"files": [str(final_path)], "confirm": True}
    )
    assert response.json()["deletedFiles"] == 0
    assert response.json()["failedDeletions"]
    assert outside.read_bytes() == b"private"


async def test_repair_covers_all_batches_and_preserves_existing_records(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    for index in range(105):
        path = tmp_path / f"{index}.mp4"
        path.write_bytes(b"video")
        db_session.add(
            Download(
                id=f"download-{index:03}",
                url="https://example.test/watch",
                status="completed",
                output_path=str(path),
            )
        )
    await db_session.commit()
    existing = await DownloadFileRepository(db_session).create(
        download_id="download-000",
        filename="original.mp4",
        filepath=str(tmp_path / "000" / ".." / "0.mp4"),
        file_size=5,
        file_type="video",
    )
    # Simulate a legacy noncanonical database row, bypassing canonical writes.
    existing.filepath = str(tmp_path / "000" / ".." / "0.mp4")
    await db_session.commit()
    assert await backfill_download_files(db_session) == 105
    assert await backfill_download_files(db_session) == 0
    files = list(await db_session.scalars(select(DownloadFile)))
    assert len(files) == 105
    assert [file.id for file in files if file.download_id == "download-000"] == [
        existing.id
    ]


async def test_authenticated_worker_registers_all_deliverables_and_cleans_them(
    client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    worker_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    from app.tasks.cleanup_tasks import _cleanup_download_files

    service, _ = worker_boundaries
    headers = {"Cookie": "session=provided", "Authorization": "Bearer test"}

    async def authenticated_metadata(
        url: str, download: bool, **options: object
    ) -> dict[str, object]:
        assert options["http_headers"] == headers
        assert download is False
        return {"title": "Authenticated media"}

    files = tuple(tmp_path / f"output{ext}" for ext in (".mp4", ".en.vtt", ".jpg"))

    async def authenticated_download(**options: object) -> DownloadOutputs:
        assert options["http_headers"] == headers
        for path in files:
            path.write_bytes(b"deliverable")
        return DownloadOutputs(str(files[0]), tuple(str(path) for path in files[1:]))

    service.extract_info.side_effect = authenticated_metadata
    service.download_video.side_effect = authenticated_download
    download = await DownloadRepository(db_session).create(
        url="https://example.test/private"
    )
    result = await download_tasks._download_video_task(
        download.id, download.url, http_headers=headers
    )
    assert result["success"] is True
    async with async_session_maker() as session:
        records = await DownloadFileRepository(session).get_by_download_id(download.id)
        assert {record.file_type for record in records} == {
            "video",
            "subtitle",
            "thumbnail",
        }
        assert {record.filepath for record in records} == {str(path) for path in files}
    listing = await client.get("/api/v1/files/")
    assert listing.json()["totalFiles"] == 3
    for path in files:
        response = await client.get(
            "/api/v1/files/download", params={"path": path.name}
        )
        assert response.status_code == 200
        assert response.content == b"deliverable"

    # Removing the main file must preserve the parent's registered sidecars.
    deleted = await client.request(
        "DELETE", "/api/v1/files/", json={"files": [str(files[0])], "confirm": True}
    )
    assert deleted.json()["deletedFiles"] == 1
    listing = await client.get("/api/v1/files/")
    assert listing.json()["totalFiles"] == 2
    cleaned = await _cleanup_download_files([download.id])
    assert cleaned["deleted_files"] == 2
    assert cleaned["failed_files"] == 0
    assert not any(path.exists() for path in files)


async def test_sidecar_registration_failure_rolls_back_completion(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    media = tmp_path / "media.mp4"
    media.write_bytes(b"media")
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch"
    )
    outputs = DownloadOutputs(str(media), (str(tmp_path / "missing.vtt"),))
    with pytest.raises(FileNotFoundError):
        await download_tasks._update_download_status(
            download.id,
            "completed",
            outputs=outputs,
            publish_sse=False,
        )
    async with async_session_maker() as session:
        current = await DownloadRepository(session).get_by_id(download.id)
        assert current is not None
        assert current.status == "pending"
        assert current.files == []


async def test_cancellation_removes_all_unregistered_outputs(
    db_session: AsyncSession,
    tmp_path: Path,
    worker_boundaries: tuple[AsyncMock, AsyncMock],
) -> None:
    service, _ = worker_boundaries
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch"
    )
    download_id = download.id
    paths = tuple(tmp_path / f"cancelled{ext}" for ext in (".mp4", ".en.vtt", ".jpg"))

    async def cancel_while_downloading(**options: object) -> DownloadOutputs:
        for path in paths:
            path.write_bytes(b"output")
        async with async_session_maker() as session:
            await DownloadRepository(session).update_status(download_id, "cancelled")
        return DownloadOutputs(str(paths[0]), tuple(str(path) for path in paths[1:]))

    service.download_video.side_effect = cancel_while_downloading
    result = await download_tasks._download_video_task(download_id, download.url)
    assert result["success"] is False
    assert not any(path.exists() for path in paths)
    async with async_session_maker() as session:
        current = await DownloadRepository(session).get_by_id(download_id)
        assert current is not None
        assert current.status == "cancelled"
        assert current.files == []
