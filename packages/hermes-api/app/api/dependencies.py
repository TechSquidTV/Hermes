"""
FastAPI dependencies for authentication and authorization.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import verify_token
from app.db.repositories import TokenBlacklistRepository, UserRepository
from app.db.session import get_database_session

logger = get_logger(__name__)
security = HTTPBearer()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_session: AsyncSession = Depends(get_database_session),
) -> dict:
    """Extract and validate JWT token, return current user."""
    try:
        logger.info("====== get_current_user_from_token called ======")
        scheme = credentials.scheme if credentials else None
        token_length = len(credentials.credentials) if credentials else 0
        logger.info(
            f"Credentials received: scheme={scheme}, token_length={token_length}"
        )

        # Verify JWT token
        payload = verify_token(credentials.credentials)
        logger.info(
            f"Token verification result: {payload is not None}",
            payload_keys=list(payload.keys()) if payload else None,
        )

        if not payload:
            logger.warning("Token verification returned None")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        token_id: str = payload.get("jti")  # JWT ID for blacklist checking
        token_info = f"username={username}, user_id={user_id}, jti={token_id}"
        logger.info(f"Extracted from token: {token_info}")

        if not username or not user_id:
            logger.warning("Missing username or user_id in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Check if token is blacklisted
        token_blacklist_repo = TokenBlacklistRepository(db_session)
        if token_id:
            is_blacklisted = await token_blacklist_repo.is_blacklisted(token_id)
            if is_blacklisted:
                logger.warning(f"Token is blacklisted: {token_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )

        # Verify user still exists and is active
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_id(user_id)
        logger.info(f"User lookup result: found={user is not None}")

        if not user:
            logger.warning(f"User not found for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not user.is_active:
            logger.warning(f"User account disabled: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
            )

        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc) > datetime.fromtimestamp(
            exp, timezone.utc
        ):
            logger.warning(f"Token expired: exp={exp}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )

        logger.info(f"Successfully authenticated user: {username}")
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "preferences": user.preferences,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "token_id": token_id,  # Include token ID for logout
        }

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
