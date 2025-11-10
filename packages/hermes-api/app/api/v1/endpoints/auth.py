"""
Authentication endpoints for user management.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_from_token
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_api_key,
    create_refresh_token,
    get_password_hash,
    hash_api_key,
    verify_password,
    verify_token,
)
from app.db.repositories import (
    ApiKeyRepository,
    TokenBlacklistRepository,
    UserRepository,
)
from app.db.session import get_database_session
from app.models.base import CamelCaseModel

# Rate limiting setup (placeholder for now)
# In production, you would use a proper rate limiting library like slowapi
rate_limit_store = {}


def get_repositories_from_session(db_session: AsyncSession):
    """Create repository instances using the provided database session."""
    return {
        "users": UserRepository(db_session),
        "token_blacklist": TokenBlacklistRepository(db_session),
        "api_keys": ApiKeyRepository(db_session),
    }


def rate_limit(max_attempts: int = 5, window_minutes: int = 15):
    """Simple rate limiting decorator."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get client IP
            request = None
            for arg in args:
                if hasattr(arg, "client") and hasattr(arg.client, "host"):
                    request = arg
                    break

            if request:
                client_ip = request.client.host
                now = datetime.now(timezone.utc)

                # Clean old entries
                for ip in list(rate_limit_store.keys()):
                    if now - rate_limit_store[ip]["first_attempt"] > timedelta(
                        minutes=window_minutes
                    ):
                        del rate_limit_store[ip]

                # Check rate limit
                if client_ip in rate_limit_store:
                    attempts = rate_limit_store[client_ip]
                    if now - attempts["first_attempt"] <= timedelta(
                        minutes=window_minutes
                    ):
                        if attempts["count"] >= max_attempts:
                            raise HTTPException(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="Too many requests. Please try again later.",
                            )
                        attempts["count"] += 1
                    else:
                        attempts["count"] = 1
                        attempts["first_attempt"] = now
                else:
                    rate_limit_store[client_ip] = {"count": 1, "first_attempt": now}

            return await func(*args, **kwargs)

        return wrapper

    return decorator


router = APIRouter()
logger = get_logger(__name__)
security = HTTPBearer()


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(CamelCaseModel):
    """Token response with automatic camelCase conversion."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(CamelCaseModel):
    """User information response model with automatic camelCase conversion."""

    id: str
    username: str
    email: str
    avatar: str | None
    is_active: bool = True
    is_admin: bool = False
    preferences: dict | None = None
    created_at: str
    last_login: str | None = None


class AuthResponse(CamelCaseModel):
    """Authentication response with user and tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/login", response_model=AuthResponse)
@rate_limit(
    max_attempts=settings.max_login_attempts,
    window_minutes=settings.login_attempt_window_minutes,
)
async def login(
    request: Request,
    credentials: UserLogin,
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """Authenticate user and return access token."""
    try:
        repos = get_repositories_from_session(db_session)

        # Get user by username or email
        user = await repos["users"].get_by_username(credentials.username)
        if not user:
            # If not found by username, try by email
            user = await repos["users"].get_by_email(credentials.username)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                )

        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled"
            )

        # Update last login
        await repos["users"].update_last_login(user.id)

        # Create tokens
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                avatar=user.avatar,
                is_active=user.is_active,
                is_admin=user.is_admin,
                preferences=user.preferences,
                created_at=user.created_at.isoformat() if user.created_at else None,
                last_login=user.last_login.isoformat() if user.last_login else None,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/signup", response_model=AuthResponse)
