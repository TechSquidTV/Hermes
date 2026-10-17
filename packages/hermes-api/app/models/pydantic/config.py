"""
Pydantic models for configuration management.
"""

from typing import Optional

from pydantic import Field

from app.models.base import CamelCaseModel


class Configuration(CamelCaseModel):
    """Non-secret startup settings of the responding API process."""

    output_directory: str
    temp_directory: str
    download_retention_days: int | None = Field(
        ...,
        description="Configured media retention age; scheduling is owned by Celery beat",
    )
    max_login_attempts: int
    login_attempt_window_minutes: int
    rate_limiting_enabled: bool
    debug_mode: bool


class ConfigurationUpdate(CamelCaseModel):
    """Unsupported update request; valid requests are rejected with HTTP 501."""

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
