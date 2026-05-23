"""
Storage information endpoint.
"""

from fastapi import APIRouter, Depends

from app.core.logging import get_logger
from app.core.security import ApiKeyPermission, AuthPrincipal, require_api_permission
from app.models.pydantic.storage import StorageInfo
from app.services.storage_service import StorageService

router = APIRouter(prefix="/storage", tags=["storage"])
logger = get_logger(__name__)


@router.get("/", response_model=StorageInfo)
async def get_storage_info(
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.READ)),
):
    """
    Get storage usage information and cleanup recommendations.

    Returns comprehensive storage information including:
    - Total, used, and free space
    - Usage percentage
    - Download and temp directory sizes
    - Cleanup recommendations with potential space savings

    Use this endpoint to monitor disk usage and identify cleanup opportunities.
    """
    return await StorageService.get_storage_info()
