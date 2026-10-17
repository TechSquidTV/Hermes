"""
Celery tasks for video downloading operations.
"""

import asyncio
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, TypedDict

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import async_session_maker
from app.db.repositories import (
    DownloadHistoryRepository,
    DownloadRepository,
    WebhookRepository,
)
from app.services.download_files import register_download_file
from app.services.redis_progress import redis_progress_service
from app.services.yt_dlp_service import YTDLPService
from app.tasks.runtime import run_async_task
from app.tasks.types import task
from app.utils.download_progress import (
    build_download_progress_payload,
)
from app.utils.files import resolve_download_path
from app.utils.media import DEFAULT_FORMAT_SPEC

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
    progress: float | None = None,
    downloaded_bytes: int | None = None,
    total_bytes: int | None = None,
    download_speed: float | None = None,
    eta: float | None = None,
    result: dict[str, Any] | None = None,
) -> None:
    """
    Publish real-time progress updates via SSE (Redis Pub/Sub only).

    This is lightweight and can be called frequently (e.g., every 1% or 0.5s)
    without hitting the database.

    Structures data to match DownloadStatus schema with nested progress object.
    """
    # Structure to match DownloadStatus schema
    # Note: download_id is added by publish_download_progress
    sse_data = build_download_progress_payload(
        status=status,
        message=(
            f"Downloading: {progress:.1f}%"
            if progress is not None
            else "Downloading..."
        ),
        progress=progress,
        downloaded_bytes=downloaded_bytes,
        total_bytes=total_bytes,
        download_speed=download_speed,
        eta=eta,
        result=result,
        include_progress=True,
    )

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


class ProgressFields(TypedDict):
    progress: float | None
    downloaded_bytes: int | None
    total_bytes: int | None
    download_speed: float | None
    eta: float | None


async def _get_progress_payload_fields(
    download_id: str,
    status: str,
    progress: float | None = None,
    downloaded_bytes: int | None = None,
    total_bytes: int | None = None,
    download_speed: float | None = None,
    eta: float | None = None,
) -> ProgressFields | None:
    """Resolve progress fields for active SSE payloads."""
    if progress is not None or downloaded_bytes is not None:
        return {
            "progress": progress,
            "downloaded_bytes": downloaded_bytes,
            "total_bytes": total_bytes,
            "download_speed": download_speed,
            "eta": eta,
        }

    if status not in ("downloading", "processing"):
        return None

    async with async_session_maker() as session:
        download_repo = DownloadRepository(session)
        download = await download_repo.get_by_id(download_id)

        if not download or download.progress is None:
            return None

        return {
            "progress": download.progress,
            "downloaded_bytes": download.downloaded_bytes,
            "total_bytes": download.total_bytes,
            "download_speed": download.download_speed,
            "eta": download.eta,
        }


