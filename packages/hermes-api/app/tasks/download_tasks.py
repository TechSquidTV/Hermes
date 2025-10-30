"""
Celery tasks for video downloading operations.
"""

import asyncio
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.logging import get_logger
from app.db.base import async_session_maker
from app.db.repositories import (
    DownloadHistoryRepository,
    DownloadRepository,
    WebhookRepository,
)
from app.services.redis_progress import redis_progress_service
from app.services.yt_dlp_service import YTDLPService
from app.tasks.celery_app import celery_app

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


async def _publish_sse_progress(
    download_id: str,
    status: str,
    progress: float = None,
    downloaded_bytes: int = None,
    total_bytes: int = None,
    download_speed: float = None,
    eta: float = None,
    result: dict = None,
) -> None:
    """
    Publish real-time progress updates via SSE (Redis Pub/Sub only).

    This is lightweight and can be called frequently (e.g., every 1% or 0.5s)
    without hitting the database.

    Structures data to match DownloadStatus schema with nested progress object.
    """
    # Structure to match DownloadStatus schema
    # Note: download_id is added by publish_download_progress
    sse_data = {
        "status": status,
        "message": f"Downloading: {progress:.1f}%" if progress else "Downloading...",
        "progress": {
            "percentage": progress,
            "status": status,
            "downloaded_bytes": downloaded_bytes,
            "total_bytes": total_bytes,
            "speed": download_speed,
            "eta": eta,
        },
    }

    # Include result object if provided (for video metadata)
    if result:
        sse_data["result"] = result

    # Debug logging
    logger.info(
        "Publishing lightweight SSE progress (from hook)",
        download_id=download_id,
        progress_percentage=progress,
        status=status,
    )

    await redis_progress_service.publish_download_progress(
        download_id=download_id,
        progress_data=sse_data,
    )


