"""
Authentication endpoints for user management.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field, JsonValue, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user_from_token,
    get_repositories_from_session,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limit import limit_auth_requests
from app.core.security import (
    ApiKeyPermission,
    create_api_key,
    create_token_pair,
    get_password_hash,
    hash_api_key,
    verify_password,
    verify_token,
)
from app.db.registration import lock_user_registration
from app.db.session import get_database_session
from app.models.base import CamelCaseModel
from app.models.pydantic.password import Password
from app.services.system_settings_service import system_settings_service
from app.utils.dates import as_utc

router = APIRouter()
logger = get_logger(__name__)
security = HTTPBearer()


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: Password


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(CamelCaseModel):
    """Token response with automatic camelCase conversion."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(CamelCaseModel):
    """Refresh-token request accepting camelCase and snake_case input."""

    refresh_token: str


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


@router.post(
    "/login", response_model=AuthResponse, dependencies=[Depends(limit_auth_requests)]
)
async def login(
    request: Request,
    credentials: UserLogin,
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """Authenticate user and return access token."""
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
    access_token, refresh_token = create_token_pair(
        {"sub": str(user.username), "user_id": str(user.id)}
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


@router.post(
    "/signup", response_model=AuthResponse, dependencies=[Depends(limit_auth_requests)]
)
async def signup(
    request: Request,
    user_data: UserCreate,
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """Create new user account."""
    repos = get_repositories_from_session(db_session)

    await lock_user_registration(db_session)

    # Check if any users exist
    user_count = await repos["users"].count()
    is_first_user = user_count == 0

    # If users exist and public signup is disabled, reject
    allow_public_signup = await system_settings_service.get_allow_public_signup()
    if not is_first_user and not allow_public_signup:
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
    access_token, refresh_token = create_token_pair(
        {"sub": str(user.username), "user_id": str(user.id)}
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


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, str]:
    """Revoke the entire token family, including already-rotated refresh tokens."""
    repos = get_repositories_from_session(db_session)
    session_id = current_user["session_id"]
    if not await repos["token_blacklist"].is_blacklisted(session_id):
        await repos["token_blacklist"].add_to_blacklist(
            token_id=session_id,
            user_id=current_user["id"],
            # Keep the revocation until every token in the family has expired.
            expires_at=datetime.now(timezone.utc)
            + timedelta(
                days=settings.refresh_token_expire_days,
                minutes=settings.access_token_expire_minutes,
            ),
            reason="user_logout",
        )
    return {"message": "Successfully logged out"}


@router.post("/refresh", dependencies=[Depends(limit_auth_requests)])
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db_session: AsyncSession = Depends(get_database_session),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    refresh_token = refresh_data.refresh_token
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    # Verify refresh token
    payload = verify_token(refresh_token)
    if (
        not payload
        or payload.get("type") != "refresh"
        or not payload.get("sid")
        or not payload.get("jti")
    ):
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
    if await repos["token_blacklist"].is_blacklisted(payload["jti"]) or await repos[
        "token_blacklist"
    ].is_blacklisted(payload["sid"]):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    user = await repos["users"].get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Consume the refresh token before minting its successor. The unique jti
    # constraint makes parallel replays fail as well.
    from sqlalchemy.exc import IntegrityError

    try:
        await repos["token_blacklist"].add_to_blacklist(
            token_id=payload["jti"],
            user_id=user_id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            reason="refresh_rotation",
        )
    except IntegrityError as error:
        await db_session.rollback()
        raise HTTPException(
            status_code=401, detail="Refresh token has been revoked"
        ) from error

    access_token, refresh_token = create_token_pair(
        {"sub": username, "user_id": user_id, "sid": payload["sid"]}
    )

    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: dict = Depends(get_current_user_from_token),
) -> UserResponse:
    """Get current authenticated user information."""
    user_response = UserResponse(**current_user)
    return user_response


class ProfileUpdate(CamelCaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    avatar: str | None = Field(default=None, max_length=65536)
    preferences: dict[str, JsonValue] | None = None

    @field_validator("email")
    @classmethod
    def non_null_email(cls, value: EmailStr | None) -> EmailStr:
        if value is None:
            raise ValueError("Email cannot be null")
        return value

    @field_validator("preferences")
    @classmethod
    def bounded_preferences(
        cls, value: dict[str, JsonValue] | None
    ) -> dict[str, JsonValue] | None:
        if value is not None and len(json.dumps(value).encode()) > 16384:
            raise ValueError("Preferences must not exceed 16 KiB")
        return value


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    updates: ProfileUpdate,
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    """Update user profile (name, email, avatar, preferences)."""
    repos = get_repositories_from_session(db_session)
    user = await repos["users"].get_by_id(current_user["id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Validate and filter allowed fields
    filtered_updates = updates.model_dump(exclude_unset=True)

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


class PasswordChange(CamelCaseModel):
    """Password change request with automatic camelCase conversion."""

    current_password: str
    new_password: Password


class ApiKeyCreate(CamelCaseModel):
    """API key creation request with automatic camelCase conversion."""

    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    permissions: list[ApiKeyPermission] = Field(default_factory=list)
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

    logger.info(f"Password changed successfully for user {current_user['username']}")

    return {"message": "Password changed successfully"}


@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key_endpoint(
    api_key_data: ApiKeyCreate,
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """Create a new API key for the authenticated user."""
    # Generate the actual API key
    plain_api_key = create_api_key()  # Call the imported function from security module

    # Hash it for storage
    key_hash = hash_api_key(plain_api_key)

    # Create API key in database
    repos = get_repositories_from_session(db_session)
    api_key = await repos["api_keys"].create(
        user_id=current_user["id"],
        name=api_key_data.name,
        key_hash=key_hash,
        permissions=[permission.value for permission in api_key_data.permissions],
        rate_limit=60,  # Default rate limit
        expires_at=api_key_data.expires_at,
    )

    logger.info(f"API key created for user {current_user['username']}: {api_key.name}")

    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_api_key,  # Return plain key only on creation
        permissions=api_key.permissions,
        rate_limit=api_key.rate_limit,
        is_active=api_key.is_active,
        created_at=api_key.created_at.isoformat(),
        last_used=api_key.last_used.isoformat() if api_key.last_used else None,
        expires_at=(
            as_utc(api_key.expires_at).isoformat() if api_key.expires_at else None
        ),
    )


@router.get("/api-keys", response_model=list[ApiKeyListResponse])
async def list_api_keys(
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> list[Dict[str, Any]]:
    """List all API keys for the authenticated user."""
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
                    as_utc(api_key.expires_at).isoformat()
                    if api_key.expires_at
                    else None
                ),
            )
        )

    return result


@router.delete("/api-keys/{api_key_id}")
async def revoke_api_key(
    api_key_id: str,
    current_user: dict = Depends(get_current_user_from_token),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, str]:
    """Revoke (deactivate) an API key."""
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