async def _update_download_status(
    download_id: str,
    status: str,
    progress: float | None = None,
    error_message: str | None = None,
    downloaded_bytes: int | None = None,
    total_bytes: int | None = None,
    download_speed: float | None = None,
    eta: float | None = None,
    publish_sse: bool = True,
    result: dict[str, Any] | None = None,
    message: str | None = None,
    **kwargs: object,
) -> bool:
    """
    Update download status in database and optionally publish to SSE.

    Args:
        publish_sse: If True, also publish to SSE. Set to False when calling
                     from progress hook (SSE is handled separately for frequency control).
    """
    async with async_session_maker() as session:
        if status == "completed":
            # The status repository commits both writes below; registration must
            # never become visible independently of the completed status.
            completed_path = kwargs.get("output_path")
            if not isinstance(completed_path, str):
                raise ValueError("Completed download must have an output path")
            file_record = await register_download_file(
                session, download_id, completed_path
            )
            kwargs["output_path"] = file_record.filepath
            kwargs["file_size"] = file_record.file_size

        updated = await DownloadRepository(session).update_status(
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

        if not updated or updated.status != status:
            return False

    # Optionally publish SSE (disabled during progress updates for frequency control)
    if publish_sse:
        payload_extra = dict(kwargs)
        progress_fields = await _get_progress_payload_fields(
            download_id=download_id,
            status=status,
            progress=progress,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            download_speed=download_speed,
            eta=eta,
        )

        progress_data = build_download_progress_payload(
            status=status,
            error_message=error_message,
            result=result,
            include_progress=progress_fields is not None,
            message=message,
            progress=progress_fields["progress"] if progress_fields else None,
            downloaded_bytes=(
                progress_fields["downloaded_bytes"] if progress_fields else None
            ),
            total_bytes=progress_fields["total_bytes"] if progress_fields else None,
            download_speed=(
                progress_fields["download_speed"] if progress_fields else None
            ),
            eta=progress_fields["eta"] if progress_fields else None,
            **payload_extra,
        )

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

    return True


async def _create_download_history(
    download_id: str,
    url: str,
    status: str,
    started_at: datetime,
    completed_at: datetime,
    **kwargs: object,
) -> None:
    """Helper function to create download history record."""
    async with async_session_maker() as session:
        await DownloadHistoryRepository(session).create(
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
            repository = WebhookRepository(session)
            webhooks = await repository.get_webhooks_for_event(event)

            for webhook in webhooks:
                # TODO: Implement webhook triggering with retry logic
                logger.info(
                    f"Webhook triggered for {event}",
                    webhook_id=webhook.id,
                    download_id=download_id,
                )
                await repository.update_last_triggered(webhook.id)

    except Exception as e:
        logger.error("Failed to trigger webhooks", event_type=event, error=str(e))


async def _download_video_task(
    download_id: str,
    url: str,
    format_spec: str = DEFAULT_FORMAT_SPEC,
    output_path: str | None = None,
    output_template: str | None = None,
    **kwargs: object,
) -> Dict[str, Any]:
    """Core download logic."""
    started_at = datetime.now(timezone.utc)

    try:
        output_directory = resolve_download_path(output_path or settings.download_dir)
        # A cancelled/finished task may still be delivered after broker retries.
        if not await _update_download_status(
            download_id, "downloading", started_at=started_at
        ):
            return {
                "success": False,
                "download_id": download_id,
                "error": "Download is no longer active",
            }

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

        output_filename = (
            os.path.basename(output_template)
            if output_template
            else f"{sanitized_title}.%(ext)s"
        )

        if not output_filename:
            output_filename = f"{sanitized_title}.%(ext)s"

        # Prefix custom templates too, so all retries/duplicates are isolated.
        output_filename = f"{download_id}_{output_filename}"
        output_path = str(
            resolve_download_path(str(output_directory / output_filename))
        )

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
                        **build_download_progress_payload(
                            status="downloading",
                            message=f"Downloading: {percentage:.1f}%",
                            progress=percentage,
                            downloaded_bytes=downloaded_int,
                            total_bytes=total_int,
                            download_speed=speed_float,
                            eta=eta_float,
                            result=result_data,
                            include_progress=True,
                        ),
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

        if not result_path or not os.path.isfile(result_path):
            raise FileNotFoundError("Downloaded file is missing")

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
        completed = await _update_download_status(
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

        if not completed:
            # A cancellation won the atomic status transition. Do not announce
            # completion or leave an unregistered final file behind.
            resolve_download_path(result_path).unlink(missing_ok=True)
            return {
                "success": False,
                "download_id": download_id,
                "error": "Download is no longer active",
            }

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

        # Emit stats update event via SSE
        try:
            await redis_progress_service.publish_stats_update(
                {
                    "event": "download_completed",
                    "download_id": download_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            # Don't fail the download if stats event publish fails
            logger.error(
                "Failed to publish stats update event",
                download_id=download_id,
                error=str(e),
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

    except Exception as e:
        error_message = "Download failed; see server logs for details"
        completed_at = datetime.now(timezone.utc)

        logger.error("Download task failed", download_id=download_id, error=str(e))

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


@task(name="app.tasks.download_tasks.download_video_task")
def download_video_task(
    download_id: str,
    url: str,
    format_spec: str = DEFAULT_FORMAT_SPEC,
    output_path: str | None = None,
    output_template: str | None = None,
    **kwargs: object,
) -> Dict[str, Any]:
    """
    Celery task for downloading a video.

    This is a synchronous wrapper that runs the async download logic.
    """
    return run_async_task(
        _download_video_task(
            download_id=download_id,
            url=url,
            format_spec=format_spec,
            output_path=output_path,
            output_template=output_template,
            **kwargs,
        )
    )
