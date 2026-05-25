"""Tests for download task orchestration.

These tests mock external boundaries (yt-dlp, Redis, webhooks, and database
writes) so they exercise Hermes' own task state machine and data shaping.
"""

import asyncio
import os
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from app.tasks import download_tasks


def test_sanitize_filename_removes_invalid_characters_and_normalizes_spaces():
    assert (
        download_tasks.sanitize_filename(' My <Great>: "Video" / Part 1?.mp4 ')
        == "My_Great_Video_Part_1.mp4"
    )


def test_sanitize_filename_returns_default_for_empty_result():
    assert download_tasks.sanitize_filename(' <>:"/\\|?* .. ') == "video"


def test_sanitize_filename_limits_very_long_names():
    assert len(download_tasks.sanitize_filename("a" * 250)) == 200


@pytest.mark.asyncio
async def test_publish_sse_progress_shapes_download_status_payload():
    mock_progress_service = AsyncMock()

    with patch.object(download_tasks, "redis_progress_service", mock_progress_service):
        await download_tasks._publish_sse_progress(
            download_id="download-123",
            status="downloading",
            progress=37.5,
            downloaded_bytes=375,
            total_bytes=1000,
            download_speed=42.0,
            eta=9.0,
            result={"title": "Example"},
        )

    mock_progress_service.publish_download_progress.assert_awaited_once_with(
        download_id="download-123",
        progress_data={
            "status": "downloading",
            "message": "Downloading: 37.5%",
            "progress": {
                "percentage": 37.5,
                "status": "downloading",
                "downloaded_bytes": 375,
                "total_bytes": 1000,
                "speed": 42.0,
                "eta": 9.0,
            },
            "result": {"title": "Example"},
        },
    )


@pytest.mark.asyncio
async def test_update_download_status_publishes_cached_db_progress_for_active_status(
    db_session,
):
    from app.db.repositories import DownloadRepository

    repo = DownloadRepository(db_session)
    download = await repo.create(
        url="https://example.test/watch",
        status="downloading",
    )
    await repo.update_status(
        download.id,
        "downloading",
        progress=33.0,
        downloaded_bytes=330,
        total_bytes=1000,
        download_speed=2048.0,
        eta=18.0,
    )

    redis_progress_service = AsyncMock()

    with patch.object(download_tasks, "redis_progress_service", redis_progress_service):
        await download_tasks._update_download_status(download.id, "processing")

    redis_progress_service.publish_download_progress.assert_awaited_once_with(
        download_id=download.id,
        progress_data={
            "status": "processing",
            "error_message": None,
            "progress": {
                "percentage": 33.0,
                "status": "processing",
                "downloaded_bytes": 330,
                "total_bytes": 1000,
                "speed": 2048.0,
                "eta": 18.0,
            },
        },
    )
    redis_progress_service.publish_queue_update.assert_awaited_once_with(
        action="status_changed",
        download_id=download.id,
        data={"status": "processing"},
    )


