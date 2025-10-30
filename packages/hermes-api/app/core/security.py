"""
Security utilities for API authentication and authorization.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.repositories import ApiKeyRepository

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()

# Optional HTTP Bearer for SSE endpoints (doesn't raise error if missing)
optional_security = HTTPBearer(auto_error=False)


def create_api_key() -> str:
    """Generate a new API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify a plain API key against its hash."""
    return hash_api_key(plain_key) == hashed_key


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    # Add JWT ID for token tracking and blacklisting
    import uuid

    jti = str(uuid.uuid4())

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": jti,  # JWT ID for token blacklisting
            "type": "access",
            "iss": "hermes-api",  # Issuer
            "aud": "hermes-app",  # Audience
        }
    )
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )

    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT refresh token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

    # Add JWT ID for token tracking and blacklisting
    import uuid

    jti = str(uuid.uuid4())

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": jti,  # JWT ID for token blacklisting
            "type": "refresh",
            "iss": "hermes-api",  # Issuer
            "aud": "hermes-app",  # Audience
        }
    )
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience=["hermes-app", "hermes-api"],  # Accept tokens for app or API
            issuer="hermes-api",
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.warning("JWT expired", error=str(e))
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token", error=str(e))
        return None
    except jwt.PyJWTError as e:
        logger.warning("JWT verification failed", error=str(e))
        return None


async def validate_database_api_key(
    api_key: str, db_session: AsyncSession
) -> Optional[str]:
    """Validate a database API key and return the API key if valid."""
    try:
        api_key_repo = ApiKeyRepository(db_session)
        db_api_key = await api_key_repo.get_by_key_hash(hash_api_key(api_key))

        if db_api_key:
            # Check if API key is active
            if not db_api_key.is_active:
                logger.warning(f"Inactive API key used: {db_api_key.id}")
                return None

            # Check if API key has expired
            if (
                db_api_key.expires_at
                and datetime.now(timezone.utc) > db_api_key.expires_at
            ):
                logger.warning(f"Expired API key used: {db_api_key.id}")
                return None

            # Update last used timestamp
            await api_key_repo.update_last_used(db_api_key.id)

            logger.info(
                f"Valid database API key used: {db_api_key.id} for user {db_api_key.user_id}"
            )
            return api_key

    except Exception as e:
        logger.warning(f"Database API key validation error: {str(e)}")

    return None


async def get_current_api_key_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    token: Optional[str] = Query(None),
) -> Optional[str]:
    """
    Extract and validate API key from Authorization header or query param.

    For SSE endpoints where EventSource cannot send custom headers,
    accepts token as query parameter as fallback.

    Args:
        credentials: HTTP Bearer token from Authorization header
        token: Optional token from query parameter (for SSE)

    Returns:
        Validated API key/user marker or None if no auth provided
    """
    # Try Authorization header first
    auth_token = None
    if credentials:
        auth_token = credentials.credentials
    # Fall back to query param (for EventSource SSE connections)
    elif token:
        auth_token = token
    else:
        return None

    # Validate token (JWT or API key)
    payload = verify_token(auth_token)
    if payload:
        user_id = payload.get("user_id")
        if user_id:
            logger.info(f"Accepting user token for user_id: {user_id}")
            return f"user:{user_id}"

        api_key = payload.get("api_key")
        if api_key:
            return api_key

    # Check configured API keys
    for configured_key in settings.api_keys:
        if verify_api_key(auth_token, hash_api_key(configured_key)):
            return configured_key

    # Check database API keys
    if len(auth_token) >= 32:
        logger.info(f"Database API key provided, length: {len(auth_token)}")
        return f"db_api_key:{auth_token}"

    return None


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract and validate API key from Authorization header."""
    if credentials is None:
        logger.warning("No authorization credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if it's a Bearer token (JWT)
    if credentials.scheme.lower() == "bearer":
        payload = verify_token(credentials.credentials)
        logger.info(
            f"JWT verification result: {payload is not None}",
            payload_keys=list(payload.keys()) if payload else None,
        )
        if payload:
            # If it's a valid JWT (user token), allow access
            user_id = payload.get("user_id")
            logger.info(f"User ID from payload: {user_id}")
            if user_id:
                # Valid user token, return a special marker
                logger.info(f"Accepting user token for user_id: {user_id}")
                return f"user:{user_id}"

            # Check for API key in JWT
            api_key = payload.get("api_key")
            if api_key:
                return api_key

    # Otherwise treat as API key directly
    api_key = credentials.credentials

    # First, validate against configured API keys (legacy support)
    for configured_key in settings.api_keys:
        if verify_api_key(api_key, hash_api_key(configured_key)):
            return configured_key

    # Then validate against database-stored API keys
    # Note: Database validation will be handled by the endpoint dependencies
    # since get_current_api_key cannot access the database session directly
    try:
        # Basic format validation
        if len(api_key) >= 32:  # Basic validation that it looks like an API key
            logger.info(f"Database API key provided, length: {len(api_key)}")
            # Return a special marker that endpoints will validate against the database
            return f"db_api_key:{api_key}"
    except Exception as e:
        logger.warning(f"API key validation error: {str(e)}")

    logger.warning("Invalid API key provided", key_hash=hash_api_key(api_key)[:8])
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        # Convert string to bytes if needed
        if isinstance(plain_password, str):
            plain_password = plain_password.encode("utf-8")
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")

        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        logger.error("Password verification failed", error=str(e))
        return False


def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    try:
        # Convert string to bytes and hash
        if isinstance(password, str):
            password = password.encode("utf-8")

        # Generate salt and hash
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password, salt)

        # Return as string
        return hashed.decode("utf-8")
    except Exception as e:
        logger.error("Password hashing failed", error=str(e))
        raise


