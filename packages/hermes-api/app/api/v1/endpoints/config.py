"""
Configuration management endpoints.
"""

from fastapi import APIRouter

from app.core.logging import get_logger
from app.models.base import CamelCaseModel
from app.services.system_settings_service import system_settings_service

router = APIRouter(prefix="/config", tags=["configuration"])
logger = get_logger(__name__)


class PublicConfig(CamelCaseModel):
    """Public configuration with automatic camelCase conversion."""

    allow_public_signup: bool


@router.get("/public", response_model=PublicConfig)
async def get_public_configuration():
    """
    Get public configuration settings.

    This endpoint is accessible without authentication and returns
    configuration that the frontend needs to display correctly,
    such as whether public signup is allowed.
    """
    allow_public_signup = await system_settings_service.get_allow_public_signup()
    return PublicConfig(allow_public_signup=allow_public_signup)
