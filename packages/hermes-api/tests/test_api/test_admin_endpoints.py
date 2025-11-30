"""
Tests for admin endpoints - settings and configuration.
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


class TestAdminSettings:
    """Test admin settings endpoints."""

    @pytest.mark.asyncio
    async def test_get_settings_requires_admin(self, client: AsyncClient):
        """Test that non-admin users cannot access settings."""
        from app.api.dependencies import get_current_user_from_token
        from app.core.security import create_access_token
        from app.main import app

        # Mock authentication to bypass database for this test
        mock_user = {
            "id": "test-user-id",
            "username": "testuser",
            "email": "test@example.com",
            "is_admin": False,
        }

        token = create_access_token(
            data={"sub": mock_user["username"], "user_id": mock_user["id"]}
        )

        # Override the authentication dependency
        app.dependency_overrides[get_current_user_from_token] = lambda: mock_user

        try:
            response = await client.get(
                "/api/v1/admin/settings",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 403
            data = response.json()
            # The response could have either 'detail' or 'error' structure
            assert ("detail" in data and "Admin access required" in data["detail"]) or (
                "error" in data and "Admin access required" in data["error"]["message"]
            )
        finally:
            # Clean up override
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_settings_success_for_admin(
        self, client: AsyncClient, admin_auth_token
    ):
        """Test that admin users can access settings."""
        with patch(
            "app.services.system_settings_service.system_settings_service.get_all_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = {
                "allow_public_signup": True,
                "updated_at": "2025-11-10T03:00:00Z",
                "updated_by_user_id": None,
            }

            response = await client.get(
                "/api/v1/admin/settings",
                headers={"Authorization": f"Bearer {admin_auth_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "allowPublicSignup" in data
            assert data["allowPublicSignup"] is True

    @pytest.mark.asyncio
    async def test_update_signup_requires_admin(self, client: AsyncClient, test_user):
        """Test that non-admin users cannot update signup setting."""
        from app.core.security import create_access_token

        # Create token directly in test to avoid fixture ordering issues
        token = create_access_token(
            data={"sub": test_user.username, "user_id": test_user.id}
        )

        response = await client.put(
            "/api/v1/admin/settings/signup",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_signup_success_for_admin(
        self, client: AsyncClient, admin_auth_token
    ):
        """Test that admin users can update signup setting."""
        with patch(
            "app.services.system_settings_service.system_settings_service.update_allow_public_signup"
        ) as mock_update:
            mock_update.return_value = {
                "allow_public_signup": False,
                "updated_at": "2025-11-10T03:00:00Z",
                "updated_by_user_id": "admin-123",
            }

            response = await client.put(
                "/api/v1/admin/settings/signup",
                json={"enabled": False},
                headers={"Authorization": f"Bearer {admin_auth_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["allowPublicSignup"] is False
            mock_update.assert_called_once()


class TestAdminConfig:
    """Test admin configuration endpoints (moved from /config)."""

    @pytest.mark.asyncio
    async def test_get_config_requires_admin(self, client: AsyncClient, test_user):
        """Test that non-admin users cannot access config."""
        from app.core.security import create_access_token

        # Create token directly in test to avoid fixture ordering issues
        token = create_access_token(
            data={"sub": test_user.username, "user_id": test_user.id}
        )

        response = await client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_config_success_for_admin(
        self, client: AsyncClient, admin_auth_token
    ):
        """Test that admin users can access config."""
        response = await client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {admin_auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Check for expected config fields
        assert "outputTemplate" in data or "output_template" in data
        assert "maxConcurrentDownloads" in data or "max_concurrent_downloads" in data

    @pytest.mark.asyncio
    async def test_update_config_requires_admin(self, client: AsyncClient, test_user):
        """Test that non-admin users cannot update config."""
        from app.core.security import create_access_token

        # Create token directly in test to avoid fixture ordering issues
        token = create_access_token(
            data={"sub": test_user.username, "user_id": test_user.id}
        )

        response = await client.put(
            "/api/v1/admin/config",
            json={"maxConcurrentDownloads": 5},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_config_success_for_admin(
        self, client: AsyncClient, admin_auth_token
    ):
        """Test that admin users can update config."""
        response = await client.put(
            "/api/v1/admin/config",
            json={"maxConcurrentDownloads": 5},
            headers={"Authorization": f"Bearer {admin_auth_token}"},
        )

        # Should return 200 even if not fully implemented
        assert response.status_code == 200


class TestPublicConfig:
    """Test public config endpoint (no auth required)."""

    @pytest.mark.asyncio
    async def test_public_config_no_auth_required(self, client: AsyncClient):
        """Test that public config is accessible without authentication."""
        with patch(
            "app.services.system_settings_service.system_settings_service.get_allow_public_signup"
        ) as mock_get_signup:
            mock_get_signup.return_value = True

            # Clear any auth overrides
            from app.main import app

            app.dependency_overrides.clear()

            response = await client.get("/api/v1/config/public")

            assert response.status_code == 200
            data = response.json()
            assert "allowPublicSignup" in data