@rate_limit(
    max_attempts=settings.max_login_attempts,
    window_minutes=settings.login_attempt_window_minutes,
)
async def signup(
    request: Request,
    user_data: UserCreate,
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """Create new user account."""
    try:
        repos = get_repositories_from_session(db_session)

        # Check if any users exist
        user_count = await repos["users"].count()
        is_first_user = user_count == 0

        # If users exist and public signup is disabled, reject
        if not is_first_user and not settings.allow_public_signup:
            logger.warning(
                "Signup attempt rejected - public signup disabled",
                username=user_data.username,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public signup is disabled. Contact your administrator to create an account.",
            )

        # Check if username or email already exists
        # Use generic message to prevent user enumeration
        existing_user = await repos["users"].get_by_username(user_data.username)
        existing_email = await repos["users"].get_by_email(user_data.email)

        if existing_user or existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to create account with the provided credentials",
            )

        # Create new user
        # First user automatically becomes admin
        user = await repos["users"].create(
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            is_admin=is_first_user,
        )

        # Log admin creation for security audit
        if is_first_user:
            logger.info(
                "First user created and granted admin privileges",
                username=user.username,
                user_id=user.id,
                security_event="first_user_admin_created",
            )

        # Create tokens
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                avatar=user.avatar,
                is_active=user.is_active,
                is_admin=user.is_admin,
                preferences=user.preferences,
                created_at=user.created_at.isoformat() if user.created_at else None,
                last_login=user.last_login.isoformat() if user.last_login else None,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Signup error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, str]:
    """Logout user and blacklist current token."""
    try:
        # Extract token ID from current user (includes jti from dependency)
        token_id = current_user.get("token_id")
        user_id = current_user.get("id")

        if token_id and user_id:
            # Get token expiration from JWT
            # We'll set the blacklist expiration to match the token's natural expiration
            # Access tokens expire in 15 minutes by default
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=settings.access_token_expire_minutes
            )

            # Add token to blacklist
            repos = get_repositories_from_session(db_session)
            await repos["token_blacklist"].add_to_blacklist(
                token_id=token_id,
                user_id=user_id,
                expires_at=expires_at,
                reason="user_logout",
            )
            token_prefix = token_id[:8] if token_id else "unknown"
            log_message = (
                f"Token {token_prefix}... blacklisted for user "
                f"{current_user['username']}"
            )
            logger.info(log_message)
        else:
            username = current_user.get("username", "unknown")
            logger.warning(
                f"Token ID not found in token payload during logout for user {username}"
            )

        logger.info(f"User {current_user['username']} logged out successfully")
        return {"message": "Successfully logged out"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Logout error", error=str(e))
        # Still return success for client-side logout
        return {"message": "Logout completed"}


@router.post("/refresh")
async def refresh_token(
    refresh_data: dict, db_session: AsyncSession = Depends(get_database_session)
) -> TokenResponse:
    """Refresh access token using refresh token."""
    try:
        refresh_token = refresh_data.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required",
            )

        # Verify refresh token
        payload = verify_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        username = payload.get("sub")
        user_id = payload.get("user_id")

        if not username or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Get user to verify they still exist and are active
        repos = get_repositories_from_session(db_session)
        user = await repos["users"].get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Create new tokens
        access_token = create_access_token(
            data={"sub": username, "user_id": user_id},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )
        refresh_token = create_refresh_token(
            data={"sub": username, "user_id": user_id},
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )

        return TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: dict = Depends(get_current_user_from_token),
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse(**current_user)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    updates: dict,
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    """Update user profile (name, email, avatar, preferences)."""
    try:
        repos = get_repositories_from_session(db_session)
        user = await repos["users"].get_by_id(current_user["id"])

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Validate and filter allowed fields
        allowed_fields = {"email", "avatar", "preferences"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update",
            )

        # If email is being updated, check it's not already taken
        if "email" in filtered_updates and filtered_updates["email"]:
            existing_user = await repos["users"].get_by_email(filtered_updates["email"])
            if existing_user and existing_user.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
                )

        # Update user fields
        for field, value in filtered_updates.items():
            setattr(user, field, value)

        await repos["users"].update(user)

        logger.info(
            f"Profile updated for user {current_user['username']}",
            fields=list(filtered_updates.keys()),
        )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            is_active=user.is_active,
            is_admin=user.is_admin,
            preferences=user.preferences,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Profile update error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


