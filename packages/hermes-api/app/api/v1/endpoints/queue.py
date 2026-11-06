"""
Queue management endpoints.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from app.models.status import DownloadState
from app.utils.files import relative_download_path, resolve_download_path

router = APIRouter()
logger = get_logger(__name__)


@router.get("/")
async def get_download_queue(
    status: Optional[DownloadState] = Query(
        None, description="Filter by download status"
    ),
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

    This endpoint removes terminal download records only when every known
    managed deliverable, including the primary output, is missing. This can happen due to:
    - External file deletion
    - System crashes during deletion
    - Manual database operations

    Use dry_run=true to preview what would be deleted without actually deleting.
    """
    repos = get_repositories_from_session(db_session)

    orphaned_downloads = []
    last_id = ""
    while True:
        downloads = (
            await db_session.scalars(
                select(Download)
                .options(selectinload(Download.files))
                .where(
                    Download.id > last_id,
                    Download.status.in_(["completed", "failed", "cancelled"]),
                )
                .order_by(Download.id)
                .limit(100)
            )
        ).all()
        if not downloads:
            break
        for download in downloads:
            if _is_orphaned(download):
                orphaned_downloads.append(download)
        last_id = downloads[-1].id

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
        current = await repos["downloads"].get_by_id(download.id)
        if current is None or not _is_orphaned(current):
            continue
        await repos["downloads"].delete(current.id)
        logger.info(f"Cleaned up orphaned download record: {download.id}")
        deleted_count += 1

    logger.info(f"Cleaned up {deleted_count} orphaned download records")
    return CleanupOrphanedResponse(
        orphaned_count=len(orphaned_downloads),
        deleted_count=deleted_count,
        dry_run=False,
    )


def _is_orphaned(download: Download) -> bool:
    if download.status not in {"completed", "failed", "cancelled"}:
        return False
    paths = {file.filepath for file in download.files}
    if download.output_path:
        paths.add(download.output_path)
    if not paths:
        return False
    for path in paths:
        try:
            if resolve_download_path(path).is_file():
                return False
        except (OSError, ValueError, RuntimeError):
            continue
    return True
