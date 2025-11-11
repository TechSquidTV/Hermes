"""
Tests for system settings service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import SystemSettings
from app.services.system_settings_service import SystemSettingsService


@pytest.fixture
def mock_settings_repo():
    """Mock SystemSettingsRepository for tests."""
    return MagicMock()


@pytest.fixture
def service():
    """Create a fresh service instance for each test."""
    return SystemSettingsService()


@pytest.mark.asyncio
class TestSystemSettingsServiceCaching:
    """Test caching behavior of the system settings service."""

    async def test_get_allow_public_signup_uses_cache(
        self, service, mock_settings_repo
    ):
        """Test that cached values are returned without DB calls."""
        # Setup
        settings_obj = SystemSettings(
            id=1,
            allow_public_signup=True,
            updated_at=datetime.now(timezone.utc),
        )

        with patch(
            "app.services.system_settings_service.async_session_maker"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = MagicMock()
            mock_settings_repo.get_settings = AsyncMock(return_value=settings_obj)

            with patch(
                "app.services.system_settings_service.SystemSettingsRepository",
                return_value=mock_settings_repo,
            ):
                # First call - should hit DB
                result1 = await service.get_allow_public_signup()
                assert result1 is True
                assert mock_settings_repo.get_settings.call_count == 1

                # Second call - should use cache
                result2 = await service.get_allow_public_signup()
                assert result2 is True
                assert (
                    mock_settings_repo.get_settings.call_count == 1
                )  # Not called again

    async def test_cache_invalidation_on_update(self, service, mock_settings_repo):
        """Test that cache is invalidated when settings are updated."""
        settings_obj = SystemSettings(
            id=1,
            allow_public_signup=False,
            updated_at=datetime.now(timezone.utc),
        )

        mock_settings_repo.update_allow_public_signup = AsyncMock(
            return_value=settings_obj
        )

        with patch(
            "app.services.system_settings_service.async_session_maker"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = MagicMock()

            with patch(
                "app.services.system_settings_service.SystemSettingsRepository",
                return_value=mock_settings_repo,
            ):
                # Update should invalidate cache
                await service.update_allow_public_signup(False, "user123")

                # Cache should be None after invalidation
                assert service._cache is None
                assert service._cache_timestamp is None

    async def test_fallback_to_env_var_on_db_failure(self, service):
        """Test fallback to environment variable when DB is unavailable."""
        with patch(
            "app.services.system_settings_service.async_session_maker"
        ) as mock_session:
            # Simulate DB failure
            mock_session.return_value.__aenter__.side_effect = Exception(
                "DB unavailable"
            )

            with patch(
                "app.services.system_settings_service.settings"
            ) as mock_settings:
                mock_settings.allow_public_signup = True

                # Should fall back to env var
                result = await service.get_allow_public_signup()
                assert result is True


@pytest.mark.asyncio
class TestSystemSettingsServiceUpdate:
    """Test update operations."""

    async def test_update_allow_public_signup_success(
        self, service, mock_settings_repo
    ):
        """Test successful signup setting update."""
        updated_obj = SystemSettings(
            id=1,
            allow_public_signup=False,
            updated_by_user_id="admin123",
            updated_at=datetime.now(timezone.utc),
        )

        mock_settings_repo.update_allow_public_signup = AsyncMock(
            return_value=updated_obj
        )

        with patch(
            "app.services.system_settings_service.async_session_maker"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = MagicMock()

            with patch(
                "app.services.system_settings_service.SystemSettingsRepository",
                return_value=mock_settings_repo,
            ):
                result = await service.update_allow_public_signup(False, "admin123")

                assert result["allow_public_signup"] is False
                assert result["updated_by_user_id"] == "admin123"
                mock_settings_repo.update_allow_public_signup.assert_called_once_with(
                    False, "admin123"
                )

    async def test_update_raises_on_db_error(self, service, mock_settings_repo):
        """Test that update raises exception on DB error."""
        mock_settings_repo.update_allow_public_signup = AsyncMock(
            side_effect=Exception("DB error")
        )

        with patch(
            "app.services.system_settings_service.async_session_maker"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = MagicMock()

            with patch(
                "app.services.system_settings_service.SystemSettingsRepository",
                return_value=mock_settings_repo,
            ):
                with pytest.raises(Exception, match="DB error"):
                    await service.update_allow_public_signup(True, "admin123")


@pytest.mark.asyncio
class TestSystemSettingsServiceGetAll:
    """Test getting all settings."""

    async def test_get_all_settings_from_db(self, service, mock_settings_repo):
        """Test getting all settings from database."""
        settings_obj = SystemSettings(
            id=1,
            allow_public_signup=True,
            updated_at=datetime.now(timezone.utc),
            updated_by_user_id="admin123",
        )

        with patch(
            "app.services.system_settings_service.async_session_maker"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = MagicMock()
            mock_settings_repo.get_settings = AsyncMock(return_value=settings_obj)

            with patch(
                "app.services.system_settings_service.SystemSettingsRepository",
                return_value=mock_settings_repo,
            ):
                result = await service.get_all_settings()

                assert result["allow_public_signup"] is True
                assert result["updated_by_user_id"] == "admin123"
                assert result["updated_at"] is not None

    async def test_get_all_settings_fallback_to_env(self, service):
        """Test fallback to environment variables when DB fails."""
        with patch(
            "app.services.system_settings_service.async_session_maker"
        ) as mock_session:
            mock_session.return_value.__aenter__.side_effect = Exception("DB error")

            with patch(
                "app.services.system_settings_service.settings"
            ) as mock_settings:
                mock_settings.allow_public_signup = False

                result = await service.get_all_settings()

                assert result["allow_public_signup"] is False
                assert result["updated_at"] is None
                assert result["updated_by_user_id"] is None
