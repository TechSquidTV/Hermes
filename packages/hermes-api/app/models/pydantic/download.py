"""
Pydantic models for download-related API requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class DownloadRequest(BaseModel):
    """Request model for starting a download."""

    url: str = Field(
        ..., description="Video URL to download", min_length=1, max_length=2048
    )
    format: str = Field(
        default="best",
        description=(
            "Format selection specification. "
            "Examples: 'best', 'worst', 'bestvideo+bestaudio', 'mp4', 'bestaudio', "
            "'bestvideo[height<=720]+bestaudio', or specific format IDs like '137+140'. "
            "See GET /formats endpoint for all available options and detailed descriptions."
        ),
        json_schema_extra={
            "example": "best",
            "examples": [
                "best",
                "bestvideo+bestaudio",
                "bestvideo[height<=1080]+bestaudio",
                "bestaudio[ext=m4a]",
                "mp4",
            ],
        },
    )
    output_template: Optional[str] = Field(None, description="Output filename template")
    download_subtitles: bool = Field(
        default=False, description="Whether to download subtitles"
    )
    download_thumbnail: bool = Field(
        default=False, description="Whether to download thumbnail"
    )
    subtitle_languages: Optional[List[str]] = Field(
        None, description="List of subtitle languages to download"
    )
    output_directory: Optional[str] = Field(None, description="Custom output directory")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata for the download"
    )

    # Cookie support
    cookies: Optional[Dict[str, str]] = Field(
        None, description="Custom cookies to use for the download"
    )
    cookie_file: Optional[str] = Field(
        None, description="Path to cookie file for authentication"
    )
    browser_cookies: Optional[Dict[str, str]] = Field(
        None, description="Browser cookie extraction settings"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("subtitle_languages")
    @classmethod
    def validate_subtitle_languages(cls, v):
        """Validate subtitle language codes."""
        if v:
            # Basic validation - could be expanded with proper language code validation
            for lang in v:
                if not isinstance(lang, str) or len(lang) < 2:
                    raise ValueError(f"Invalid language code: {lang}")
        return v


class DownloadResult(BaseModel):
    """Final video information when download is completed."""

    url: Optional[str] = Field(None, description="Original video URL")
    title: Optional[str] = Field(None, description="Video title")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    duration: Optional[float] = Field(None, description="Video duration in seconds")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    extractor: Optional[str] = Field(
        None, description="Extractor used (youtube, vimeo, etc)"
    )
    description: Optional[str] = Field(None, description="Video description")


class DownloadProgress(BaseModel):
    """Download progress information."""

    percentage: Optional[float] = Field(None, description="Download percentage (0-100)")
    status: Optional[str] = Field(None, description="Current progress status")
    downloaded_bytes: Optional[int] = Field(
        None, description="Number of bytes downloaded"
    )
    total_bytes: Optional[int] = Field(None, description="Total bytes to download")
    speed: Optional[float] = Field(
        None, description="Download speed in bytes per second"
    )
    eta: Optional[float] = Field(
        None, description="Estimated time remaining in seconds"
    )


class DownloadResponse(BaseModel):
    """Response model for download initiation."""

    download_id: str = Field(..., description="Unique identifier for this download")
    status: str = Field(..., description="Current download status")
    message: str = Field(..., description="Status message")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )


class DownloadStatus(BaseModel):
    """Response model for download status."""

    download_id: str = Field(..., description="Unique download identifier")
    status: str = Field(..., description="Current download status")
    progress: Optional[DownloadProgress] = Field(
        None, description="Progress information"
    )
    current_filename: Optional[str] = Field(
        None, description="Current output filename being written"
    )
    message: str = Field(..., description="Current status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    result: Optional[DownloadResult] = Field(
        None, description="Final video information when completed"
    )


class CancelResponse(BaseModel):
    """Response model for download cancellation."""

    download_id: str = Field(..., description="Download identifier that was cancelled")
    cancelled: bool = Field(..., description="Whether cancellation was successful")
    message: str = Field(..., description="Cancellation result message")


class BatchDownloadRequest(BaseModel):
    """Request model for batch downloads."""

    urls: List[str] = Field(
        ..., min_length=1, max_length=50, description="List of video URLs to download"
    )
    format: str = Field(
        default="best",
        description=(
            "Format selection for all downloads. "
            "See GET /formats endpoint for available options. "
            "Examples: 'best', 'bestvideo+bestaudio', 'mp4'"
        ),
    )
    download_subtitles: bool = Field(
        default=False, description="Whether to download subtitles for all videos"
    )
    download_thumbnail: bool = Field(
        default=False, description="Whether to download thumbnails for all videos"
    )
    output_directory: Optional[str] = Field(
        None, description="Base output directory for all downloads"
    )
    priority: str = Field(default="normal", description="Download priority")

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v):
        """Validate all URLs in the batch."""
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL format: {url}")
        return v


class BatchDownloadResponse(BaseModel):
    """Response model for batch download initiation."""

    batch_id: str = Field(..., description="Unique identifier for the batch download")
    total_downloads: int = Field(
        ..., description="Total number of downloads in the batch"
    )
    status: str = Field(..., description="Current batch status")
    downloads: List[str] = Field(..., description="List of individual download IDs")


class DownloadQueue(BaseModel):
    """Response model for download queue information."""

    total_items: int = Field(..., description="Total number of items in queue")
    pending: int = Field(..., description="Number of pending downloads")
    active: int = Field(..., description="Number of active downloads")
    completed: int = Field(..., description="Number of completed downloads")
    failed: int = Field(..., description="Number of failed downloads")
    items: List[DownloadStatus] = Field(
        ..., description="List of download items in the queue"
    )


class CleanupOrphanedResponse(BaseModel):
    """Response model for cleanup orphaned downloads."""

    orphaned_count: int = Field(..., description="Number of orphaned downloads found")
    deleted_count: int = Field(..., description="Number of orphaned downloads deleted")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    would_delete: Optional[List[Dict[str, Any]]] = Field(
        None, description="Details of downloads that would be deleted (dry run only)"
    )