class PasswordChange(CamelCaseModel):
    """Password change request with automatic camelCase conversion."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class ApiKeyCreate(CamelCaseModel):
    """API key creation request with automatic camelCase conversion."""

    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    permissions: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class ApiKeyResponse(CamelCaseModel):
    """API key response with automatic camelCase conversion."""

    id: str
    name: str
    key: str  # Only returned on creation, not on list
    permissions: list[str]
    rate_limit: int
    is_active: bool
    created_at: str
    last_used: str | None
    expires_at: str | None


class ApiKeyListResponse(CamelCaseModel):
    """API key list response with automatic camelCase conversion."""

    id: str
    name: str
    permissions: list[str]
    rate_limit: int
    is_active: bool
    created_at: str
    last_used: str | None
    expires_at: str | None


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, str]:
    """Change user password. Requires current password for verification."""
    try:
        repos = get_repositories_from_session(db_session)
        user = await repos["users"].get_by_id(current_user["id"])

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Verify current password
        if not verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        # Validate new password is different from current
        if verify_password(password_data.new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        # Hash and update new password
        user.password_hash = get_password_hash(password_data.new_password)
        await repos["users"].update(user)

        logger.info(
            f"Password changed successfully for user {current_user['username']}"
        )

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key_endpoint(
    api_key_data: ApiKeyCreate,
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """Create a new API key for the authenticated user."""
    try:
        # Generate the actual API key
        plain_api_key = (
            create_api_key()
        )  # Call the imported function from security module

        # Hash it for storage
        key_hash = hash_api_key(plain_api_key)

        # Create API key in database
        repos = get_repositories_from_session(db_session)
        api_key = await repos["api_keys"].create(
            user_id=current_user["id"],
            name=api_key_data.name,
            key_hash=key_hash,
            permissions=api_key_data.permissions,
            rate_limit=60,  # Default rate limit
        )

        logger.info(
            f"API key created for user {current_user['username']}: {api_key.name}"
        )

        return ApiKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key=plain_api_key,  # Return plain key only on creation
            permissions=api_key.permissions,
            rate_limit=api_key.rate_limit,
            is_active=api_key.is_active,
            created_at=api_key.created_at.isoformat(),
            last_used=api_key.last_used.isoformat() if api_key.last_used else None,
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("API key creation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/api-keys", response_model=list[ApiKeyListResponse])
async def list_api_keys(
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> list[Dict[str, Any]]:
    """List all API keys for the authenticated user."""
    try:
        repos = get_repositories_from_session(db_session)

        # Get all API keys for the user
        api_keys = await repos["api_keys"].get_by_user_id(current_user["id"])
        result = []
        for api_key in api_keys:
            result.append(
                ApiKeyListResponse(
                    id=api_key.id,
                    name=api_key.name,
                    permissions=api_key.permissions,
                    rate_limit=api_key.rate_limit,
                    is_active=api_key.is_active,
                    created_at=api_key.created_at.isoformat(),
                    last_used=(
                        api_key.last_used.isoformat() if api_key.last_used else None
                    ),
                    expires_at=(
                        api_key.expires_at.isoformat() if api_key.expires_at else None
                    ),
                )
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("API key listing error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/api-keys/{api_key_id}")
async def revoke_api_key(
    api_key_id: str,
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, str]:
    """Revoke (deactivate) an API key."""
    try:
        repos = get_repositories_from_session(db_session)

        # Get the API key
        api_key = await repos["api_keys"].get_by_id(api_key_id)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Verify the API key belongs to the current user
        if api_key.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to revoke this API key",
            )

        # Deactivate the API key
        api_key.is_active = False
        await repos["api_keys"].update(api_key)

        logger.info(f"API key {api_key_id} revoked for user {current_user['username']}")

        return {"message": "API key revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("API key revocation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