async def _update_download_status(
    download_id: str,
    status: str,
    progress: float = None,
    error_message: str = None,
    downloaded_bytes: int = None,
    total_bytes: int = None,
    download_speed: float = None,
    eta: float = None,
    publish_sse: bool = True,
    **kwargs,
) -> None:
    """
    Update download status in database and optionally publish to SSE.

    Args:
        publish_sse: If True, also publish to SSE. Set to False when calling
                     from progress hook (SSE is handled separately for frequency control).
    """
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
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            download_speed=download_speed,
            eta=eta,
            **kwargs,
        )

    # Optionally publish SSE (disabled during progress updates for frequency control)
    if publish_sse:
        # Structure to match DownloadStatus schema with nested progress object
        progress_data = {
            "status": status,
            "error_message": error_message,
            **kwargs,
        }

        # Add nested progress object (matching _publish_sse_progress structure)
        # Always include progress for active downloads to prevent frontend state loss
        if progress is not None or downloaded_bytes is not None:
            progress_data["progress"] = {
                "percentage": progress,
                "status": status,
                "downloaded_bytes": downloaded_bytes,
                "total_bytes": total_bytes,
                "speed": download_speed,
                "eta": eta,
            }
        elif status in ("downloading", "processing"):
            # For active downloads without new progress data, fetch current progress from DB
            # to prevent SSE events from wiping out frontend progress state
            async with async_session_maker() as session:
                download_repo = DownloadRepository(session)
                download = await download_repo.get_by_id(download_id)
                if download and download.progress is not None:
                    progress_data["progress"] = {
                        "percentage": download.progress,
                        "status": status,
                        "downloaded_bytes": download.downloaded_bytes,
                        "total_bytes": download.total_bytes,
                        "speed": download.download_speed,
                        "eta": download.eta,
                    }

        # Debug logging to trace SSE events
        logger.info(
            "Publishing SSE progress update",
            download_id=download_id,
            status=status,
            has_progress_object="progress" in progress_data,
            progress_percentage=(
                progress_data.get("progress", {}).get("percentage")
                if "progress" in progress_data
                else None
            ),
        )

        await redis_progress_service.publish_download_progress(
            download_id=download_id,
            progress_data=progress_data,
        )

        # Publish queue update
        await redis_progress_service.publish_queue_update(
            action="status_changed", download_id=download_id, data={"status": status}
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
        # Structure metadata as DownloadResult for consistent SSE format
        result_data = {
            "url": url,
            "title": video_title,
            "thumbnail_url": thumbnail_url,
            "extractor": extractor,
            "description": description,
            "duration": duration,
        }
        await _update_download_status(
            download_id,
            "downloading",
            title=video_title,
            thumbnail_url=thumbnail_url,
            extractor=extractor,
            description=description,
            duration=duration,
            result=result_data,  # Include result for SSE
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

        # Create progress callback to update Redis and database (throttled)
        # Capture the running event loop to schedule async work from sync callback.
        # Note: get_running_loop() is correct here - we're inside an async function
        # and need to capture THIS loop for use in the sync progress_hook callback.
        # The callback will use run_coroutine_threadsafe() to schedule back to this loop.
        loop = asyncio.get_running_loop()

        # Throttling variables for database writes and SSE updates
        last_db_update_time = [0.0]  # Use list for mutable closure variable
        last_db_percentage = [0.0]
        last_sse_update_time = [0.0]
        last_sse_percentage = [0.0]

        def progress_hook(d: Dict[str, Any]) -> None:
            """Progress callback for yt-dlp downloads."""
            try:
                if d.get("status") == "downloading":
                    # Extract progress information
                    downloaded = d.get("downloaded_bytes", 0)
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    speed = d.get("speed")
                    eta_seconds = d.get("eta")

                    # Convert to appropriate types (yt-dlp sometimes returns floats)
                    downloaded_int = int(downloaded) if downloaded is not None else None
                    total_int = int(total) if total is not None else None
                    speed_float = float(speed) if speed is not None else None
                    eta_float = float(eta_seconds) if eta_seconds is not None else None

                    # Calculate percentage
                    percentage = 0.0
                    if total_int and total_int > 0 and downloaded_int is not None:
                        raw_percentage = (downloaded_int / total_int) * 100

                        # Sanity check: yt-dlp's first callbacks often have wildly incorrect
                        # total_bytes estimates (too small), causing false 100% readings.
                        # If we get >= 100% but haven't downloaded much data, it's bogus.
                        MIN_BYTES_FOR_COMPLETION = 1_000_000  # 1MB minimum
                        if (
                            raw_percentage >= 100.0
                            and downloaded_int < MIN_BYTES_FOR_COMPLETION
                        ):
                            # Clearly wrong - cap at 5% to show some progress
                            percentage = 5.0
                        elif raw_percentage > 100.0:
                            # Over 100% means bad estimate, cap at 99
                            percentage = 99.0
                        else:
                            percentage = raw_percentage

                    # Prepare progress data matching DownloadStatus schema
                    progress_data = {
                        "download_id": download_id,
                        "status": "downloading",
                        "message": f"Downloading: {percentage:.1f}%",
                        "progress": {
                            "percentage": percentage,
                            "status": "downloading",
                            "downloaded_bytes": downloaded_int,
                            "total_bytes": total_int,
                            "speed": speed_float,
                            "eta": eta_float,
                        },
                        "result": result_data,  # Include video metadata
                    }

                    # ============================================================
                    # THREE-LAYER PROGRESS UPDATE ARCHITECTURE
                    # ============================================================
                    # 1. Redis Cache: ALWAYS (fastest, for GET /download/{id})
                    # 2. SSE Updates: FREQUENT - 1% or 0.5s (real-time UI, no DB)
                    # 3. DB Updates: THROTTLED - 5% or 2s (persistent storage)
                    # ============================================================

                    # Layer 1: Redis cache (always write - fast, ephemeral)
                    redis_progress_service.set_progress_sync(download_id, progress_data)

                    current_time = time.time()

                    # Layer 2: SSE updates (frequent - Redis Pub/Sub only, no database)
                    # Purpose: Smooth real-time progress bars in the UI
                    percentage_diff_sse = abs(percentage - last_sse_percentage[0])
                    time_diff_sse = current_time - last_sse_update_time[0]

                    should_send_sse = (
                        percentage_diff_sse >= 1.0  # 1% change
                        or time_diff_sse >= 0.5  # 0.5 seconds passed
                        or percentage >= 99.9  # Near completion
                    )

                    if should_send_sse:
                        asyncio.run_coroutine_threadsafe(
                            _publish_sse_progress(
                                download_id=download_id,
                                status="downloading",
                                progress=percentage,
                                downloaded_bytes=downloaded_int,
                                total_bytes=total_int,
                                download_speed=speed_float,
                                eta=eta_float,
                                result=result_data,  # Include video metadata in SSE
                            ),
                            loop,
                        )
                        last_sse_update_time[0] = current_time
                        last_sse_percentage[0] = percentage

                    # Layer 3: Database writes (throttled - persistent storage only)
                    # Purpose: Persistent records without overloading the database
                    percentage_diff_db = abs(percentage - last_db_percentage[0])
                    time_diff_db = current_time - last_db_update_time[0]

                    should_update_db = (
                        percentage_diff_db >= 5.0  # 5% change
                        or time_diff_db >= 2.0  # 2 seconds passed
                        or percentage >= 99.9  # Near completion
                    )

                    if should_update_db:
                        asyncio.run_coroutine_threadsafe(
                            _update_download_status(
                                download_id=download_id,
                                status="downloading",
                                progress=percentage,
                                downloaded_bytes=downloaded_int,
                                total_bytes=total_int,
                                download_speed=speed_float,
                                eta=eta_float,
                                publish_sse=False,  # SSE already sent above
                            ),
                            loop,
                        )
                        last_db_update_time[0] = current_time
                        last_db_percentage[0] = percentage
            except Exception as e:
                logger.error(
                    "Progress hook error", download_id=download_id, error=str(e)
                )

        # Download the video with progress callback
        result_path = await yt_service.download_video(
            url=url,
            output_path=output_path,
            format_spec=format_spec,
            progress_callback=progress_hook,
            **kwargs,
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
            # Structure complete metadata as DownloadResult for SSE
            complete_result = {
                "url": url,
                "title": video_title,
                "file_size": file_size,
                "duration": duration,
                "thumbnail_url": thumbnail_url,
                "extractor": extractor,
                "description": description,
            }
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
                result=complete_result,  # Include result for SSE
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

            # Clean up Redis progress data (download complete)
            await redis_progress_service.delete_progress(download_id)

            # Revoke SSE tokens for this download (security cleanup)
            try:
                revoked = await redis_progress_service.revoke_user_sse_tokens(
                    user_id="*",  # Revoke for all users since we don't track user per download yet
                    scope_prefix=f"download:{download_id}",
                )
                if revoked > 0:
                    logger.info(
                        "Revoked SSE tokens for completed download",
                        download_id=download_id,
                        tokens_revoked=revoked,
                    )
            except Exception as e:
                # Don't fail the download if token revocation fails
                logger.error(
                    "Failed to revoke SSE tokens for completed download",
                    download_id=download_id,
                    error=str(e),
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

            # Clean up Redis progress data (download failed)
            await redis_progress_service.delete_progress(download_id)

            # Revoke SSE tokens for this download (security cleanup)
            try:
                revoked = await redis_progress_service.revoke_user_sse_tokens(
                    user_id="*",
                    scope_prefix=f"download:{download_id}",
                )
                if revoked > 0:
                    logger.info(
                        "Revoked SSE tokens for failed download",
                        download_id=download_id,
                        tokens_revoked=revoked,
                    )
            except Exception as e:
                logger.error(
                    "Failed to revoke SSE tokens for failed download",
                    download_id=download_id,
                    error=str(e),
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

        # Clean up Redis progress data (download exception)
        await redis_progress_service.delete_progress(download_id)

        # Revoke SSE tokens for this download (security cleanup)
        try:
            revoked = await redis_progress_service.revoke_user_sse_tokens(
                user_id="*",
                scope_prefix=f"download:{download_id}",
            )
            if revoked > 0:
                logger.info(
                    "Revoked SSE tokens for failed download (exception)",
                    download_id=download_id,
                    tokens_revoked=revoked,
                )
        except Exception as revoke_error:
            logger.error(
                "Failed to revoke SSE tokens for failed download (exception)",
                download_id=download_id,
                error=str(revoke_error),
            )

        return {"success": False, "download_id": download_id, "error": error_message}


@celery_app.task(name="app.tasks.download_tasks.download_video_task")
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


@celery_app.task(name="app.tasks.download_tasks.batch_download_task")
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
