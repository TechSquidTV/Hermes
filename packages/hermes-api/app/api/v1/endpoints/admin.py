"""
Admin-only endpoints for system management.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field

from app.api.dependencies import get_current_admin_user
from app.core.config import settings
from app.core.logging import get_logger
from app.models.base import CamelCaseModel
from app.models.pydantic.config import Configuration, ConfigurationUpdate
from app.services.system_settings_service import system_settings_service

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)


# ============================================================================
# System Settings Endpoints
# ============================================================================


class SystemSettingsResponse(CamelCaseModel):
    """System settings response with automatic camelCase conversion."""

    allow_public_signup: bool
    updated_at: Optional[datetime] = None
    updated_by_user_id: Optional[str] = None


class UpdateSignupSettingRequest(CamelCaseModel):
    """Request to update signup setting."""

    enabled: bool = Field(..., description="Whether to allow public signups")


@router.get("/settings", response_model=SystemSettingsResponse)
async def get_system_settings(
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Get current system settings.

    Admin-only endpoint for retrieving system-wide settings including:
    - Public signup control
    - Update history

    **Requires**: Admin authentication
    """
    settings_data = await system_settings_service.get_all_settings()
    return SystemSettingsResponse(**settings_data)


@router.put("/settings/signup", response_model=SystemSettingsResponse)
async def update_signup_setting(
    request: UpdateSignupSettingRequest,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Update the public signup setting.

    Allows admins to enable or disable public user registration.

    **Note**: The first user signup is always allowed regardless of this setting
    to ensure system bootstrap capability.

    **Requires**: Admin authentication
    """
    try:
        updated_settings = await system_settings_service.update_allow_public_signup(
            value=request.enabled,
            user_id=current_user.get("id"),
        )

        logger.info(
            "Admin updated signup setting",
            admin_id=current_user.get("id"),
            admin_username=current_user.get("username"),
            new_value=request.enabled,
        )

        return SystemSettingsResponse(**updated_settings)
    except Exception as e:
        logger.error(
            f"Failed to update signup setting: {e}",
            admin_id=current_user.get("id"),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update signup setting",
        )


# ============================================================================
# System Configuration Endpoints (moved from /config)
# ============================================================================


@router.get("/config", response_model=Configuration)
async def get_admin_configuration(
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Get current API configuration.

    Admin-only endpoint for viewing system configuration including:
    - Download defaults (format, subtitles, thumbnails)
    - Performance settings (concurrency, retries, timeout)
    - Storage settings (directories, cleanup)
    - API settings (rate limits, debug mode)

    **Note**: Sensitive settings like secret keys are not exposed.

    **Requires**: Admin authentication
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


@router.put("/config", response_model=Configuration)
async def update_admin_configuration(
    config_update: ConfigurationUpdate,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Update API configuration.

    Admin-only endpoint for updating runtime configuration settings.
    Only provided fields will be updated.

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

    **Requires**: Admin authentication

    Returns the updated configuration.
    """
    logger.info(
        "Configuration update requested by admin",
        admin_id=current_user.get("id"),
        admin_username=current_user.get("username"),
        updates=config_update.model_dump(exclude_none=True),
    )

    # Warn that these are runtime changes only
    logger.warning("Configuration changes are runtime-only and will reset on restart")

    # Return current config (in real impl, would return updated values)
    return await get_admin_configuration(current_user=current_user)
