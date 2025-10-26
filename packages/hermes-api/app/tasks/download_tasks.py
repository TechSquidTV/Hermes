"""
Celery tasks for video downloading operations.
"""

import asyncio
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery import current_task

from app.core.logging import get_logger
from app.db.base import async_session_maker
from app.db.repositories import (
    DownloadHistoryRepository,
    DownloadRepository,
    WebhookRepository,
)
from app.services.yt_dlp_service import YTDLPService

logger = get_logger(__name__)
yt_service = YTDLPService()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.

    Args:
        filename: The filename to sanitize

    Returns:
        A safe filename with spaces replaced by underscores and invalid chars removed
    """
    # Remove or replace invalid characters
    # Remove: < > : " / \ | ? *
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Replace multiple underscores with single underscore
    filename = re.sub(r"_+", "_", filename)

    # Remove leading/trailing underscores and dots
    filename = filename.strip("_.")

    # Limit filename length (keep extension)
    max_length = 200
    if len(filename) > max_length:
        name_part = filename[:max_length]
        filename = name_part

    return filename or "video"


async def _update_download_status(
    download_id: str,
    status: str,
    progress: float = None,
    error_message: str = None,
    **kwargs,
) -> None:
    """Helper function to update download status."""
    async with async_session_maker() as session:
        repos = {
            "downloads": DownloadRepository(session),
            "history": DownloadHistoryRepository(session),
        }
        await repos["downloads"].update_status(
            download_id=download_id,
            status=status,
            progress=progress,
            error_message=error_message,
            **kwargs,
        )


async def _create_download_history(
    download_id: str,
    url: str,
    status: str,
    started_at: datetime,
    completed_at: datetime,
    **kwargs,
) -> None:
    """Helper function to create download history record."""
    async with async_session_maker() as session:
        repos = {
            "downloads": DownloadRepository(session),
            "history": DownloadHistoryRepository(session),
        }
        await repos["history"].create(
            download_id=download_id,
            url=url,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            **kwargs,
        )


async def _trigger_webhooks(event: str, download_id: str, data: Dict[str, Any]) -> None:
    """Helper function to trigger webhooks for an event."""
    try:
        async with async_session_maker() as session:
            repos = {
                "downloads": DownloadRepository(session),
                "history": DownloadHistoryRepository(session),
                "webhooks": WebhookRepository(session),
            }
            webhooks = await repos["webhooks"].get_webhooks_for_event(event)

            for webhook in webhooks:
                # TODO: Implement webhook triggering with retry logic
                logger.info(
                    f"Webhook triggered for {event}",
                    webhook_id=webhook.id,
                    download_id=download_id,
                )
                await repos["webhooks"].update_last_triggered(webhook.id)

    except Exception as e:
        logger.error("Failed to trigger webhooks", event=event, error=str(e))


async def _download_video_task(
    download_id: str,
    url: str,
    format_spec: str = "best",
    output_path: str = None,
    **kwargs,
) -> Dict[str, Any]:
    """Core download logic."""
    started_at = datetime.now(timezone.utc)

    try:
        # Update status to downloading
        await _update_download_status(download_id, "downloading", started_at=started_at)

        # Trigger download started webhook
        await _trigger_webhooks("download_started", download_id, {"url": url})

        # First, extract info to get the video title and metadata
        video_info = await yt_service.extract_info(url, download=False)

        if not video_info:
            raise Exception("Failed to extract video information")

        # Get and sanitize the video title for filename
        video_title = video_info.get("title", f"video_{download_id}")
        sanitized_title = sanitize_filename(video_title)

        # Extract metadata for storage
        thumbnail_url = video_info.get("thumbnail")
        extractor = video_info.get("extractor")
        description = video_info.get("description")
        duration = video_info.get("duration")

        # Update download with title and metadata
        await _update_download_status(
            download_id,
            "downloading",
            title=video_title,
            thumbnail_url=thumbnail_url,
            extractor=extractor,
            description=description,
            duration=duration,
        )

        # Generate output path if not provided
        if not output_path:
            output_path = os.path.join(
                os.getenv("HERMES_DOWNLOADS_DIR", "./downloads"),
                f"{sanitized_title}.%(ext)s",
            )
        else:
            # If custom path provided, still use sanitized title
            output_path = os.path.join(output_path, f"{sanitized_title}.%(ext)s")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Download the video
        result_path = await yt_service.download_video(
            url=url, output_path=output_path, format_spec=format_spec, **kwargs
        )

        if result_path and os.path.exists(result_path):
            # Ensure the file has a proper extension
            if not result_path.lower().endswith(
                (".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".3gp", ".m4v")
            ):
                # Try to find the correct file with extension
                directory = os.path.dirname(result_path)
                base_name = os.path.basename(result_path)

                for ext in [
                    ".mp4",
                    ".webm",
                    ".mkv",
                    ".avi",
                    ".mov",
                    ".flv",
                    ".3gp",
                    ".m4v",
                ]:
                    potential_path = os.path.join(directory, base_name + ext)
                    if os.path.exists(potential_path):
                        result_path = potential_path
                        break
                else:
                    # If no extension found, add the most common one
                    result_path = result_path + ".mp4"

            # Get file size
            file_size = os.path.getsize(result_path)

            # Update status to completed
            completed_at = datetime.now(timezone.utc)
            await _update_download_status(
                download_id,
                "completed",
                progress=100.0,
                completed_at=completed_at,
                file_size=file_size,
                output_path=result_path,
                title=video_title,
                duration=duration,
                thumbnail_url=thumbnail_url,
                extractor=extractor,
                description=description,
            )

            # Create history record
            await _create_download_history(
                download_id=download_id,
                url=url,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
                file_size=file_size,
            )

            # Trigger download completed webhook
            await _trigger_webhooks(
                "download_completed",
                download_id,
                {"url": url, "file_path": result_path, "file_size": file_size},
            )

            return {
                "success": True,
                "download_id": download_id,
                "file_path": result_path,
                "file_size": file_size,
            }
        else:
            # Download failed
            error_message = "Download completed but file not found"
            completed_at = datetime.now(timezone.utc)

            await _update_download_status(
                download_id,
                "failed",
                completed_at=completed_at,
                error_message=error_message,
            )

            await _create_download_history(
                download_id=download_id,
                url=url,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                error_message=error_message,
            )

            await _trigger_webhooks(
                "download_failed", download_id, {"url": url, "error": error_message}
            )

            return {
                "success": False,
                "download_id": download_id,
                "error": error_message,
            }

    except Exception as e:
        error_message = str(e)
        completed_at = datetime.now(timezone.utc)

        logger.error(
            "Download task failed", download_id=download_id, error=error_message
        )

        await _update_download_status(
            download_id,
            "failed",
            completed_at=completed_at,
            error_message=error_message,
        )

        await _create_download_history(
            download_id=download_id,
            url=url,
            status="failed",
            started_at=started_at,
            completed_at=completed_at,
            error_message=error_message,
        )

        await _trigger_webhooks(
            "download_failed", download_id, {"url": url, "error": error_message}
        )

        return {"success": False, "download_id": download_id, "error": error_message}


def download_video_task(
    download_id: str,
    url: str,
    format_spec: str = "best",
    output_path: str = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Celery task for downloading a video.

    This is a synchronous wrapper that runs the async download logic.
    """
    return asyncio.run(
        _download_video_task(
            download_id=download_id,
            url=url,
            format_spec=format_spec,
            output_path=output_path,
            **kwargs,
        )
    )


