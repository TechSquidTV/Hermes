"""
Cleanup endpoint.
"""

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_repositories_from_session
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import ApiKeyPermission, AuthPrincipal, require_api_permission
from app.db.models import Download
from app.db.session import get_database_session
from app.models.pydantic.cleanup import CleanupRequest, CleanupResponse
from app.services.file_cleanup import (
    active_download_prefixes,
    cleanup_candidates,
    download_artifacts,
    remove_download_artifacts,
    temporary_cleanup_candidates,
)

router = APIRouter(prefix="/cleanup", tags=["cleanup"])
logger = get_logger(__name__)


@router.post("/", response_model=CleanupResponse)
async def cleanup_downloads(
    request: CleanupRequest = CleanupRequest(),
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.ADMIN)),
) -> CleanupResponse:
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
    files_deleted = 0
    space_freed = 0
    files_previewed = 0
    records_deleted = 0
    records_previewed = 0
    errors: List[str] = []

    download_dir = Path(settings.download_dir)
    active_prefixes = await active_download_prefixes(db_session)

    async def candidates() -> AsyncIterator[Path]:
        if request.older_than_days:
            for path in cleanup_candidates(
                download_dir, request.older_than_days * 24, active_prefixes
            ):
                yield path
        if request.delete_temp_files:
            async for path in temporary_cleanup_candidates(
                db_session, request.temp_max_age_hours
            ):
                yield path

    seen: set[Path] = set()
    async for file_path in candidates():
        if files_deleted + files_previewed >= request.max_files_to_delete:
            break
        resolved = file_path.resolve()
        if resolved in seen:
            continue
        try:
            file_size = file_path.stat().st_size
            if request.dry_run:
                files_previewed += 1
            else:
                file_path.unlink()
                files_deleted += 1
            space_freed += file_size
            seen.add(resolved)
        except OSError:
            logger.exception("File cleanup failed")
            errors.append("File cleanup failed")

    if request.delete_failed_downloads:
        remaining = request.max_files_to_delete - files_deleted - files_previewed
        if remaining > 0:
            failed = (
                await db_session.scalars(
                    select(Download)
                    .where(Download.status == "failed")
                    .order_by(Download.id)
                    .limit(remaining)
                )
            ).all()
            artifacts_by_id = download_artifacts([download.id for download in failed])
            for download in failed:
                budget = (
                    request.max_files_to_delete
                    - files_deleted
                    - files_previewed
                    - records_deleted
                    - records_previewed
                )
                if budget <= 0:
                    break
                try:
                    artifacts = remove_download_artifacts(
                        download.id,
                        limit=budget,
                        dry_run=request.dry_run,
                        paths=artifacts_by_id[download.id],
                        excluded_paths=(
                            {str(path) for path in seen} if request.dry_run else ()
                        ),
                    )
                except OSError:
                    logger.exception("Failed artifact cleanup")
                    errors.append("Failed artifact cleanup")
                    continue
                space_freed += artifacts.bytes_freed
                if request.dry_run:
                    files_previewed += artifacts.files
                else:
                    files_deleted += artifacts.files
                if artifacts.failed:
                    errors.append("Failed artifact cleanup")
                if not artifacts.complete or artifacts.files >= budget:
                    continue
                if request.dry_run:
                    records_previewed += 1
                else:
                    await db_session.delete(download)
                    records_deleted += 1
            if not request.dry_run:
                await db_session.commit()

    logger.info(
        "Cleanup operation completed",
        dry_run=request.dry_run,
        files_deleted=files_deleted,
        records_deleted=records_deleted,
        records_previewed=records_previewed,
        files_previewed=files_previewed,
        space_freed=space_freed,
    )

    return CleanupResponse(
        files_deleted=files_deleted,
        records_deleted=records_deleted,
        records_previewed=records_previewed,
        space_freed=space_freed,
        files_previewed=files_previewed,
        errors=errors,
        dry_run=request.dry_run,
    )


@router.post("/tokens", response_model=dict)
async def cleanup_expired_tokens(
    dry_run: bool = False,
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.ADMIN)),
) -> dict[str, object]:
    """
    Clean up expired tokens from the blacklist.

    This endpoint removes tokens that have already expired and are no longer
    needed in the blacklist. Helps keep the blacklist table size manageable.

    Parameters:
    - `dry_run`: Preview mode (no actual deletion)

    Returns statistics on tokens deleted.
    """
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
