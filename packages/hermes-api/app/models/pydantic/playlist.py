"""
Pydantic models for playlist and batch operations.

These models provide type-safe data structures for playlist extraction,
batch management, and progress tracking.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# yt-dlp result types (from YouTubeDL.py line ~3300)
YTDLResultType = Literal[
    "video", "playlist", "multi_video", "url", "url_transparent", "compat_list"
]

# Batch types
BatchType = Literal["playlist", "manual_batch", "api_batch"]

# Status enums
BatchStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
VideoStatus = Literal[
    "pending", "queued", "downloading", "completed", "failed", "skipped"
]


class PlaylistVideoInfo(BaseModel):
    """
    Represents a single video entry from a playlist.
    Extracted from yt-dlp info_dict['entries'][n]
    """

    url: str = Field(description="Video webpage URL from 'webpage_url' or 'url' field")
    video_id: str = Field(description="Video ID from 'id' field")
    title: str = Field(description="Video title from 'title' field")
    duration: Optional[int] = Field(
        None, description="Duration in seconds from 'duration' field"
    )
    thumbnail: Optional[str] = Field(
        None, description="Thumbnail URL from 'thumbnail' field"
    )
    uploader: Optional[str] = Field(
        None, description="Video uploader from 'uploader' field"
    )
    view_count: Optional[int] = Field(
        None, description="View count from 'view_count' field"
    )
    upload_date: Optional[str] = Field(
        None, description="Upload date YYYYMMDD from 'upload_date' field"
    )


class PlaylistInfo(BaseModel):
    """
    Complete playlist information extracted from yt-dlp.
    Maps to yt-dlp info_dict when _type is 'playlist' or 'multi_video'
    """

    is_playlist: bool = Field(description="True if URL is a playlist")
    playlist_type: YTDLResultType = Field(description="Type from info_dict['_type']")
    playlist_title: str = Field(description="Playlist name from 'title' field")
    playlist_id: str = Field(description="Playlist ID from 'id' field")
    playlist_url: str = Field(description="Original playlist URL from 'webpage_url'")
    uploader: Optional[str] = Field(
        None, description="Playlist creator from 'uploader' field"
    )
    uploader_id: Optional[str] = Field(
        None, description="Uploader ID from 'uploader_id' field"
    )
    video_count: int = Field(description="Number of videos, len(info_dict['entries'])")
    videos: list[PlaylistVideoInfo] = Field(
        description="List of video entries from 'entries' field"
    )
    description: Optional[str] = Field(
        None, description="Playlist description from 'description' field"
    )


class SingleVideoInfo(BaseModel):
    """
    Single video information when URL is not a playlist.
    Maps to yt-dlp info_dict when _type is 'video'
    """

    is_playlist: Literal[False] = Field(default=False)
    url: str = Field(description="Video webpage URL from 'webpage_url' or 'url'")
    video_id: str = Field(description="Video ID from 'id' field")
    title: str = Field(description="Video title from 'title' field")
    duration: Optional[int] = Field(
        None, description="Duration in seconds from 'duration'"
    )
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL from 'thumbnail'")
    uploader: Optional[str] = Field(None, description="Uploader from 'uploader'")
    description: Optional[str] = Field(
        None, description="Video description from 'description'"
    )


class UrlDetectionResult(BaseModel):
    """Result of URL type detection"""

    url: str
    url_type: Literal["playlist", "video", "unknown"]
    metadata: Optional[PlaylistInfo | SingleVideoInfo] = None


class BatchCreateParams(BaseModel):
    """Parameters for creating a batch"""

    user_id: str
    batch_type: BatchType
    batch_title: Optional[str] = None
    source_url: Optional[str] = None
    format_spec: str = "best"
    output_directory: Optional[str] = None
    videos: list[PlaylistVideoInfo] = Field(default_factory=list)


class BatchProgressInfo(BaseModel):
    """Current batch progress information"""

    batch_id: str
    status: BatchStatus
    total_videos: int
    completed_videos: int
    failed_videos: int
    pending_videos: int
    overall_progress: float = Field(ge=0.0, le=100.0)


class BatchCreateResult(BaseModel):
    """Result of batch creation"""

    batch_id: str
    batch_title: str
    batch_type: BatchType
    status: BatchStatus
    total_videos: int
    created_at: datetime


class BatchStartResult(BaseModel):
    """Result of starting a batch"""

    batch_id: str
    queued_count: int
    failed_count: int
    task_ids: list[str]


# API Request/Response Models


class DetectUrlTypeRequest(BaseModel):
    """Request to detect URL type"""

    url: str


class DetectUrlTypeResponse(BaseModel):
    """Response from URL type detection"""

    success: bool
    url_type: Literal["playlist", "video", "unknown"]
    metadata: Optional[dict] = None


class ParsePlaylistRequest(BaseModel):
    """Request to parse a playlist"""

    url: str
    extract_flat: bool = True


class ParsePlaylistResponse(BaseModel):
    """Response from playlist parsing"""

    success: bool
    playlist: Optional[PlaylistInfo] = None
    message: str


class CreateBatchRequest(BaseModel):
    """Request to create a batch"""

    source_type: Literal["playlist", "manual"]
    playlist_url: Optional[str] = None
    urls: Optional[list[str]] = None
    batch_title: Optional[str] = None
    format_spec: str = "best"
    output_directory: Optional[str] = None
    start_immediately: bool = True


class CreateBatchResponse(BaseModel):
    """Response from batch creation"""

    success: bool
    batch_id: str
    batch_title: str
    batch_type: BatchType
    total_videos: int
    status: BatchStatus
    created_at: datetime
