"""
Pydantic models for file-related API requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DownloadedFile(BaseModel):
    """Model for downloaded file information."""

    filename: str = Field(..., description="Original filename")
    filepath: str = Field(..., description="Full file path")
    size: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="File creation timestamp")
    modified_at: Optional[datetime] = Field(
        None, description="File modification timestamp"
    )
    video_info: Optional[Dict[str, Any]] = Field(
        None, description="Associated video information"
    )


class FileList(BaseModel):
    """Response model for file listing."""

    total_files: int = Field(..., description="Total number of files found")
    total_size: int = Field(..., description="Total size of all files in bytes")
    files: List[DownloadedFile] = Field(..., description="List of downloaded files")


class DeleteFilesRequest(BaseModel):
    """Request model for file deletion."""

    files: List[str] = Field(
        ..., min_length=1, max_length=100, description="List of file paths to delete"
    )
    confirm: bool = Field(
        default=False, description="Confirmation for destructive operation"
    )


class DeleteFilesResponse(BaseModel):
    """Response model for file deletion."""

    deleted_files: int = Field(..., description="Number of files successfully deleted")
    failed_deletions: List[str] = Field(
        default_factory=list, description="List of files that could not be deleted"
    )
    total_freed_space: int = Field(..., description="Total bytes freed by deletion")
