"""
Queue management endpoints.
"""

import os
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_repositories_from_session
from app.core.logging import get_logger
from app.core.security import ApiKeyPermission, AuthPrincipal, require_api_permission
from app.db.models import Download
from app.db.session import get_database_session
from app.models.pydantic.download import (
    CleanupOrphanedResponse,
    DownloadQueue,
    DownloadStatus,
)
from app.utils.files import relative_download_path

router = APIRouter()
logger = get_logger(__name__)


@router.get("/")
async def get_download_queue(
    status: Optional[str] = Query(None, description="Filter by download status"),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of items to return"
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    view_mode: Literal["active", "history", "all"] = Query("all"),
    search: str = Query("", max_length=200),
    sort_by: Literal["date", "title", "size", "status"] = Query("date"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.READ)),
) -> DownloadQueue:
    """Get the current download queue with all pending, active, and recently completed downloads."""
    query = select(Download)
    if view_mode == "active":
        query = query.where(Download.status != "completed")
    elif view_mode == "history":
        query = query.where(Download.status == "completed")
    if status:
        query = query.where(Download.status == status)
    if search:
        query = query.where(
            or_(
                Download.title.icontains(search, autoescape=True),
                Download.url.icontains(search, autoescape=True),
            )
        )

    total_items = int(
        await db_session.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    counts = await db_session.execute(
        select(Download.status, func.count()).group_by(Download.status)
    )
    status_counts = {name: int(count) for name, count in counts.all()}
    sort_column = {
        "date": Download.created_at,
        "title": Download.title,
        "size": Download.file_size,
        "status": Download.status,
    }[sort_by]
    ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    downloads = (
        await db_session.scalars(
            query.order_by(ordering.nulls_last(), Download.id)
            .offset(offset)
            .limit(limit)
        )
    ).all()
    pending = status_counts.get("pending", 0)
    active = status_counts.get("downloading", 0) + status_counts.get("processing", 0)
    completed = status_counts.get("completed", 0)
    failed = status_counts.get("failed", 0)

    # Build the requested page without dropping records for missing media.
    queue_items = []
    for download in downloads[:limit]:
        progress_info = None
        if download.progress is not None:
            progress_info = {
                "percentage": download.progress,
                "status": download.status,
                "downloaded_bytes": download.downloaded_bytes,
                "total_bytes": download.total_bytes,
                "speed": download.download_speed,
                "eta": download.eta,
            }

        queue_items.append(
            DownloadStatus.model_validate(
                {
                    "download_id": download.id,
                    "status": download.status,
                    "progress": progress_info,
                    "current_filename": relative_download_path(download.output_path),
                    "message": f"Download {download.status}",
                    "error": download.error_message,
                    "result": (
                        {
                            "url": download.url,
                            "title": download.title,
                            "file_size": download.file_size,
                            "thumbnail_url": download.thumbnail_url,
                        }
                        if download.title
                        else {"url": download.url}
                    ),
                    "completed_at": download.completed_at,
                    "created_at": download.created_at,
                }
            )
        )

    return DownloadQueue(
        total_items=total_items,
        pending=pending,
        active=active,
        completed=completed,
        failed=failed,
        items=queue_items,
    )


@router.post("/cleanup-orphaned")
async def cleanup_orphaned_downloads(
    dry_run: bool = False,
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.WRITE)),
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