@pytest.mark.asyncio
async def test_download_video_task_success_updates_metadata_and_cleans_up(tmp_path):
    download_file = tmp_path / "Dangerous_Title.mp4"
    yt_service = AsyncMock()
    yt_service.extract_info.return_value = {
        "title": 'Dangerous: "Title"?',
        "thumbnail": "https://example.test/thumb.jpg",
        "extractor": "ExampleSite",
        "description": "An example video",
        "duration": 123,
    }

    async def fake_download_video(
        url, output_path, format_spec, progress_callback=None, **kwargs
    ):
        assert url == "https://example.test/watch"
        assert output_path == os.path.join(str(tmp_path), "Dangerous_Title.%(ext)s")
        assert format_spec == "bestvideo+bestaudio"
        assert kwargs == {"merge_output_format": "mp4"}
        download_file.write_bytes(b"video")
        return str(download_file)

    yt_service.download_video.side_effect = fake_download_video

    update_status = AsyncMock()
    create_history = AsyncMock()
    trigger_webhooks = AsyncMock()
    redis_progress_service = AsyncMock()
    redis_progress_service.revoke_user_sse_tokens.return_value = 2

    with (
        patch.object(download_tasks, "yt_service", yt_service),
        patch.object(download_tasks, "_update_download_status", update_status),
        patch.object(download_tasks, "_create_download_history", create_history),
        patch.object(download_tasks, "_trigger_webhooks", trigger_webhooks),
        patch.object(download_tasks, "redis_progress_service", redis_progress_service),
    ):
        result = await download_tasks._download_video_task(
            download_id="download-123",
            url="https://example.test/watch",
            format_spec="bestvideo+bestaudio",
            output_path=str(tmp_path),
            merge_output_format="mp4",
        )

    assert result == {
        "success": True,
        "download_id": "download-123",
        "file_path": str(download_file),
        "file_size": 5,
    }
    yt_service.extract_info.assert_awaited_once_with(
        "https://example.test/watch", download=False
    )
    yt_service.download_video.assert_awaited_once()

    initial_status_call = update_status.await_args_list[0]
    assert initial_status_call.args == ("download-123", "downloading")
    assert initial_status_call.kwargs["started_at"].tzinfo is not None
    assert update_status.await_args_list[1] == call(
        "download-123",
        "downloading",
        title='Dangerous: "Title"?',
        thumbnail_url="https://example.test/thumb.jpg",
        extractor="ExampleSite",
        description="An example video",
        duration=123,
        result={
            "url": "https://example.test/watch",
            "title": 'Dangerous: "Title"?',
            "thumbnail_url": "https://example.test/thumb.jpg",
            "extractor": "ExampleSite",
            "description": "An example video",
            "duration": 123,
        },
    )
    completed_call = update_status.await_args_list[2]
    assert completed_call.args == ("download-123", "completed")
    assert completed_call.kwargs["progress"] == 100.0
    assert completed_call.kwargs["file_size"] == 5
    assert completed_call.kwargs["output_path"] == str(download_file)
    assert completed_call.kwargs["result"] == {
        "url": "https://example.test/watch",
        "title": 'Dangerous: "Title"?',
        "file_size": 5,
        "duration": 123,
        "thumbnail_url": "https://example.test/thumb.jpg",
        "extractor": "ExampleSite",
        "description": "An example video",
    }

    create_history.assert_awaited_once()
    assert create_history.await_args.kwargs["download_id"] == "download-123"
    assert create_history.await_args.kwargs["status"] == "completed"
    assert create_history.await_args.kwargs["file_size"] == 5

    assert trigger_webhooks.await_args_list[0] == call(
        "download_started", "download-123", {"url": "https://example.test/watch"}
    )
    assert trigger_webhooks.await_args_list[1] == call(
        "download_completed",
        "download-123",
        {
            "url": "https://example.test/watch",
            "file_path": str(download_file),
            "file_size": 5,
        },
    )
    redis_progress_service.publish_stats_update.assert_awaited_once()
    redis_progress_service.delete_progress.assert_awaited_once_with("download-123")
    redis_progress_service.revoke_user_sse_tokens.assert_awaited_once_with(
        user_id="*", scope_prefix="download:download-123"
    )


