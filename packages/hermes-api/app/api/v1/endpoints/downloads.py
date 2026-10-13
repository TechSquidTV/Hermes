"""
Download management endpoints.
"""

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_repositories_from_session
from app.core.logging import get_logger
from app.core.security import ApiKeyPermission, AuthPrincipal, require_api_permission
from app.db.session import get_database_session
from app.models.pydantic.download import (
    BatchDownloadRequest,
    BatchDownloadResponse,
    CancelResponse,
    DownloadProgress,
    DownloadRequest,
    DownloadResponse,
    DownloadResult,
    DownloadStatus,
)
from app.services.redis_progress import redis_progress_service
from app.tasks.celery_app import celery_app
from app.tasks.download_tasks import download_video_task
from app.utils.download_progress import progress_fields_from_payload
from app.utils.urls import validate_public_url

router = APIRouter()
logger = get_logger(__name__)


def _download_options_from_request(
    download_request: DownloadRequest,
) -> dict[str, object]:
    """Map public download options onto task/yt-dlp keyword arguments."""
    options: dict[str, object] = {}

    if download_request.output_template:
        options["output_template"] = download_request.output_template
    if download_request.download_subtitles:
        options["writesubtitles"] = True
    if download_request.download_thumbnail:
        options["writethumbnail"] = True
    if download_request.subtitle_languages:
        options["subtitleslangs"] = download_request.subtitle_languages
    if download_request.cookies:
        options["http_headers"] = {
            "Cookie": "; ".join(
                f"{name}={value}" for name, value in download_request.cookies.items()
            )
        }

    return options


def _batch_download_options_from_request(
    batch_request: BatchDownloadRequest,
) -> dict[str, object]:
    """Map public batch download options onto task/yt-dlp keyword arguments."""
    options: dict[str, object] = {}

    if batch_request.download_subtitles:
        options["writesubtitles"] = True
    if batch_request.download_thumbnail:
        options["writethumbnail"] = True

    return options


@router.post("/")
async def start_download(
    download_request: DownloadRequest,  # Renamed from 'request' to avoid conflicts
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.WRITE)),
) -> DownloadResponse:
    """
    Start a new video download.

    This endpoint initiates a video download with the specified format and options.
    The download is processed asynchronously in the background.

    **Format Selection:**
    The `format` parameter accepts various format specifications:

    **Authentication:**
    This endpoint accepts both JWT tokens (from user login) and API keys.
    For API keys, both configured keys and database-stored keys are supported.
    - Quality selectors: `best`, `worst`, `bestvideo+bestaudio`
    - Resolution limits: `bestvideo[height<=720]+bestaudio`
    - Container preferences: `mp4`, `webm`, `mkv`
    - Audio-only: `bestaudio`, `bestaudio[ext=m4a]`
    - Specific format IDs: `137+140` (obtained from GET /info endpoint)

    For a complete list of format options and detailed descriptions, see:
    **GET /api/v1/formats/** endpoint

    **Workflow:**
    1. Call GET /info with the URL to preview available formats
    2. Call GET /formats to understand format selection syntax
    3. Call POST /download with your chosen format specification
    4. Poll GET /download/{id} to track download progress

    **Examples:**
    ```json
    // Best quality (default)
    {"url": "https://youtube.com/watch?v=...", "format": "bestvideo*+bestaudio/best"}

    // Best video + audio up to 1080p
    {"url": "https://youtube.com/watch?v=...",
     "format": "bestvideo[height<=1080]+bestaudio"}

    // Audio only in MP3
    {"url": "https://youtube.com/watch?v=...", "format": "bestaudio[ext=mp3]"}

    // MP4 container preferred
    {"url": "https://youtube.com/watch?v=...", "format": "mp4"}
    ```

    Returns:
        DownloadResponse: Download ID and initial status
    """
    await _validate_urls([download_request.url])
    logger.info(
        "Starting download",
        format=download_request.format,
    )

    # Create download record in database
    repos = get_repositories_from_session(db_session)
    download = await repos["downloads"].create(
        url=download_request.url,
        format_spec=download_request.format,  # Store as format_spec in DB
        status="pending",
    )

    _queue_download(
        download.id,
        download_request.url,
        download_request.format,
        download_request.output_directory,
        _download_options_from_request(download_request),
    )

    logger.info("Download queued successfully", download_id=download.id)

    return DownloadResponse(
        download_id=download.id,
        status=download.status,
        message="Download queued successfully",
    )


