"""
FastAPI dependencies for authentication and authorization.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_principal
from app.db.session import get_database_session

logger = get_logger(__name__)
security = HTTPBearer()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_session: AsyncSession = Depends(get_database_session),
) -> dict:
    """Extract and validate JWT token, return current user."""
    try:
        principal = await get_current_principal(credentials, db_session)
        return principal.as_user_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Token validation error", error=str(e), error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


# Optional dependency for endpoints that can work with or without auth
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db_session: AsyncSession = Depends(get_database_session),
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        return await get_current_user_from_token(credentials, db_session)
    except HTTPException:
        return None


# Dependency to get token without validation (for logout, etc.)
async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract token from Authorization header."""
    return credentials.credentials


# Admin-only dependency
async def get_current_admin_user(
    current_user: dict = Depends(get_current_user_from_token),
) -> dict:
    """
    Verify that the current user is an admin.

    This dependency should be used for admin-only endpoints.
    Raises 403 Forbidden if the user is not an admin.
    """
    if not current_user.get("is_admin", False):
        logger.warning(
            "Non-admin user attempted to access admin endpoint",
            user_id=current_user.get("id"),
            username=current_user.get("username"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    logger.info(
        "Admin user authenticated",
        user_id=current_user.get("id"),
        username=current_user.get("username"),
    )
    return current_user
