"""
Pydantic models for API statistics.
"""

from typing import List

from pydantic import Field

from app.models.base import CamelCaseModel


class ExtractorStats(CamelCaseModel):
    """Extractor usage statistics."""

    extractor: str = Field(..., description="Extractor name")
    count: int = Field(..., description="Number of uses")
    percentage: float = Field(..., description="Percentage of total")


class ErrorBreakdown(CamelCaseModel):
    """Error type breakdown."""

    error_type: str = Field(..., description="Error type/category")
    count: int = Field(..., description="Number of occurrences")
    percentage: float = Field(..., description="Percentage of failures")


class ApiStatistics(CamelCaseModel):
    """API usage statistics."""

    period: str = Field(..., description="Statistics period (day, week, month, year)")
    total_downloads: int = Field(..., description="Total downloads in period")
    successful_downloads: int = Field(..., description="Successful downloads")
    failed_downloads: int = Field(..., description="Failed downloads")
    success_rate: float = Field(..., description="Success rate (0.0 to 1.0)")
    average_download_time: float = Field(
        ..., description="Average download time in seconds"
    )
    total_bandwidth_used: int = Field(..., description="Total bandwidth in bytes")
    popular_extractors: List[ExtractorStats] = Field(
        default_factory=list, description="Most popular extractors"
    )
    error_breakdown: List[ErrorBreakdown] = Field(
        default_factory=list, description="Error type breakdown"
    )
    peak_hour: int = Field(
        0,
        description="Peak UTC completion hour (0-23); earliest hour wins ties, 0 when history is empty",
    )
    total_storage_used: int = Field(
        0,
        description="Current regular-file bytes under download storage, independent of the selected period; excludes symlinks and temp storage",
    )
