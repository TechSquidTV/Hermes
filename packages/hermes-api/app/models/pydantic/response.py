"""
Common Pydantic response models for API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Current environment")


class FormatDetail(BaseModel):
    """Detailed format information."""

    format_id: Optional[str] = Field(None, description="Format identifier")
    ext: Optional[str] = Field(None, description="File extension")
    resolution: Optional[str] = Field(None, description="Video resolution")
    fps: Optional[float] = Field(None, description="Frames per second")
    vcodec: Optional[str] = Field(None, description="Video codec")
    acodec: Optional[str] = Field(None, description="Audio codec")
    tbr: Optional[float] = Field(None, description="Total bitrate")
    filesize: Optional[int] = Field(None, description="File size in bytes")
    format_note: Optional[str] = Field(None, description="Format description")


class ThumbnailDetail(BaseModel):
    """Detailed thumbnail information."""

    url: str = Field(..., description="Thumbnail URL")
    width: Optional[int] = Field(None, description="Thumbnail width")
    height: Optional[int] = Field(None, description="Thumbnail height")
    resolution: Optional[str] = Field(None, description="Thumbnail resolution")


class SubtitleDetail(BaseModel):
    """Detailed subtitle information."""

    url: str = Field(..., description="Subtitle URL")
    ext: str = Field(..., description="Subtitle file extension")
    lang: Optional[str] = Field(None, description="Language code")


class PlaylistEntry(BaseModel):
    """Playlist entry information."""

    id: str = Field(..., description="Video identifier")
    title: str = Field(..., description="Video title")
    url: str = Field(..., description="Video URL")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    uploader: Optional[str] = Field(None, description="Uploader name")


class VideoInfo(BaseModel):
    """Response model for video information."""

    id: str = Field(..., description="Video unique identifier")
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    uploader: Optional[str] = Field(None, description="Channel/uploader name")
    upload_date: Optional[str] = Field(
        None, description="Upload date (YYYYMMDD format)"
    )
    view_count: Optional[int] = Field(None, description="Number of views")
    webpage_url: str = Field(..., description="Original webpage URL")
    extractor: str = Field(..., description="Extractor used")
    formats: List[FormatDetail] = Field(
        default_factory=list, description="Available download formats"
    )
    thumbnails: List[ThumbnailDetail] = Field(
        default_factory=list, description="Available thumbnails"
    )
    subtitles: Dict[str, List[SubtitleDetail]] = Field(
        default_factory=dict, description="Available subtitles by language"
    )
    # Playlist fields
    playlist_count: Optional[int] = Field(
        None, description="Number of videos in playlist"
    )
    playlist_id: Optional[str] = Field(None, description="Playlist identifier")
    playlist_title: Optional[str] = Field(None, description="Playlist name")
    entries: List[PlaylistEntry] = Field(
        default_factory=list, description="Playlist video entries"
    )


class Error(BaseModel):
    """Error response model."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: Error


class PaginationParams(BaseModel):
    """Common pagination parameters."""

    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum number of items to return"
    )
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class SortParams(BaseModel):
    """Common sorting parameters."""

    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")
