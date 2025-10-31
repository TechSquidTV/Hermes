"""
Queue management endpoints.
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_api_key
from app.db.repositories import DownloadRepository
from app.db.session import get_database_session
from app.models.pydantic.download import CleanupOrphanedResponse, DownloadQueue

router = APIRouter()
logger = get_logger(__name__)


def get_repositories_from_session(db_session: AsyncSession):
    """Create repository instances using the provided database session."""
    return {
        "downloads": DownloadRepository(db_session),
    }


@router.get("/")
async def get_download_queue(
    status: Optional[str] = Query(None, description="Filter by download status"),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of items to return"
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
) -> DownloadQueue:
    """Get the current download queue with all pending, active, and recently completed downloads."""
    try:
        repos = get_repositories_from_session(db_session)

        # Calculate accurate statistics from the full database
        all_statuses = ["pending", "downloading", "completed", "failed"]
        status_counts = {}
        total_orphaned = 0
        for status_type in all_statuses:
            status_downloads = await repos["downloads"].get_by_status(
                status_type, limit=10000
            )
            # Only count downloads that still have their files
            filtered_downloads = []
            orphaned_count = 0
            for download in status_downloads:
                if download.output_path and not os.path.exists(download.output_path):
                    logger.warning(
                        "Found orphaned download record in statistics",
                        download_id=download.id,
                        expected_path=download.output_path,
                        title=download.title,
                        status=status_type,
                    )
                    orphaned_count += 1
                    continue
                filtered_downloads.append(download)

            status_counts[status_type] = len(filtered_downloads)
            total_orphaned += orphaned_count

        if total_orphaned > 0:
            logger.info(
                f"Found {total_orphaned} total orphaned download records across all statuses"
            )

        # Get downloads by status or all if no status specified
        if status:
            downloads = await repos["downloads"].get_by_status(status, limit + offset)
            downloads = downloads[offset : offset + limit]
        else:
            # Get mix of recent downloads from different statuses
            downloads = []
            for status_type in ["pending", "downloading", "completed", "failed"]:
                status_downloads = await repos["downloads"].get_by_status(
                    status_type, limit // 3
                )
                downloads.extend(status_downloads)
            downloads = downloads[:limit]

        # Filter out downloads where the output file no longer exists
        filtered_downloads = []
        orphaned_count = 0
        for download in downloads:
            if download.output_path and not os.path.exists(download.output_path):
                # Log warning for orphaned database records
                logger.warning(
                    "Found orphaned download record - file missing from disk",
                    download_id=download.id,
                    expected_path=download.output_path,
                    title=download.title,
                )
                orphaned_count += 1
                # TODO: Consider auto-cleanup via /api/v1/queue/cleanup-orphaned endpoint
                # or periodic background task instead of manual deletion here
                continue

            filtered_downloads.append(download)

        downloads = filtered_downloads

        if orphaned_count > 0:
            logger.info(
                f"Filtered out {orphaned_count} orphaned download records from queue"
            )

        # Use accurate statistics
        total_items = sum(status_counts.values())
        pending = status_counts.get("pending", 0)
        active = status_counts.get("downloading", 0)
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)

        # Build queue items (simplified - in production you'd want proper pagination)
        queue_items = []
        for download in downloads[:limit]:
            progress_info = None
            if download.progress is not None:
                progress_info = {
                    "percentage": download.progress,
                    "status": download.status,
                }

            queue_items.append(
                {
                    "download_id": download.id,
                    "status": download.status,
                    "progress": progress_info,
                    "current_filename": download.output_path,
                    "message": f"Download {download.status}",
                    "error": download.error_message,
                    "result": (
                        {"url": download.url, "title": download.title}
                        if download.title
                        else {"url": download.url}
                    ),
                    "completed_at": download.completed_at,
                    "created_at": download.created_at,
                }
            )

        return DownloadQueue(
            total_items=total_items,
            pending=pending,
            active=active,
            completed=completed,
            failed=failed,
            items=queue_items,
        )

    except Exception as e:
        logger.error("Failed to get download queue", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get download queue: {str(e)}"
        )


@router.post("/cleanup-orphaned")
async def cleanup_orphaned_downloads(
    dry_run: bool = False,
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
) -> CleanupOrphanedResponse:
    """
    Clean up orphaned download records where files no longer exist on disk.

    This endpoint removes database records for downloads where the output_path
    file is missing from the filesystem. This can happen due to:
    - External file deletion
    - System crashes during deletion
    - Manual database operations

    Use dry_run=true to preview what would be deleted without actually deleting.
    """
    try:
        repos = get_repositories_from_session(db_session)

        # Get all downloads
        all_downloads = await repos["downloads"].get_all(limit=10000)
        orphaned_downloads = []

        for download in all_downloads:
            if download.output_path and not os.path.exists(download.output_path):
                orphaned_downloads.append(download)

        if dry_run:
            return CleanupOrphanedResponse(
                orphaned_count=len(orphaned_downloads),
                deleted_count=0,
                dry_run=True,
                would_delete=[
                    {
                        "id": d.id,
                        "title": d.title,
                        "output_path": d.output_path,
                        "status": d.status,
                        "created_at": d.created_at.isoformat(),
                    }
                    for d in orphaned_downloads
                ],
            )

        # Actually delete orphaned records
        deleted_count = 0
        for download in orphaned_downloads:
            await repos["downloads"].delete(download.id)
            logger.info(f"Cleaned up orphaned download record: {download.id}")
            deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} orphaned download records")
        return CleanupOrphanedResponse(
            orphaned_count=len(orphaned_downloads),
            deleted_count=deleted_count,
            dry_run=False,
        )

    except Exception as e:
        logger.error("Failed to cleanup orphaned downloads", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to cleanup orphaned downloads: {str(e)}"
        )
