"""
Celery tasks for cleanup and maintenance operations.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.core.logging import get_logger
from app.db.base import async_session_maker
from app.db.repositories import (
    DownloadFileRepository,
    DownloadHistoryRepository,
    DownloadRepository,
    TokenBlacklistRepository,
)
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


async def _get_repositories_for_task():
    """Get repository instances for background tasks with proper session management."""
    async with async_session_maker() as session:
        return {
            "downloads": DownloadRepository(session),
            "download_files": DownloadFileRepository(session),
            "token_blacklist": TokenBlacklistRepository(session),
            "history": DownloadHistoryRepository(session),
        }


async def _get_old_downloads(days: int = 30) -> List[Dict[str, Any]]:
    """Get downloads older than specified days."""
    async with async_session_maker() as session:
        repos = {
            "downloads": DownloadRepository(session),
            "download_files": DownloadFileRepository(session),
            "token_blacklist": TokenBlacklistRepository(session),
            "history": DownloadHistoryRepository(session),
        }
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get downloads that are completed/failed and older than cutoff
        # Note: This would need a proper repository method to be implemented
        logger.info(
            f"Would clean up downloads older than {days} days (cutoff: {cutoff_date})"
        )
        logger.info(f"Repository available: {repos is not None}")

        return []


async def _cleanup_download_files(download_ids: List[str]) -> Dict[str, Any]:
    """Clean up files for specified downloads."""
    total_freed = 0
    deleted_files = 0
    failed_files = []

    async with async_session_maker() as session:
        repos = {
            "downloads": DownloadRepository(session),
            "download_files": DownloadFileRepository(session),
            "token_blacklist": TokenBlacklistRepository(session),
            "history": DownloadHistoryRepository(session),
        }

        for download_id in download_ids:
            try:
                # Get download files
                files = await repos["download_files"].get_by_download_id(download_id)

                for file_info in files:
                    file_path = file_info.filepath
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        total_freed += file_size
                        deleted_files += 1

            except Exception as e:
                logger.error(
                    f"Failed to cleanup files for download {download_id}", error=str(e)
                )
                failed_files.append(download_id)

    return {
        "deleted_files": deleted_files,
        "failed_files": len(failed_files),
        "total_freed_bytes": total_freed,
        "failed_downloads": failed_files,
    }


async def _cleanup_temp_files(max_age_hours: int = 24) -> Dict[str, Any]:
    """Clean up temporary files older than specified hours."""
    temp_dir = os.getenv("HERMES_TEMP_DIR", "./temp")
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    if not os.path.exists(temp_dir):
        return {"deleted_files": 0, "total_freed_bytes": 0}

    total_freed = 0
    deleted_files = 0

    try:
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)

            if os.path.isfile(file_path):
                file_mtime = datetime.fromtimestamp(
                    os.path.getmtime(file_path), tz=timezone.utc
                )

                if file_mtime < cutoff_time:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    total_freed += file_size
                    deleted_files += 1

    except Exception as e:
        logger.error("Failed to cleanup temp files", error=str(e))

    return {"deleted_files": deleted_files, "total_freed_bytes": total_freed}


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_old_downloads")
def cleanup_old_downloads(days: int = 30, dry_run: bool = False) -> Dict[str, Any]:
    """
    Celery task to clean up old download records and files.

    Args:
        days: Remove downloads older than this many days
        dry_run: If True, only report what would be deleted

    Returns:
        Dictionary with cleanup statistics
    """
    return asyncio.run(_cleanup_old_downloads_async(days, dry_run))


async def _cleanup_old_downloads_async(
    days: int = 30, dry_run: bool = False
) -> Dict[str, Any]:
    """Async implementation of cleanup_old_downloads."""
    logger.info(
        f"Starting cleanup of downloads older than {days} days", dry_run=dry_run
    )

    try:
        # Get old downloads
        old_downloads = await _get_old_downloads(days)

        if not old_downloads:
            logger.info("No old downloads found for cleanup")
            return {
                "total_downloads": 0,
                "deleted_downloads": 0,
                "deleted_files": 0,
                "total_freed_bytes": 0,
            }

        download_ids = [d["id"] for d in old_downloads]

        if dry_run:
            # Just count what would be deleted
            total_files = 0
            async with async_session_maker() as session:
                repos = {
                    "downloads": DownloadRepository(session),
                    "download_files": DownloadFileRepository(session),
                    "token_blacklist": TokenBlacklistRepository(session),
                    "history": DownloadHistoryRepository(session),
                }

                for download_id in download_ids:
                    files = await repos["download_files"].get_by_download_id(
                        download_id
                    )
                    total_files += len(files)

            return {
                "total_downloads": len(download_ids),
                "would_delete_downloads": len(download_ids),
                "would_delete_files": total_files,
                "dry_run": True,
            }

        # Actually delete
        file_cleanup = await _cleanup_download_files(download_ids)

        # Delete download records from database
        deleted_downloads = 0
        async with async_session_maker() as session:
            repos = {
                "downloads": DownloadRepository(session),
                "download_files": DownloadFileRepository(session),
                "token_blacklist": TokenBlacklistRepository(session),
                "history": DownloadHistoryRepository(session),
            }

            for download_id in download_ids:
                try:
                    # First delete associated files records
                    await repos["download_files"].delete_by_download_id(download_id)
                    # Then delete the download record
                    await repos["downloads"].delete(download_id)
                    deleted_downloads += 1
                except Exception as e:
                    logger.error(
                        f"Failed to delete download record {download_id}", error=str(e)
                    )

        logger.info(
            "Cleanup completed",
            downloads_deleted=deleted_downloads,
            files_deleted=file_cleanup["deleted_files"],
            bytes_freed=file_cleanup["total_freed_bytes"],
        )

        return {
            "total_downloads": len(download_ids),
            "deleted_downloads": deleted_downloads,
            "deleted_files": file_cleanup["deleted_files"],
            "total_freed_bytes": file_cleanup["total_freed_bytes"],
            "failed_downloads": file_cleanup["failed_files"],
        }

    except Exception as e:
        logger.error("Cleanup task failed", error=str(e))
        return {
            "error": str(e),
            "total_downloads": 0,
            "deleted_downloads": 0,
            "deleted_files": 0,
            "total_freed_bytes": 0,
        }


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_temp_files")
def cleanup_temp_files(
    max_age_hours: int = 24, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Celery task to clean up temporary files.

    Args:
        max_age_hours: Remove files older than this many hours
        dry_run: If True, only report what would be deleted

    Returns:
        Dictionary with cleanup statistics
    """
    return asyncio.run(_cleanup_temp_files_async(max_age_hours, dry_run))


