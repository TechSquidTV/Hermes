"""
Pydantic models for storage information.
"""

from typing import List

from pydantic import BaseModel, Field


class CleanupRecommendation(BaseModel):
    """Storage cleanup recommendation."""

    type: str = Field(
        ..., description="Type of cleanup (old_files, failed_downloads, temp_files)"
    )
    description: str = Field(..., description="Human-readable description")
    potential_savings: int = Field(..., description="Bytes that could be freed")
    file_count: int = Field(0, description="Number of files affected")


class StorageInfo(BaseModel):
    """Storage usage information."""

    total_space: int = Field(..., description="Total storage space in bytes")
    used_space: int = Field(..., description="Used storage space in bytes")
    free_space: int = Field(..., description="Free storage space in bytes")
    usage_percentage: float = Field(..., description="Storage usage percentage (0-100)")
    download_directory: str = Field(..., description="Main download directory path")
    temp_directory: str = Field(..., description="Temporary files directory path")
    downloads_size: int = Field(0, description="Size of downloads directory in bytes")
    temp_size: int = Field(0, description="Size of temp directory in bytes")
    cleanup_recommendations: List[CleanupRecommendation] = Field(
        default_factory=list, description="Cleanup recommendations"
    )
