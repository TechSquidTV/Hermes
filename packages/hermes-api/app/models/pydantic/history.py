"""
Pydantic models for download history and statistics.
"""

from datetime import date as date_type
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    """Individual history record."""

    download_id: str = Field(..., description="Download identifier")
    url: str = Field(..., description="Video URL")
    status: str = Field(..., description="Final status (completed, failed, cancelled)")
    started_at: datetime = Field(..., description="When download started")
    completed_at: datetime = Field(..., description="When download finished")
    duration: float = Field(..., description="Download duration in seconds")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    extractor: str = Field(..., description="Extractor used (e.g., youtube)")
    title: Optional[str] = Field(None, description="Video title")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DailyStats(BaseModel):
    """Daily statistics."""

    date: date_type = Field(..., description="Date")
    downloads: int = Field(..., description="Number of downloads")
    success_rate: float = Field(..., description="Success rate (0.0 to 1.0)")
    total_size: int = Field(0, description="Total bytes downloaded")


class PopularExtractor(BaseModel):
    """Popular extractor statistics."""

    extractor: str = Field(..., description="Extractor name")
    count: int = Field(..., description="Number of downloads")
    percentage: float = Field(..., description="Percentage of total downloads")


class DownloadHistory(BaseModel):
    """Complete download history with statistics."""

    total_downloads: int = Field(..., description="Total number of downloads")
    success_rate: float = Field(..., description="Overall success rate (0.0 to 1.0)")
    average_download_time: float = Field(
        ..., description="Average download time in seconds"
    )
    total_size: int = Field(0, description="Total bytes downloaded")
    popular_extractors: List[PopularExtractor] = Field(
        default_factory=list, description="Most used extractors"
    )
    daily_stats: List[DailyStats] = Field(
        default_factory=list, description="Daily breakdown"
    )
    items: List[HistoryItem] = Field(
        default_factory=list, description="Individual history items"
    )

    # Pagination
    total_items: int = Field(..., description="Total number of items matching filters")
    page: int = Field(1, description="Current page number")
    per_page: int = Field(20, description="Items per page")
