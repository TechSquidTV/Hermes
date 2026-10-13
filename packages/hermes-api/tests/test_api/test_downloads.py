"""Tests for download endpoint orchestration.

External work queues and Redis are mocked; these tests cover API-owned request
handling, persistence, response shaping, and state transitions.
"""

from unittest.mock import AsyncMock, call, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories import DownloadRepository
from app.utils.media import DEFAULT_FORMAT_SPEC


class TestDownloadEndpoints:
    """Download endpoint behavior that belongs to Hermes."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("format_spec", [None, "bestvideo+bestaudio", "best"])
    async def test_start_download_creates_record_and_queues_task(
        self, client: AsyncClient, db_session: AsyncSession, format_spec: str | None
    ):
        expected_format = format_spec or DEFAULT_FORMAT_SPEC
        with patch(
            "app.api.v1.endpoints.downloads.download_video_task.apply_async"
        ) as apply_async:
            response = await client.post(
                "/api/v1/download/",
                json={
                    "url": "https://example.test/watch",
                    **({"format": format_spec} if format_spec else {}),
                    "outputDirectory": str(settings.download_dir + "/custom"),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["message"] == "Download queued successfully"

        download = await DownloadRepository(db_session).get_by_id(data["downloadId"])
        assert download is not None
        assert download.url == "https://example.test/watch"
        assert download.format_spec == expected_format
        assert download.status == "pending"

        apply_async.assert_called_once_with(
            kwargs={
                "download_id": data["downloadId"],
                "url": "https://example.test/watch",
                "format_spec": expected_format,
                "output_path": str(settings.download_dir + "/custom"),
            },
            task_id=data["downloadId"],
            queue="hermes.downloads",
        )

    @pytest.mark.asyncio
    async def test_start_download_forwards_supported_options(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch(
            "app.api.v1.endpoints.downloads.download_video_task.apply_async"
        ) as apply_async:
            response = await client.post(
                "/api/v1/download/",
                json={
                    "url": "https://example.test/watch",
                    "format": "best",
                    "outputDirectory": str(settings.download_dir + "/custom"),
                    "outputTemplate": "%(title)s.custom.%(ext)s",
                    "downloadSubtitles": True,
                    "downloadThumbnail": True,
                    "subtitleLanguages": ["en", "es"],
                    "cookies": {"session": "abc", "pref": "dark"},
                },
            )

        assert response.status_code == 200
        data = response.json()
        download = await DownloadRepository(db_session).get_by_id(data["downloadId"])
        assert download is not None

        queued_kwargs = apply_async.call_args.kwargs["kwargs"]
        assert queued_kwargs == {
            "download_id": data["downloadId"],
            "url": "https://example.test/watch",
            "format_spec": "best",
            "output_path": str(settings.download_dir + "/custom"),
            "output_template": "%(title)s.custom.%(ext)s",
            "writesubtitles": True,
            "writethumbnail": True,
            "subtitleslangs": ["en", "es"],
            "http_headers": {"Cookie": "session=abc; pref=dark"},
        }
        assert apply_async.call_args.kwargs["queue"] == "hermes.downloads"

    @pytest.mark.asyncio
    async def test_completed_download_persists_full_progress(
        self, db_session: AsyncSession
    ):
        repo = DownloadRepository(db_session)
        download = await repo.create(
            url="https://example.test/watch",
            status="downloading",
            progress=41.5,
        )

        await repo.update_status(download.id, "completed", progress=41.5)
        await db_session.refresh(download)

        assert download.status == "completed"
        assert download.progress == 100.0

    @pytest.mark.asyncio
    async def test_terminal_download_ignores_late_active_progress(
        self, db_session: AsyncSession
    ):
        repo = DownloadRepository(db_session)
        download = await repo.create(
            url="https://example.test/watch",
            status="downloading",
            progress=83.0,
        )

        await repo.update_status(download.id, "completed", progress=100.0)
        await repo.update_status(download.id, "downloading", progress=41.5)
        await db_session.refresh(download)

        assert download.status == "completed"
        assert download.progress == 100.0

    @pytest.mark.asyncio
    async def test_get_download_status_uses_nested_redis_progress_from_task(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        download = await DownloadRepository(db_session).create(
            url="https://example.test/watch",
            status="downloading",
            title="Redis Video",
            progress=12.0,
            downloaded_bytes=120,
            total_bytes=1000,
        )

        redis_payload = {
            "status": "downloading",
            "message": "Downloading: 42.5%",
            "progress": {
                "percentage": 42.5,
                "status": "downloading",
                "downloaded_bytes": 425,
                "total_bytes": 1000,
                "speed": 2048.0,
                "eta": 12.0,
            },
        }

        with patch(
            "app.api.v1.endpoints.downloads.redis_progress_service.get_progress",
            new=AsyncMock(return_value=redis_payload),
        ) as get_progress:
            response = await client.get(f"/api/v1/download/{download.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["downloadId"] == download.id
        assert data["status"] == "downloading"
        assert data["progress"] == {
            "percentage": 42.5,
            "status": "downloading",
            "downloadedBytes": 425,
            "totalBytes": 1000,
            "speed": 2048.0,
            "eta": 12.0,
        }
        assert data["result"]["title"] == "Redis Video"
        get_progress.assert_awaited_once_with(download.id)

    @pytest.mark.asyncio
    async def test_cancel_download_updates_cancellable_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        download = await DownloadRepository(db_session).create(
            url="https://example.test/watch",
            status="pending",
        )

        with (
            patch("app.api.v1.endpoints.downloads.celery_app.control.revoke") as revoke,
            patch(
                "app.api.v1.endpoints.downloads.redis_progress_service", new=AsyncMock()
            ),
        ):
            response = await client.post(f"/api/v1/download/{download.id}/cancel")

        revoke.assert_called_once_with(download.id, terminate=True, signal="SIGTERM")
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "downloadId": download.id,
            "cancelled": True,
            "message": "Download cancelled successfully",
        }

        await db_session.refresh(download)
        assert download.status == "cancelled"
        assert download.error_message == "Cancelled by user"

    @pytest.mark.asyncio
    async def test_cancel_download_rejects_terminal_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        download = await DownloadRepository(db_session).create(
            url="https://example.test/watch",
            status="completed",
        )

        response = await client.post(f"/api/v1/download/{download.id}/cancel")

        assert response.status_code == 200
        assert response.json() == {
            "downloadId": download.id,
            "cancelled": False,
            "message": "Cannot cancel completed download",
        }

        await db_session.refresh(download)
        assert download.status == "completed"

    @pytest.mark.asyncio
    async def test_start_batch_download_creates_records_and_schedules_batch(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch(
            "app.api.v1.endpoints.downloads.download_video_task.apply_async"
        ) as apply_async:
            response = await client.post(
                "/api/v1/download/batch",
                json={
                    "urls": [
                        "https://example.test/one",
                        "https://example.test/two",
                    ],
                    "format": "best",
                    "outputDirectory": str(settings.download_dir + "/batch"),
                    "downloadSubtitles": True,
                    "downloadThumbnail": True,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["batchId"] not in data["downloads"]
        assert data["totalDownloads"] == 2
        assert data["status"] == "queued"
        assert len(data["downloads"]) == 2

        repo = DownloadRepository(db_session)
        downloads = [
            await repo.get_by_id(download_id) for download_id in data["downloads"]
        ]
        assert [download.url for download in downloads] == [
            "https://example.test/one",
            "https://example.test/two",
        ]
        assert [download.status for download in downloads] == ["pending", "pending"]

        assert apply_async.call_args_list == [
            call(
                task_id=download_id,
                kwargs={
                    "download_id": download_id,
                    "url": url,
                    "format_spec": "best",
                    "output_path": str(settings.download_dir + "/batch"),
                    "writesubtitles": True,
                    "writethumbnail": True,
                },
                queue="hermes.downloads",
            )
            for download_id, url in zip(
                data["downloads"],
                ["https://example.test/one", "https://example.test/two"],
                strict=True,
            )
        ]