@router.get("/{download_id}")
async def get_download_status(
    download_id: str,
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.READ)),
) -> DownloadStatus:
    """Get the status of a download."""
    repos = get_repositories_from_session(db_session)
    download = await repos["downloads"].get_by_id(download_id)

    if not download:
        raise HTTPException(status_code=404, detail="Download not found")

    # Build progress information
    # Try Redis first for active downloads (fast, real-time)
    progress_info = None
    if download.status == "downloading":
        redis_progress = await redis_progress_service.get_progress(download_id)
        if redis_progress:
            # Use Redis data for active downloads
            progress_info = DownloadProgress(
                **progress_fields_from_payload(
                    redis_progress, fallback_status="downloading"
                )
            )

    # Fall back to database if not in Redis or not downloading
    if progress_info is None and download.progress is not None:
        progress_info = DownloadProgress(
            percentage=download.progress,
            status=download.status,
            downloaded_bytes=download.downloaded_bytes,
            total_bytes=download.total_bytes,
            speed=download.download_speed,
            eta=download.eta,
        )

    # Build result information
    result_info = None
    if download.status == "completed":
        result_info = DownloadResult(
            url=download.url,
            title=download.title,
            file_size=download.file_size,
            duration=download.duration,
            thumbnail_url=download.thumbnail_url,
            extractor=download.extractor,
            description=download.description,
        )
    else:
        # Include partial information for non-completed statuses
        result_info = DownloadResult(
            url=download.url,
            title=download.title,
            thumbnail_url=download.thumbnail_url,
            extractor=download.extractor,
        )

    # Build response
    response = DownloadStatus(
        download_id=download.id,
        status=download.status,
        progress=progress_info,
        current_filename=(
            Path(download.output_path).name if download.output_path else None
        ),
        message=f"Download {download.status}",
        error=download.error_message,
        result=result_info,
        created_at=download.created_at,
    )

    return response


@router.post("/{download_id}/cancel")
async def cancel_download(
    download_id: str,
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.WRITE)),
) -> CancelResponse:
    """Cancel a running download."""
    repos = get_repositories_from_session(db_session)
    download = await repos["downloads"].get_by_id(download_id)

    if not download:
        raise HTTPException(status_code=404, detail="Download not found")

    if download.status in ["completed", "failed", "cancelled"]:
        return CancelResponse(
            download_id=download_id,
            cancelled=False,
            message=f"Cannot cancel {download.status} download",
        )

    # Update status to cancelled
    updated = await repos["downloads"].update_status(
        download_id, "cancelled", error_message="Cancelled by user"
    )
    if updated is None or updated.status != "cancelled":
        return CancelResponse(
            download_id=download_id,
            cancelled=False,
            message="Download already finished",
        )
    # Each download owns exactly one Celery task, including batch members.
    celery_app.control.revoke(download_id, terminate=True, signal="SIGTERM")
    await redis_progress_service.delete_progress(download_id)
    await redis_progress_service.revoke_user_sse_tokens(
        user_id="*", scope_prefix=f"download:{download_id}"
    )

    logger.info("Download cancelled", download_id=download_id)

    return CancelResponse(
        download_id=download_id,
        cancelled=True,
        message="Download cancelled successfully",
    )


@router.post("/batch")
async def start_batch_download(
    batch_request: BatchDownloadRequest,  # Renamed from 'request' to avoid conflicts
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.WRITE)),
) -> BatchDownloadResponse:
    """
    Start a batch download of multiple videos.

    Downloads multiple videos with the same format specification applied to all.
    All downloads are processed asynchronously in the background.

    **Format Selection:**
    The `format` parameter applies to all videos in the batch.
    See GET /api/v1/formats/ for available format options.

    Common batch scenarios:
    - `"bestvideo*+bestaudio/best"`: Best quality for all videos, merging when needed
    - `"bestaudio[ext=mp3]"`: Audio-only in MP3 format
    - `"bestvideo[height<=720]+bestaudio"`: All videos limited to 720p

    Returns:
        BatchDownloadResponse: Batch ID and list of individual download IDs
    """
    await _validate_urls(batch_request.urls)
    logger.info(
        "Starting batch download",
        urls_count=len(batch_request.urls),
        format=batch_request.format,
    )

    # Get repositories
    repos = get_repositories_from_session(db_session)

    # Create download records in database for each URL
    download_ids = []
    for url in batch_request.urls:
        download = await repos["downloads"].create(
            url=url, format_spec=batch_request.format, status="pending"
        )
        download_ids.append(download.id)

    logger.info("Created download records", download_count=len(download_ids))

    # Independent tasks keep cancellation of one member isolated.
    options = _batch_download_options_from_request(batch_request)
    for download_id, url in zip(download_ids, batch_request.urls, strict=True):
        _queue_download(
            download_id,
            url,
            batch_request.format,
            batch_request.output_directory,
            options,
        )

    logger.info("Batch download queued successfully", download_count=len(download_ids))

    return BatchDownloadResponse(
        batch_id=str(uuid.uuid4()),
        total_downloads=len(download_ids),
        status="queued",
        downloads=download_ids,
    )


def _queue_download(
    download_id: str,
    url: str,
    format_spec: str,
    output_directory: str | None,
    options: dict[str, object],
) -> None:
    """Keep task identity and routing identical for single and batch downloads."""
    download_video_task.apply_async(
        task_id=download_id,
        kwargs={
            "download_id": download_id,
            "url": url,
            "format_spec": format_spec,
            "output_path": output_directory,
            **options,
        },
        queue="hermes.downloads",
    )


async def _validate_urls(urls: list[str]) -> None:
    try:
        await asyncio.gather(
            *(asyncio.to_thread(validate_public_url, url) for url in urls)
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
