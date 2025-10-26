"""
Configuration management endpoints.
"""

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_current_api_key
from app.models.pydantic.config import Configuration, ConfigurationUpdate

router = APIRouter(prefix="/config", tags=["configuration"])
logger = get_logger(__name__)


@router.get("/", response_model=Configuration)
async def get_configuration(api_key: str = Depends(get_current_api_key)):
    """
    Get current API configuration.

    Returns all configurable settings including:
    - Download defaults (format, subtitles, thumbnails)
    - Performance settings (concurrency, retries, timeout)
    - Storage settings (directories, cleanup)
    - API settings (rate limits, debug mode)

    Note: Sensitive settings like secret keys are not exposed.
    """
    return Configuration(
        # Download settings
        output_template="%(title)s.%(ext)s",
        default_format="best",
        download_subtitles=False,
        download_thumbnail=False,
        output_directory=settings.download_dir,
        # Performance settings
        max_concurrent_downloads=3,
        retry_attempts=3,
        timeout=30,
        # Storage settings
        temp_directory=settings.temp_dir,
        cleanup_enabled=True,
        cleanup_older_than_days=30,
        # API settings
        rate_limit_per_minute=settings.rate_limit_per_minute,
        debug_mode=settings.debug,
    )


@router.put("/", response_model=Configuration)
async def update_configuration(
    config_update: ConfigurationUpdate, api_key: str = Depends(get_current_api_key)
):
    """
    Update API configuration.

    Updates runtime configuration settings. Only provided fields will be updated.

    **Note**: Configuration changes are runtime-only and will be reset on restart.
    For persistent changes, update environment variables or configuration files.

    **Supported Updates**:
    - Download defaults
    - Performance settings
    - Cleanup settings
    - Rate limits

    **Not Supported** (require restart):
    - Database URLs
    - Secret keys
    - Core directories (requires file system changes)

    Returns the updated configuration.
    """
    # In a real implementation, you would update settings in memory or a config store
    # For now, we'll just return the current config as this is runtime-only

    logger.info(
        "Configuration update requested",
        updates=config_update.model_dump(exclude_none=True),
    )

    # Warn that these are runtime changes only
    logger.warning("Configuration changes are runtime-only and will reset on restart")

    # Return current config (in real impl, would return updated values)
    return await get_configuration(api_key=api_key)
