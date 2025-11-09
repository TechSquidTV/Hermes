"""
Pydantic models for cleanup operations.
"""

from typing import List, Optional

from pydantic import Field

from app.models.base import CamelCaseModel


class CleanupRequest(CamelCaseModel):
    """Request for cleanup operation."""

    older_than_days: Optional[int] = Field(
        None, ge=1, description="Delete files older than N days"
    )
    delete_failed_downloads: bool = Field(
        False, description="Delete records of failed downloads"
    )
    delete_temp_files: bool = Field(True, description="Delete temporary download files")
    max_files_to_delete: int = Field(
        100, ge=1, le=1000, description="Maximum number of files to delete"
    )
    dry_run: bool = Field(
        False, description="Preview what would be deleted without actually deleting"
    )


class CleanupResponse(CamelCaseModel):
    """Response from cleanup operation."""

    files_deleted: int = Field(..., description="Number of files actually deleted")
    space_freed: int = Field(..., description="Total space freed in bytes")
    files_previewed: int = Field(
        0, description="Files that would be deleted (dry_run=true)"
    )
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    dry_run: bool = Field(..., description="Whether this was a dry run")
