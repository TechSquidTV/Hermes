"""
Cleanup endpoint.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_current_api_key
from app.db.repositories import TokenBlacklistRepository
from app.db.session import get_database_session
from app.models.pydantic.cleanup import CleanupRequest, CleanupResponse

router = APIRouter(prefix="/cleanup", tags=["cleanup"])
logger = get_logger(__name__)


def get_repositories_from_session(db_session: AsyncSession):
    """Create repository instances using the provided database session."""
    return {
        "token_blacklist": TokenBlacklistRepository(db_session),
    }


@router.post("/", response_model=CleanupResponse)
async def cleanup_downloads(
    request: CleanupRequest = CleanupRequest(),
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
):
    """
    Clean up old downloads and temporary files.

    This endpoint allows manual cleanup of:
    - Old download files (based on age)
    - Failed download attempts
    - Temporary download files

    Use `dry_run=true` to preview what would be deleted without actually deleting.

    Parameters:
    - `older_than_days`: Delete files older than this many days
    - `delete_failed_downloads`: Include failed download records
    - `delete_temp_files`: Include temporary files
    - `max_files_to_delete`: Safety limit on number of files
    - `dry_run`: Preview mode (no actual deletion)

    Returns statistics on files deleted and space freed.
    """
    try:
        files_deleted = 0
        space_freed = 0
        files_previewed = 0
        errors: List[str] = []

        download_dir = Path(settings.download_dir)
        temp_dir = Path(settings.temp_dir)

        # Cleanup old files
        if request.older_than_days:
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                days=request.older_than_days
            )

            for file_path in download_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                if files_deleted + files_previewed >= request.max_files_to_delete:
                    break

                try:
                    mtime = datetime.fromtimestamp(
                        file_path.stat().st_mtime, tz=timezone.utc
                    )
                    if mtime < cutoff_time:
                        file_size = file_path.stat().st_size

                        if request.dry_run:
                            files_previewed += 1
                            space_freed += file_size
                        else:
                            file_path.unlink()
                            files_deleted += 1
                            space_freed += file_size

                except Exception as e:
                    errors.append(f"Failed to delete {file_path.name}: {str(e)}")

        # Cleanup temp files
        if request.delete_temp_files:
            for file_path in temp_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                if files_deleted + files_previewed >= request.max_files_to_delete:
                    break

                try:
                    file_size = file_path.stat().st_size

                    if request.dry_run:
                        files_previewed += 1
                        space_freed += file_size
                    else:
                        file_path.unlink()
                        files_deleted += 1
                        space_freed += file_size

                except Exception as e:
                    errors.append(
                        f"Failed to delete temp file {file_path.name}: {str(e)}"
                    )

        logger.info(
            "Cleanup operation completed",
            dry_run=request.dry_run,
            files_deleted=files_deleted,
            files_previewed=files_previewed,
            space_freed=space_freed,
        )

        return CleanupResponse(
            files_deleted=files_deleted,
            space_freed=space_freed,
            files_previewed=files_previewed,
            errors=errors,
            dry_run=request.dry_run,
        )

    except Exception as e:
        logger.error("Cleanup operation failed", error=str(e))
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.post("/tokens", response_model=dict)
async def cleanup_expired_tokens(
    dry_run: bool = False,
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
):
    """
    Clean up expired tokens from the blacklist.

    This endpoint removes tokens that have already expired and are no longer
    needed in the blacklist. Helps keep the blacklist table size manageable.

    Parameters:
    - `dry_run`: Preview mode (no actual deletion)

    Returns statistics on tokens deleted.
    """
    try:
        repos = get_repositories_from_session(db_session)

        if dry_run:
            # Count expired tokens without deleting
            from sqlalchemy import func, select

            from app.db.models import TokenBlacklist

            now = datetime.now(timezone.utc)

            result = await repos["token_blacklist"].session.execute(
                select(func.count())
                .select_from(TokenBlacklist)
                .where(TokenBlacklist.expires_at < now)
            )
            count = result.scalar() or 0

            return {
                "would_delete_tokens": count,
                "dry_run": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Actually delete expired tokens
        deleted_count = await repos["token_blacklist"].cleanup_expired()

        logger.info("Expired token cleanup completed", tokens_deleted=deleted_count)

        return {
            "deleted_tokens": deleted_count,
            "dry_run": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error("Expired token cleanup failed", error=str(e))
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=f"Token cleanup failed: {str(e)}")