class PermissionChecker:
    """Helper class for permission checking."""

    @staticmethod
    def has_permission(
        api_key_permissions: List[str], required_permission: str
    ) -> bool:
        """Check if API key has required permission."""
        return (
            required_permission in api_key_permissions or "admin" in api_key_permissions
        )

    @staticmethod
    def require_permission(api_key_permissions: List[str], required_permission: str):
        """Raise exception if permission is not granted."""
        if not PermissionChecker.has_permission(
            api_key_permissions, required_permission
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission} required",
            )


# =============================================================================
# SSE TOKEN VALIDATION
# =============================================================================


async def validate_sse_token(token: str, required_scope: str) -> dict:
    """
    Validate ephemeral SSE token.

    This validates short-lived, scoped tokens used for SSE connections.
    Tokens are stored in Redis and automatically expire via TTL.

    Args:
        token: SSE token string (format: sse_<base64>)
        required_scope: Required scope (e.g., 'download:abc-123', 'download:*', 'queue')

    Returns:
        Token data dictionary with scope, user_id, permissions

    Raises:
        HTTPException: If token is invalid, expired, or has insufficient scope
    """
    from app.services.redis_progress import redis_progress_service

    # Get token from Redis
    token_data = await redis_progress_service.get_sse_token(token)
    if not token_data:
        logger.warning("Invalid or expired SSE token", token_prefix=token[:12])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSE token",
        )

    # Check expiry (Redis TTL should handle this, but double-check)
    expires_at_str = token_data.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now(timezone.utc) > expires_at:
                logger.warning("Expired SSE token", token_prefix=token[:12])
                await redis_progress_service.delete_sse_token(token)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="SSE token expired",
                )
        except (ValueError, TypeError) as e:
            logger.error("Invalid expires_at format", error=str(e))

    # Check scope
    token_scope = token_data.get("scope", "")
    if not _scope_matches(token_scope, required_scope):
        logger.warning(
            "Insufficient SSE token scope",
            token_scope=token_scope,
            required_scope=required_scope,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient scope: {required_scope} required",
        )

    logger.info(
        "Valid SSE token",
        token_prefix=token[:12],
        scope=token_scope,
        user_id=token_data.get("user_id"),
    )
    return token_data


def _scope_matches(token_scope: str, required_scope: str) -> bool:
    """
    Check if token scope matches required scope.

    Args:
        token_scope: Token's actual scope (e.g., 'download:abc-123')
        required_scope: Required scope (e.g., 'download:abc-123', 'download:*')

    Returns:
        True if scope matches

    Examples:
        >>> _scope_matches('download:abc-123', 'download:abc-123')
        True
        >>> _scope_matches('download:abc-123', 'download:*')
        True
        >>> _scope_matches('download:abc-123', 'queue')
        False
    """
    # Exact match
    if token_scope == required_scope:
        return True

    # Wildcard match (e.g., download:* matches any download:xxx)
    if required_scope.endswith(":*"):
        scope_prefix = required_scope[:-2]  # Remove :*
        return token_scope.startswith(scope_prefix + ":")

    return False


async def get_current_sse_token(
    token: Optional[str] = Query(None, description="SSE token from query parameter"),
) -> dict:
    """
    Dependency to extract and validate SSE token from query parameter.

    For SSE endpoints that require scoped token authentication.
    The scope validation is handled by the endpoint itself.

    Args:
        token: SSE token from query parameter

    Returns:
        Token data dictionary

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not token:
        logger.warning("SSE connection attempted without token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SSE token required",
        )

    # Check if it's an SSE token (starts with "sse_")
    if not token.startswith("sse_"):
        logger.warning("Invalid SSE token format", token_prefix=token[:12])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid SSE token format",
        )

    # Basic validation - specific scope validation done by endpoint
    from app.services.redis_progress import redis_progress_service

    token_data = await redis_progress_service.get_sse_token(token)
    if not token_data:
        logger.warning("Invalid or expired SSE token", token_prefix=token[:12])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSE token",
        )

    return token_data