@pytest.mark.asyncio
async def test_download_video_task_extract_failure_marks_failed_and_cleans_up():
    yt_service = AsyncMock()
    yt_service.extract_info.return_value = None

    update_status = AsyncMock()
    create_history = AsyncMock()
    trigger_webhooks = AsyncMock()
    redis_progress_service = AsyncMock()
    redis_progress_service.revoke_user_sse_tokens.return_value = 0

    with (
        patch.object(download_tasks, "yt_service", yt_service),
        patch.object(download_tasks, "_update_download_status", update_status),
        patch.object(download_tasks, "_create_download_history", create_history),
        patch.object(download_tasks, "_trigger_webhooks", trigger_webhooks),
        patch.object(download_tasks, "redis_progress_service", redis_progress_service),
    ):
        result = await download_tasks._download_video_task(
            download_id="download-123",
            url="https://example.test/watch",
        )

    assert result == {
        "success": False,
        "download_id": "download-123",
        "error": "Failed to extract video information",
    }
    yt_service.download_video.assert_not_awaited()

    failed_call = update_status.await_args_list[-1]
    assert failed_call.args == ("download-123", "failed")
    assert failed_call.kwargs["error_message"] == "Failed to extract video information"

    create_history.assert_awaited_once()
    assert create_history.await_args.kwargs["status"] == "failed"
    assert (
        create_history.await_args.kwargs["error_message"]
        == "Failed to extract video information"
    )
    assert trigger_webhooks.await_args_list[-1] == call(
        "download_failed",
        "download-123",
        {
            "url": "https://example.test/watch",
            "error": "Failed to extract video information",
        },
    )
    redis_progress_service.delete_progress.assert_awaited_once_with("download-123")
    redis_progress_service.revoke_user_sse_tokens.assert_awaited_once_with(
        user_id="*", scope_prefix="download:download-123"
    )


@pytest.mark.asyncio
async def test_download_video_task_missing_file_marks_failed(tmp_path):
    yt_service = AsyncMock()
    yt_service.extract_info.return_value = {"title": "Missing File"}
    yt_service.download_video.return_value = str(tmp_path / "missing-file.mp4")

    update_status = AsyncMock()
    create_history = AsyncMock()
    trigger_webhooks = AsyncMock()
    redis_progress_service = AsyncMock()

    with (
        patch.object(download_tasks, "yt_service", yt_service),
        patch.object(download_tasks, "_update_download_status", update_status),
        patch.object(download_tasks, "_create_download_history", create_history),
        patch.object(download_tasks, "_trigger_webhooks", trigger_webhooks),
        patch.object(download_tasks, "redis_progress_service", redis_progress_service),
    ):
        result = await download_tasks._download_video_task(
            download_id="download-123",
            url="https://example.test/watch",
            output_path=str(tmp_path),
        )

    assert result == {
        "success": False,
        "download_id": "download-123",
        "error": "Download completed but file not found",
    }
    failed_call = update_status.await_args_list[-1]
    assert failed_call.args == ("download-123", "failed")
    assert (
        failed_call.kwargs["error_message"] == "Download completed but file not found"
    )
    assert create_history.await_args.kwargs["status"] == "failed"
    assert (
        create_history.await_args.kwargs["error_message"]
        == "Download completed but file not found"
    )
    assert trigger_webhooks.await_args_list[-1] == call(
        "download_failed",
        "download-123",
        {
            "url": "https://example.test/watch",
            "error": "Download completed but file not found",
        },
    )
    redis_progress_service.delete_progress.assert_awaited_once_with("download-123")


