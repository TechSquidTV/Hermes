"""
User management endpoints (admin only).
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin_user
from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.db.repositories import UserRepository
from app.db.session import get_database_session
from app.models.base import CamelCaseModel

router = APIRouter(prefix="/users", tags=["users"])
logger = get_logger(__name__)


class UserListResponse(CamelCaseModel):
    """User information for list view with automatic camelCase conversion."""

    id: str
    username: str
    email: str
    avatar: str | None
    is_active: bool
    is_admin: bool
    created_at: str
    last_login: str | None = None


class UserCreateAdmin(CamelCaseModel):
    """Admin user creation model with automatic camelCase conversion."""

    username: str
    email: EmailStr
    password: str
    is_admin: bool = False


class UserUpdateAdmin(CamelCaseModel):
    """Admin user update model with automatic camelCase conversion."""

    is_admin: bool


class UserUpdateActive(CamelCaseModel):
    """User active status update model with automatic camelCase conversion."""

    is_active: bool


@router.get("/", response_model=List[UserListResponse])
async def list_users(
    current_admin: dict = Depends(get_current_admin_user),
    db_session: AsyncSession = Depends(get_database_session),
) -> List[Dict[str, Any]]:
    """
    List all users (admin only).

    Returns a list of all users in the system with their basic information.
    Only accessible by administrators.
    """
    try:
        # Get all users
        from sqlalchemy import select

        from app.db.models import User

        result = await db_session.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()

        return [
            UserListResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                avatar=user.avatar,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at.isoformat() if user.created_at else None,
                last_login=user.last_login.isoformat() if user.last_login else None,
            )
            for user in users
        ]

    except Exception as e:
        logger.error("Error listing users", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.post("/", response_model=UserListResponse)
async def create_user_as_admin(
    user_data: UserCreateAdmin,
    current_admin: dict = Depends(get_current_admin_user),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    Create a new user as admin (admin only).

    This endpoint allows administrators to create user accounts
    even when public signup is disabled.
    """
    try:
        user_repo = UserRepository(db_session)

        # Check if username already exists
        existing_user = await user_repo.get_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )

        # Check if email already exists
        existing_email = await user_repo.get_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        # Create new user
        user = await user_repo.create(
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            is_admin=user_data.is_admin,
        )

        logger.info(
            "User created by admin",
            admin_user_id=current_admin.get("id"),
            admin_username=current_admin.get("username"),
            new_user_id=user.id,
            new_username=user.username,
            new_user_is_admin=user.is_admin,
            security_event="admin_user_created",
        )

        return UserListResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating user as admin", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@router.patch("/{user_id}/admin", response_model=UserListResponse)
async def update_user_admin_status(
    user_id: str,
    update_data: UserUpdateAdmin,
    current_admin: dict = Depends(get_current_admin_user),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    Promote or demote user admin status (admin only).

    Allows administrators to grant or revoke admin privileges.

    **Security Check**: Cannot demote yourself if you're the last admin.
    """
    try:
        user_repo = UserRepository(db_session)

        # Get target user
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # If demoting an admin, check if they're the last admin
        if user.is_admin and not update_data.is_admin:
            # Count current admins
            from sqlalchemy import func, select

            from app.db.models import User

            result = await db_session.execute(
                select(func.count(User.id)).where(User.is_admin)
            )
            admin_count = result.scalar_one()

            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the last admin. Promote another user to admin first.",
                )

        # Update admin status
        user.is_admin = update_data.is_admin
        await user_repo.update(user)

        logger.info(
            "User admin status updated",
            admin_user_id=current_admin.get("id"),
            admin_username=current_admin.get("username"),
            target_user_id=user.id,
            target_username=user.username,
            new_admin_status=user.is_admin,
            security_event="admin_status_changed",
        )

        return UserListResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user admin status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user admin status",
        )


@router.patch("/{user_id}/active", response_model=UserListResponse)
async def update_user_active_status(
    user_id: str,
    update_data: UserUpdateActive,
    current_admin: dict = Depends(get_current_admin_user),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    """
    Activate or deactivate user account (admin only).

    Allows administrators to enable or disable user accounts.
    Deactivated users cannot log in.
    """
    try:
        user_repo = UserRepository(db_session)

        # Get target user
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Prevent deactivating yourself
        if user_id == current_admin.get("id") and not update_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )

        # Update active status
        user.is_active = update_data.is_active
        await user_repo.update(user)

        logger.info(
            "User active status updated",
            admin_user_id=current_admin.get("id"),
            admin_username=current_admin.get("username"),
            target_user_id=user.id,
            target_username=user.username,
            new_active_status=user.is_active,
            security_event="user_active_status_changed",
        )

        return UserListResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user active status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user active status",
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: dict = Depends(get_current_admin_user),
    db_session: AsyncSession = Depends(get_database_session),
) -> Dict[str, str]:
    """
    Delete a user account (admin only).

    Permanently deletes a user account and all associated data.
    Cannot delete your own account.
    """
    try:
        user_repo = UserRepository(db_session)

        # Get target user
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Prevent deleting yourself
        if user_id == current_admin.get("id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account",
            )

        # If deleting an admin, check if they're the last admin
        if user.is_admin:
            from sqlalchemy import func, select

            from app.db.models import User

            result = await db_session.execute(
                select(func.count(User.id)).where(User.is_admin)
            )
            admin_count = result.scalar_one()

            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last admin. Promote another user to admin first.",
                )

        # Delete user
        await db_session.delete(user)
        await db_session.commit()

        logger.info(
            "User deleted",
            admin_user_id=current_admin.get("id"),
            admin_username=current_admin.get("username"),
            deleted_user_id=user.id,
            deleted_username=user.username,
            security_event="user_deleted",
        )

        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting user", error=str(e))
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )
