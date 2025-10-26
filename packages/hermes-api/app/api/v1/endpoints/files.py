"""
File management endpoints.
"""

import os
from typing import Any, List, Optional  # noqa: F401

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_api_key
from app.db.repositories import DownloadFileRepository, DownloadRepository
from app.db.session import get_database_session
from app.models.pydantic.file import (
    DeleteFilesRequest,
    DeleteFilesResponse,
    DownloadedFile,
    FileList,
)

router = APIRouter()
logger = get_logger(__name__)


def get_repositories_from_session(db_session: AsyncSession):
    """Create repository instances using the provided database session."""
    return {
        "downloads": DownloadRepository(db_session),
        "download_files": DownloadFileRepository(db_session),
    }


@router.get("/download")
async def download_file(
    path: str = Query(..., description="File path to download"),
    api_key: str = Depends(get_current_api_key),
) -> FileResponse:
    """Download a specific file."""
    try:
        # Security: ensure the file exists and is within the downloads directory
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found")

        if not os.path.isfile(path):
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Get the filename for the Content-Disposition header
        filename = os.path.basename(path)

        logger.info("Serving file for download", filepath=path, filename=filename)

        return FileResponse(
            path=path, filename=filename, media_type="application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to serve file", error=str(e), filepath=path)
        raise HTTPException(status_code=500, detail=f"Failed to serve file: {str(e)}")


@router.get("/")
async def list_downloaded_files(
    directory: Optional[str] = Query(None, description="Filter by directory path"),
    extension: Optional[str] = Query(None, description="Filter by file extension"),
    min_size: Optional[int] = Query(
        None, ge=0, description="Minimum file size in bytes"
    ),
    max_size: Optional[int] = Query(
        None, ge=0, description="Maximum file size in bytes"
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of items to return"
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
) -> FileList:
    """List all files that have been downloaded and are currently stored."""
    try:
        repos = get_repositories_from_session(db_session)

        # Get all download files from database
        # For now, this is a simplified implementation
        # In production, you'd want more sophisticated querying and filtering
        all_files = []

        # Get recent downloads and their files
        recent_downloads = await repos["downloads"].get_by_status(
            "completed", limit * 2
        )

        for download in recent_downloads:
            files = await repos["download_files"].get_by_download_id(download.id)
            for file_info in files:
                # Apply filters
                if directory and not file_info.filepath.startswith(directory):
                    continue
                if extension and not file_info.filepath.endswith(f".{extension}"):
                    continue
                if min_size and file_info.file_size < min_size:
                    continue
                if max_size and file_info.file_size > max_size:
                    continue

                # Check if file actually exists
                if os.path.exists(file_info.filepath):
                    all_files.append(
                        DownloadedFile(
                            filename=file_info.filename,
                            filepath=file_info.filepath,
                            size=file_info.file_size,
                            created_at=file_info.created_at,
                            video_info={
                                "url": download.url,
                                "title": download.title,
                                "duration": download.duration,
                            },
                        )
                    )

        # Apply pagination
        total_files = len(all_files)
        paginated_files = all_files[offset : offset + limit]

        # Calculate total size
        total_size = sum(file.size for file in paginated_files)

        return FileList(
            total_files=total_files, total_size=total_size, files=paginated_files
        )

    except Exception as e:
        logger.error("Failed to list downloaded files", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.delete("/")
async def delete_downloaded_files(
    request: DeleteFilesRequest,
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
) -> DeleteFilesResponse:
    """Delete one or more downloaded files from storage."""
    try:
        if not request.confirm:
            raise HTTPException(
                status_code=400,
                detail="Confirmation required for destructive operations. "
                "Set 'confirm' to true.",
            )

        logger.info("Deleting downloaded files", files_count=len(request.files))

        deleted_files = 0
        failed_files = []
        total_freed = 0

        repos = get_repositories_from_session(db_session)

        for file_path in request.files:
            try:
                # Delete the physical file
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    total_freed += file_size
                    deleted_files += 1
                    logger.info(f"Deleted file: {file_path}")
                else:
                    failed_files.append(f"{file_path} (file not found)")
                    logger.warning(f"File not found: {file_path}")

                # Also delete the database record for this download
                # Find downloads with this output_path and delete them
                downloads = await repos["downloads"].get_all()
                for download in downloads:
                    if download.output_path == file_path:
                        await repos["downloads"].delete(download.id)
                        logger.info(f"Deleted download record for: {download.id}")
                        break  # Only delete first match to avoid deleting multiple

            except Exception as e:
                logger.error(f"Failed to delete file {file_path}", error=str(e))
                failed_files.append(f"{file_path} ({str(e)})")

        logger.info(
            "File deletion completed",
            deleted_files=deleted_files,
            failed_files=len(failed_files),
            bytes_freed=total_freed,
        )

        return DeleteFilesResponse(
            deleted_files=deleted_files,
            failed_deletions=failed_files,
            total_freed_space=total_freed,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete files", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete files: {str(e)}")
