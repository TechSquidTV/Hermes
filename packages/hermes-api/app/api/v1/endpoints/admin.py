"""
Admin-only endpoints for system management.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field

from app.api.dependencies import get_current_admin_user
from app.core.config import settings
from app.core.logging import get_logger
from app.models.auth import AuthenticatedUser
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
    current_user: AuthenticatedUser = Depends(get_current_admin_user),
) -> SystemSettingsResponse:
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
    current_user: AuthenticatedUser = Depends(get_current_admin_user),
) -> SystemSettingsResponse:
    """
    Update the public signup setting.

    Allows admins to enable or disable public user registration.

    **Note**: The first user signup is always allowed regardless of this setting
    to ensure system bootstrap capability.

    **Requires**: Admin authentication
    """
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


# ============================================================================
# System Configuration Endpoints (moved from /config)
# ============================================================================


@router.get("/config", response_model=Configuration)
async def get_admin_configuration(
    current_user: AuthenticatedUser = Depends(get_current_admin_user),
) -> Configuration:
    """Read this API process's startup settings.

    Does not report worker concurrency, download defaults, or scheduler state.
    Environment changes require restarting the affected API, Celery workers and
    beat processes. Sensitive settings are excluded. Requires admin login.
    """
    return Configuration(
        output_directory=settings.download_dir,
        temp_directory=settings.temp_dir,
        download_retention_days=settings.download_retention_days,
        max_login_attempts=settings.max_login_attempts,
        login_attempt_window_minutes=settings.login_attempt_window_minutes,
        rate_limiting_enabled=settings.enable_rate_limiting,
        debug_mode=settings.debug,
    )


@router.put("/config", status_code=501, response_model=None)
async def update_admin_configuration(
    config_update: ConfigurationUpdate,
    current_user: AuthenticatedUser = Depends(get_current_admin_user),
) -> None:
    """Reject unsupported runtime configuration updates.

    No fields are applied, including empty requests. Change supported deployment
    environment settings and restart all affected API, Celery worker and beat
    processes. There is no runtime propagation between these processes.
    Download options belong on individual download requests; worker concurrency
    belongs in the worker launch configuration. Requires admin login.
    """
    raise HTTPException(
        status_code=501,
        detail="Runtime configuration updates are not supported. Update deployment settings and restart affected API, Celery worker and beat processes.",
    )
