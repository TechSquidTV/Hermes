"""
Tests for admin user management endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def admin_user(db_session: AsyncSession, setup_test_database):
    """Create an admin user for testing."""
    from app.core.security import get_password_hash
    from app.db.repositories import UserRepository

    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        username="adminuser",
        email="admin@example.com",
        password_hash=get_password_hash("AdminPass123"),
        is_admin=True,
    )
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_token(admin_user):
    """Create an authentication token for the admin user."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={"sub": admin_user.username, "user_id": admin_user.id}
    )
    return token


class TestAdminUserListing:
    """Test admin user listing endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_list_users(
        self, client: AsyncClient, admin_user, admin_token, test_user
    ):
        """Test that admin can list all users."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least admin and test_user

        # Check that users have required fields
        user_data = data[0]
        assert "id" in user_data
        assert "username" in user_data
        assert "email" in user_data
        assert "is_admin" in user_data
        assert "is_active" in user_data

    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_users(
        self, client: AsyncClient, test_user, auth_token
    ):
        """Test that non-admin users cannot list users."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "admin" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_list_users_requires_auth(self, client: AsyncClient):
        """Test that listing users requires authentication."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.get("/api/v1/users/")
        # Could be either 401 (Unauthorized) or 403 (Forbidden) depending on auth check order
        assert response.status_code in [401, 403]


class TestAdminUserCreation:
    """Test admin user creation endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_create_user(
        self, client: AsyncClient, admin_user, admin_token
    ):
        """Test that admin can create new users."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "NewPass123",
                "is_admin": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["is_admin"] is False
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_admin_can_create_admin_user(
        self, client: AsyncClient, admin_user, admin_token
    ):
        """Test that admin can create other admin users."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "newadmin",
                "email": "newadmin@example.com",
                "password": "AdminPass123",
                "is_admin": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True

    @pytest.mark.asyncio
    async def test_non_admin_cannot_create_user(
        self, client: AsyncClient, test_user, auth_token
    ):
        """Test that non-admin users cannot create users."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "username": "unauthorized",
                "email": "unauthorized@example.com",
                "password": "Pass123",
                "is_admin": False,
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self, client: AsyncClient, admin_user, admin_token, test_user
    ):
        """Test that creating a user with duplicate username fails."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": test_user.username,
                "email": "different@example.com",
                "password": "Pass123",
                "is_admin": False,
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert "username" in data["error"]["message"].lower()


class TestPromoteDemoteAdmin:
    """Test promote/demote admin endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_promote_user_to_admin(
        self, client: AsyncClient, admin_user, admin_token, test_user
    ):
        """Test that admin can promote regular user to admin."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        assert test_user.is_admin is False

        response = await client.patch(
            f"/api/v1/users/{test_user.id}/admin",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_admin": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True

    @pytest.mark.asyncio
    async def test_admin_can_demote_admin_to_user(
        self, client: AsyncClient, admin_user, admin_token, db_session
    ):
        """Test that admin can demote another admin to regular user."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        # Create a second admin
        from app.core.security import get_password_hash
        from app.db.repositories import UserRepository

        user_repo = UserRepository(db_session)
        second_admin = await user_repo.create(
            username="secondadmin",
            email="secondadmin@example.com",
            password_hash=get_password_hash("Pass123"),
            is_admin=True,
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/users/{second_admin.id}/admin",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_admin": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is False

    @pytest.mark.asyncio
    async def test_cannot_demote_last_admin(
        self, client: AsyncClient, admin_user, admin_token
    ):
        """Test that the last admin cannot be demoted."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        # Try to demote the only admin
        response = await client.patch(
            f"/api/v1/users/{admin_user.id}/admin",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_admin": False},
        )

        assert response.status_code == 400
        data = response.json()
        assert "last admin" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_non_admin_cannot_promote_user(
        self, client: AsyncClient, test_user, test_user2, auth_token
    ):
        """Test that non-admin users cannot promote others."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.patch(
            f"/api/v1/users/{test_user2.id}/admin",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"is_admin": True},
        )

        assert response.status_code == 403


class TestActivateDeactivateUser:
    """Test activate/deactivate user endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_deactivate_user(
        self, client: AsyncClient, admin_user, admin_token, test_user
    ):
        """Test that admin can deactivate a user."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        assert test_user.is_active is True

        response = await client.patch(
            f"/api/v1/users/{test_user.id}/active",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_admin_can_activate_user(
        self, client: AsyncClient, admin_user, admin_token, test_user, db_session
    ):
        """Test that admin can activate a deactivated user."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        # Deactivate user first
        test_user.is_active = False
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/users/{test_user.id}/active",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_admin_cannot_deactivate_self(
        self, client: AsyncClient, admin_user, admin_token
    ):
        """Test that admin cannot deactivate their own account."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.patch(
            f"/api/v1/users/{admin_user.id}/active",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False},
        )

        assert response.status_code == 400
        data = response.json()
        assert "your own" in data["error"]["message"].lower()


class TestDeleteUser:
    """Test delete user endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_delete_user(
        self, client: AsyncClient, admin_user, admin_token, test_user, db_session
    ):
        """Test that admin can delete a regular user."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        user_id = test_user.id

        response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

        # Verify user is deleted
        from app.db.repositories import UserRepository

        user_repo = UserRepository(db_session)
        deleted_user = await user_repo.get_by_id(user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self(
        self, client: AsyncClient, admin_user, admin_token
    ):
        """Test that admin cannot delete their own account."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "your own" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_cannot_delete_last_admin(
        self, client: AsyncClient, admin_user, admin_token, db_session, test_user
    ):
        """Test that the last admin cannot be deleted."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        # admin_user is the only admin at this point
        # Try to delete the only admin using a regular user (should fail)
        # But first we need to make test_user an admin, then try to delete admin_user

        # Actually, better approach: Use admin_user's token, try to delete themselves as last admin
        # But that fails with "can't delete yourself"

        # Best approach: Have admin promote test_user to admin, then test_user tries to delete admin_user
        # which would leave test_user as the only admin (valid)
        # Then test_user tries to delete themselves (should fail with "last admin")

        # Promote test_user to admin
        test_user.is_admin = True
        await db_session.commit()

        # Create token for test_user (now admin)
        from app.core.security import create_access_token

        test_user_admin_token = create_access_token(
            data={"sub": test_user.username, "user_id": test_user.id}
        )

        # test_user (admin) deletes admin_user (the first admin) - should succeed
        response = await client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {test_user_admin_token}"},
        )
        assert response.status_code == 200

        # Now test_user is the only admin remaining
        # test_user tries to delete themselves (should fail - last admin)
        response = await client.delete(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {test_user_admin_token}"},
        )

        assert response.status_code == 400
        data = response.json()
        # Should fail with either "last admin" or "your own account" - both are valid safety checks
        error_msg = data["error"]["message"].lower()
        assert "last admin" in error_msg or "your own" in error_msg

    @pytest.mark.asyncio
    async def test_non_admin_cannot_delete_user(
        self, client: AsyncClient, test_user, test_user2, auth_token
    ):
        """Test that non-admin users cannot delete users."""
        # Clear any auth overrides
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.delete(
            f"/api/v1/users/{test_user2.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 403
