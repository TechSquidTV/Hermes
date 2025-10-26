"""
Pydantic models for configuration management.
"""

from typing import Optional

from pydantic import BaseModel, Field


class Configuration(BaseModel):
    """Current API configuration."""

    # Download settings
    output_template: str = Field(..., description="Default output filename template")
    default_format: str = Field(..., description="Default format selection")
    download_subtitles: bool = Field(
        ..., description="Default subtitle download setting"
    )
    download_thumbnail: bool = Field(
        ..., description="Default thumbnail download setting"
    )
    output_directory: str = Field(..., description="Default output directory")

    # Performance settings
    max_concurrent_downloads: int = Field(
        ..., ge=1, le=10, description="Maximum concurrent downloads"
    )
    retry_attempts: int = Field(
        ..., ge=0, le=10, description="Number of retry attempts"
    )
    timeout: int = Field(..., ge=10, description="Request timeout in seconds")

    # Storage settings
    temp_directory: str = Field(..., description="Temporary files directory")
    cleanup_enabled: bool = Field(True, description="Automatic cleanup enabled")
    cleanup_older_than_days: int = Field(
        30, description="Auto-cleanup file age threshold"
    )

    # API settings
    rate_limit_per_minute: int = Field(..., description="API rate limit per minute")
    debug_mode: bool = Field(..., description="Debug mode enabled")


class ConfigurationUpdate(BaseModel):
    """Configuration update request."""

    # Download settings
    output_template: Optional[str] = Field(
        None, description="Default output filename template"
    )
    default_format: Optional[str] = Field(None, description="Default format selection")
    download_subtitles: Optional[bool] = Field(
        None, description="Default subtitle download setting"
    )
    download_thumbnail: Optional[bool] = Field(
        None, description="Default thumbnail download setting"
    )
    output_directory: Optional[str] = Field(
        None, description="Default output directory"
    )

    # Performance settings
    max_concurrent_downloads: Optional[int] = Field(
        None, ge=1, le=10, description="Maximum concurrent downloads"
    )
    retry_attempts: Optional[int] = Field(
        None, ge=0, le=10, description="Number of retry attempts"
    )
    timeout: Optional[int] = Field(
        None, ge=10, description="Request timeout in seconds"
    )

    # Storage settings
    cleanup_enabled: Optional[bool] = Field(
        None, description="Automatic cleanup enabled"
    )
    cleanup_older_than_days: Optional[int] = Field(
        None, ge=1, description="Auto-cleanup file age threshold"
    )

    # API settings
    rate_limit_per_minute: Optional[int] = Field(
        None, ge=1, description="API rate limit per minute"
    )