async def _batch_download_task(
    download_ids: list[str],
    urls: list[str],
    format_spec: str = "best",
    output_directory: str = None,
    **kwargs,
) -> Dict[str, Any]:
    """Core batch download logic."""
    started_at = datetime.now(timezone.utc)  # TODO: Use for batch timing
    results = []

    batch_id = f"batch_{len(download_ids)}_urls"  # TODO: Create actual batch record
    logger.debug(f"Batch started at: {started_at}")  # Use for timing reference

    try:
        # Trigger batch started webhook
        await _trigger_webhooks(
            "batch_download_started",
            batch_id,
            {"urls": urls, "total_videos": len(urls)},
        )

        # Process each URL with its corresponding download ID
        for download_id, url in zip(download_ids, urls):
            result = await _download_video_task(
                download_id=download_id,
                url=url,
                format_spec=format_spec,
                output_path=output_directory,
                **kwargs,
            )

            results.append(result)

        completed_at = datetime.now(timezone.utc)  # TODO: Use for batch timing
        successful_downloads = sum(1 for r in results if r["success"])
        logger.debug(f"Batch completed at: {completed_at}")  # Use for timing reference

        await _trigger_webhooks(
            "batch_download_completed",
            batch_id,
            {
                "total_videos": len(urls),
                "successful_downloads": successful_downloads,
                "failed_downloads": len(urls) - successful_downloads,
                "results": results,
            },
        )

        return {
            "batch_id": batch_id,
            "total_downloads": len(urls),
            "successful_downloads": successful_downloads,
            "results": results,
        }

    except Exception as e:
        error_message = str(e)

        logger.error(
            "Batch download task failed", batch_id=batch_id, error=error_message
        )

        await _trigger_webhooks(
            "batch_download_failed", batch_id, {"error": error_message}
        )

        return {"batch_id": batch_id, "error": error_message, "results": results}


def batch_download_task(
    download_ids: list[str],
    urls: list[str],
    format_spec: str = "best",
    output_directory: str = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Celery task for batch downloading videos.

    This is a synchronous wrapper that runs the async batch download logic.

    Args:
        download_ids: List of pre-created download IDs from the database
        urls: List of URLs to download
        format_spec: Format specification for all downloads
        output_directory: Optional output directory path
    """
    return asyncio.run(
        _batch_download_task(
            download_ids=download_ids,
            urls=urls,
            format_spec=format_spec,
            output_directory=output_directory,
            **kwargs,
        )
    )
