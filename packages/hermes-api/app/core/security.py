"""
Security utilities for API authentication and authorization.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.repositories import (
    ApiKeyRepository,
    TokenBlacklistRepository,
    UserRepository,
)
from app.db.session import get_database_session

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()

# Optional HTTP Bearer for SSE endpoints (doesn't raise error if missing)
optional_security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthPrincipal:
    """Authenticated caller resolved from a JWT, configured API key, or DB API key."""

    kind: Literal["user", "api_key"]
    subject: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    is_admin: bool = False
    preferences: Optional[dict] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    token_id: Optional[str] = None
    api_key_id: Optional[str] = None
    api_key_name: Optional[str] = None
    permissions: list[str] = field(default_factory=list)

    @property
    def legacy_identifier(self) -> str:
        """Stable string for routes that only need to know auth succeeded."""
        if self.kind == "user" and self.user_id:
            return f"user:{self.user_id}"
        if self.api_key_id:
            return f"db_api_key:{self.api_key_id}"
        return self.subject

    def as_user_dict(self) -> dict:
        """Return the historical user dict shape used by auth/admin endpoints."""
        if self.kind != "user" or not self.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "id": self.user_id,
            "username": self.username,
            "email": self.email,
            "avatar": self.avatar,
            "is_admin": self.is_admin,
            "preferences": self.preferences,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "token_id": self.token_id,
        }


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


async def _principal_from_jwt(
    token: str, db_session: AsyncSession
) -> Optional[AuthPrincipal]:
    """Validate a JWT and resolve it to an active user principal."""
    payload = verify_token(token)
    if not payload:
        return None

    username: str = payload.get("sub")
    user_id: str = payload.get("user_id")
    token_id: str = payload.get("jti")

    if not username or not user_id:
        logger.warning("Missing username or user_id in token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_id:
        token_blacklist_repo = TokenBlacklistRepository(db_session)
        if await token_blacklist_repo.is_blacklisted(token_id):
            logger.warning(f"Token is blacklisted: {token_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        logger.warning(f"User not found for user_id: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"User account disabled: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthPrincipal(
        kind="user",
        subject=f"user:{user.id}",
        user_id=user.id,
        username=user.username,
        email=user.email,
        avatar=user.avatar,
        is_admin=user.is_admin,
        preferences=user.preferences,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        token_id=token_id,
    )


async def _principal_from_api_key(
    api_key: str, db_session: AsyncSession
) -> Optional[AuthPrincipal]:
    """Validate configured and database-backed API keys."""
    for configured_key in settings.api_keys:
        if verify_api_key(api_key, hash_api_key(configured_key)):
            return AuthPrincipal(
                kind="api_key",
                subject=f"configured_api_key:{hash_api_key(configured_key)[:12]}",
                permissions=["admin"],
            )

    api_key_repo = ApiKeyRepository(db_session)
    db_api_key = await api_key_repo.get_by_key_hash(hash_api_key(api_key))
    if not db_api_key:
        return None

    if not db_api_key.is_active:
        logger.warning(f"Inactive API key used: {db_api_key.id}")
        return None

    if db_api_key.expires_at and datetime.now(timezone.utc) > db_api_key.expires_at:
        logger.warning(f"Expired API key used: {db_api_key.id}")
        return None

    await api_key_repo.update_last_used(db_api_key.id)

    return AuthPrincipal(
        kind="api_key",
        subject=f"db_api_key:{db_api_key.id}",
        user_id=db_api_key.user_id,
        api_key_id=db_api_key.id,
        api_key_name=db_api_key.name,
        permissions=db_api_key.permissions or [],
    )


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_session: AsyncSession = Depends(get_database_session),
) -> AuthPrincipal:
    """Resolve the current authenticated caller from a bearer JWT or API key."""
    if credentials is None:
        logger.warning("No authorization credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if credentials.scheme.lower() == "bearer":
        jwt_principal = await _principal_from_jwt(token, db_session)
        if jwt_principal:
            return jwt_principal

    api_key_principal = await _principal_from_api_key(token, db_session)
    if api_key_principal:
        return api_key_principal

    logger.warning(
        "Invalid bearer credential provided", key_hash=hash_api_key(token)[:8]
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_principal_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    token: Optional[str] = Query(None),
    db_session: AsyncSession = Depends(get_database_session),
) -> Optional[AuthPrincipal]:
    """Resolve an optional authenticated caller from a header or query token."""
    auth_token = credentials.credentials if credentials else token
    if not auth_token:
        return None

    jwt_principal = await _principal_from_jwt(auth_token, db_session)
    if jwt_principal:
        return jwt_principal

    return await _principal_from_api_key(auth_token, db_session)


async def get_current_api_key_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    token: Optional[str] = Query(None),
    db_session: AsyncSession = Depends(get_database_session),
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
    principal = await get_current_principal_optional(credentials, token, db_session)
    return principal.legacy_identifier if principal else None


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_session: AsyncSession = Depends(get_database_session),
) -> str:
    """Extract and validate API key from Authorization header."""
    principal = await get_current_principal(credentials, db_session)
    return principal.legacy_identifier


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
        logger.warning("Invalid SSE token format", token_prefix=token[:6])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid SSE token format",
        )

    # Basic validation - specific scope validation done by endpoint
    from app.services.redis_progress import redis_progress_service

    token_data = await redis_progress_service.get_sse_token(token)
    if not token_data:
        logger.warning("Invalid or expired SSE token", token_prefix=token[:6])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSE token",
        )

    return token_data