async def _cleanup_temp_files_async(
    max_age_hours: int = 24, dry_run: bool = False
) -> Dict[str, Any]:
    """Async implementation of cleanup_temp_files."""
    logger.info(
        f"Starting cleanup of temp files older than {max_age_hours} hours",
        dry_run=dry_run,
    )

    try:
        temp_dir = os.getenv("HERMES_TEMP_DIR", "./temp")
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        if not os.path.exists(temp_dir):
            result = {"deleted_files": 0, "total_freed_bytes": 0}
            if dry_run:
                result["would_delete_files"] = 0
                result["would_free_bytes"] = 0
                result["dry_run"] = True
            return result

        if dry_run:
            # Just count what would be deleted without actually deleting
            total_would_free = 0
            would_delete_files = 0

            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)

                if os.path.isfile(file_path):
                    file_mtime = datetime.fromtimestamp(
                        os.path.getmtime(file_path), tz=timezone.utc
                    )

                    if file_mtime < cutoff_time:
                        file_size = os.path.getsize(file_path)
                        total_would_free += file_size
                        would_delete_files += 1

            return {
                "would_delete_files": would_delete_files,
                "would_free_bytes": total_would_free,
                "dry_run": True,
            }

        # Actually delete
        temp_cleanup = await _cleanup_temp_files(max_age_hours)

        logger.info(
            "Temp file cleanup completed",
            files_deleted=temp_cleanup["deleted_files"],
            bytes_freed=temp_cleanup["total_freed_bytes"],
        )

        return temp_cleanup

    except Exception as e:
        logger.error("Temp file cleanup task failed", error=str(e))
        return {"error": str(e), "deleted_files": 0, "total_freed_bytes": 0}


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_expired_tokens")
def cleanup_expired_tokens(dry_run: bool = False) -> Dict[str, Any]:
    """
    Celery task to clean up expired tokens from the blacklist.

    This removes tokens that have already expired and are no longer needed
    in the blacklist. Keeps the blacklist table size manageable.

    Args:
        dry_run: If True, only report what would be deleted

    Returns:
        Dictionary with cleanup statistics
    """
    return asyncio.run(_cleanup_expired_tokens_async(dry_run))


async def _cleanup_expired_tokens_async(dry_run: bool = False) -> Dict[str, Any]:
    """Async implementation of cleanup_expired_tokens."""
    logger.info("Starting cleanup of expired blacklisted tokens", dry_run=dry_run)

    try:
        now = datetime.now(timezone.utc)

        async with async_session_maker() as session:
            repos = {
                "downloads": DownloadRepository(session),
                "download_files": DownloadFileRepository(session),
                "token_blacklist": TokenBlacklistRepository(session),
                "history": DownloadHistoryRepository(session),
            }

            if dry_run:
                # Count expired tokens without deleting
                from sqlalchemy import func, select

                from app.db.models import TokenBlacklist

                stmt = (
                    select(func.count())
                    .select_from(TokenBlacklist)
                    .where(TokenBlacklist.expires_at < now)
                )
                result = await repos["token_blacklist"].session.execute(stmt)
                count = result.scalar() or 0

                return {"would_delete_tokens": count, "dry_run": True}

            # Actually delete expired tokens
            deleted_count = await repos["token_blacklist"].cleanup_expired()

        logger.info("Expired token cleanup completed", tokens_deleted=deleted_count)

        return {
            "deleted_tokens": deleted_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error("Expired token cleanup task failed", error=str(e))
        return {"error": str(e), "deleted_tokens": 0}
