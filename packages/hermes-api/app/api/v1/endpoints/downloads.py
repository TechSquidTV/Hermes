"""
Download management endpoints.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_api_key, validate_database_api_key
from app.db.repositories import DownloadRepository
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
from app.tasks.download_tasks import batch_download_task, download_video_task

router = APIRouter()
logger = get_logger(__name__)


def get_repositories_from_session(db_session: AsyncSession):
    """Create repository instances using the provided database session."""
    return {
        "downloads": DownloadRepository(db_session),
    }


@router.post("/")
async def start_download(
    download_request: DownloadRequest,  # Renamed from 'request' to avoid conflicts
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
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
    {"url": "https://youtube.com/watch?v=...", "format": "best"}

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
    try:
        # Validate database API keys
        if api_key.startswith("db_api_key:"):
            validated_key = await validate_database_api_key(
                api_key.replace("db_api_key:", ""), db_session
            )
            if not validated_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or inactive API key",
                )
            api_key = validated_key

        logger.info(
            "Starting download",
            url=download_request.url[:50] + "...",
            format=download_request.format,
        )

        # Create download record in database
        repos = get_repositories_from_session(db_session)
        download = await repos["downloads"].create(
            url=download_request.url,
            format_spec=download_request.format,  # Store as format_spec in DB
            status="pending",
        )

        # Queue the download task in Celery
        download_video_task.apply_async(
            kwargs={
                "download_id": download.id,
                "url": download_request.url,
                "format_spec": download_request.format,
                "output_path": download_request.output_directory,
            },
            queue="hermes.downloads",
        )

        logger.info("Download queued successfully", download_id=download.id)

        return DownloadResponse(
            download_id=download.id,
            status=download.status,
            message="Download queued successfully",
        )

    except Exception as e:
        logger.error("Failed to start download", url=download_request.url, error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to start download: {str(e)}"
        )


@router.get("/{download_id}")
async def get_download_status(
    download_id: str,
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
) -> DownloadStatus:
    """Get the status of a download."""
    try:
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
                    percentage=redis_progress.get("percentage", 0.0),
                    status=redis_progress.get("status", "downloading"),
                    downloaded_bytes=redis_progress.get("downloaded_bytes"),
                    total_bytes=redis_progress.get("total_bytes"),
                    speed=redis_progress.get("speed"),
                    eta=redis_progress.get("eta"),
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
            current_filename=download.output_path,
            message=f"Download {download.status}",
            error=download.error_message,
            result=result_info,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get download status", download_id=download_id, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get download status: {str(e)}"
        )


@router.post("/{download_id}/cancel")
async def cancel_download(
    download_id: str,
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
) -> CancelResponse:
    """Cancel a running download."""
    try:
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
        await repos["downloads"].update_status(
            download_id, "cancelled", error_message="Cancelled by user"
        )

        logger.info("Download cancelled", download_id=download_id)

        return CancelResponse(
            download_id=download_id,
            cancelled=True,
            message="Download cancelled successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel download", download_id=download_id, error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel download: {str(e)}"
        )


@router.post("/batch")
async def start_batch_download(
    batch_request: BatchDownloadRequest,  # Renamed from 'request' to avoid conflicts
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
) -> BatchDownloadResponse:
    """
    Start a batch download of multiple videos.

    Downloads multiple videos with the same format specification applied to all.
    All downloads are processed asynchronously in the background.

    **Format Selection:**
    The `format` parameter applies to all videos in the batch.
    See GET /api/v1/formats/ for available format options.

    Common batch scenarios:
    - `"best"`: Best quality for all videos
    - `"bestaudio[ext=mp3]"`: Audio-only in MP3 format
    - `"bestvideo[height<=720]+bestaudio"`: All videos limited to 720p

    Returns:
        BatchDownloadResponse: Batch ID and list of individual download IDs
    """
    try:
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

        # Queue the batch download task with real download IDs
        background_tasks.add_task(
            batch_download_task,
            download_ids,
            batch_request.urls,
            batch_request.format,
            batch_request.output_directory,
        )

        logger.info(
            "Batch download queued successfully", download_count=len(download_ids)
        )

        return BatchDownloadResponse(
            batch_id=f"batch_{len(download_ids)}_urls",
            total_downloads=len(download_ids),
            status="queued",
            downloads=download_ids,
        )

    except Exception as e:
        logger.error("Failed to start batch download", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to start batch download: {str(e)}"
        )
