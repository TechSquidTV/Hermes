"""
Configuration management endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories import UserRepository
from app.db.session import get_database_session
from app.models.base import CamelCaseModel
from app.services.system_settings_service import system_settings_service

router = APIRouter(prefix="/config", tags=["configuration"])
logger = get_logger(__name__)


class PublicConfig(CamelCaseModel):
    """Public configuration with automatic camelCase conversion."""

    allow_public_signup: bool


@router.get("/public", response_model=PublicConfig)
async def get_public_configuration(
    db_session: AsyncSession = Depends(get_database_session),
):
    """
    Get public configuration settings.

    This endpoint is accessible without authentication and returns
    configuration that the frontend needs to display correctly,
    such as whether public signup is allowed.
    """
    allow_public_signup = await system_settings_service.get_allow_public_signup()
    try:
        user_count = await UserRepository(db_session).count()
    except Exception as e:
        logger.warning(
            "Unable to check user count for public config; using signup setting",
            error=str(e),
        )
        user_count = 1

    return PublicConfig(
        allow_public_signup=allow_public_signup or user_count == 0,
    )