@pytest.mark.asyncio
async def test_download_progress_hook_normalizes_progress_and_keeps_metadata(tmp_path):
    download_file = tmp_path / "Progress_Video.mp4"
    scheduled_coroutines = []
    yt_service = AsyncMock()
    yt_service.extract_info.return_value = {
        "title": "Progress Video",
        "thumbnail": "https://example.test/thumb.jpg",
        "extractor": "ExampleSite",
        "description": "Progress example",
        "duration": 99,
    }

    async def fake_download_video(
        url, output_path, format_spec, progress_callback=None, **kwargs
    ):
        assert progress_callback is not None
        progress_callback(
            {
                "status": "downloading",
                "downloaded_bytes": 500,
                "total_bytes": 100,
                "speed": 12,
                "eta": 3,
            }
        )
        progress_callback(
            {
                "status": "downloading",
                "downloaded_bytes": 50,
                "total_bytes": 100,
                "speed": 8.5,
                "eta": 2.5,
            }
        )
        download_file.write_bytes(b"video")
        return str(download_file)

    def fake_run_coroutine_threadsafe(coro, loop):
        scheduled_coroutines.append(coro)
        coro.close()
        return Mock()

    yt_service.download_video.side_effect = fake_download_video

    update_status = AsyncMock()
    create_history = AsyncMock()
    trigger_webhooks = AsyncMock()
    redis_progress_service = Mock()
    redis_progress_service.publish_stats_update = AsyncMock()
    redis_progress_service.delete_progress = AsyncMock()
    redis_progress_service.revoke_user_sse_tokens = AsyncMock(return_value=0)

    with (
        patch.object(download_tasks, "yt_service", yt_service),
        patch.object(download_tasks, "_update_download_status", update_status),
        patch.object(download_tasks, "_create_download_history", create_history),
        patch.object(download_tasks, "_trigger_webhooks", trigger_webhooks),
        patch.object(download_tasks, "redis_progress_service", redis_progress_service),
        patch.object(
            asyncio,
            "run_coroutine_threadsafe",
            side_effect=fake_run_coroutine_threadsafe,
        ),
        patch.object(download_tasks.time, "time", side_effect=[10.0, 12.5]),
    ):
        result = await download_tasks._download_video_task(
            download_id="download-123",
            url="https://example.test/watch",
            output_path=str(tmp_path),
        )

    assert result["success"] is True
    assert len(scheduled_coroutines) == 4

    first_progress = redis_progress_service.set_progress_sync.call_args_list[0].args[1]
    assert first_progress["message"] == "Downloading: 5.0%"
    assert first_progress["progress"] == {
        "percentage": 5.0,
        "status": "downloading",
        "downloaded_bytes": 500,
        "total_bytes": 100,
        "speed": 12.0,
        "eta": 3.0,
    }
    assert first_progress["result"] == {
        "url": "https://example.test/watch",
        "title": "Progress Video",
        "thumbnail_url": "https://example.test/thumb.jpg",
        "extractor": "ExampleSite",
        "description": "Progress example",
        "duration": 99,
    }

    second_progress = redis_progress_service.set_progress_sync.call_args_list[1].args[1]
    assert second_progress["message"] == "Downloading: 50.0%"
    assert second_progress["progress"]["percentage"] == 50.0
    assert second_progress["progress"]["speed"] == 8.5
    assert second_progress["progress"]["eta"] == 2.5


@pytest.mark.asyncio
async def test_batch_download_task_aggregates_results_and_triggers_webhooks():
    download_task = AsyncMock(
        side_effect=[
            {"success": True, "download_id": "download-1", "file_size": 100},
            {"success": False, "download_id": "download-2", "error": "failed"},
        ]
    )
    trigger_webhooks = AsyncMock()

    with (
        patch.object(download_tasks, "_download_video_task", download_task),
        patch.object(download_tasks, "_trigger_webhooks", trigger_webhooks),
    ):
        result = await download_tasks._batch_download_task(
            download_ids=["download-1", "download-2"],
            urls=["https://example.test/one", "https://example.test/two"],
            format_spec="best",
            output_directory="/downloads/batch",
            write_thumbnail=True,
        )

    assert result == {
        "batch_id": "batch_2_urls",
        "total_downloads": 2,
        "successful_downloads": 1,
        "results": [
            {"success": True, "download_id": "download-1", "file_size": 100},
            {"success": False, "download_id": "download-2", "error": "failed"},
        ],
    }
    assert download_task.await_args_list == [
        call(
            download_id="download-1",
            url="https://example.test/one",
            format_spec="best",
            output_path="/downloads/batch",
            write_thumbnail=True,
        ),
        call(
            download_id="download-2",
            url="https://example.test/two",
            format_spec="best",
            output_path="/downloads/batch",
            write_thumbnail=True,
        ),
    ]
    assert trigger_webhooks.await_args_list == [
        call(
            "batch_download_started",
            "batch_2_urls",
            {
                "urls": ["https://example.test/one", "https://example.test/two"],
                "total_videos": 2,
            },
        ),
        call(
            "batch_download_completed",
            "batch_2_urls",
            {
                "total_videos": 2,
                "successful_downloads": 1,
                "failed_downloads": 1,
                "results": [
                    {"success": True, "download_id": "download-1", "file_size": 100},
                    {"success": False, "download_id": "download-2", "error": "failed"},
                ],
            },
        ),
    ]
