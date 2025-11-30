"""
Tests for initial admin creation from environment variables.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestInitialAdminCreation:
    """Test initial admin creation from environment variables."""

    @pytest.mark.asyncio
    async def test_initial_admin_created_from_env_vars(
        self, db_session: AsyncSession, monkeypatch
    ):
        """Test that initial admin is created from environment variables on startup."""
        # Set initial admin credentials in settings
        from app.core import config

        monkeypatch.setattr(config.settings, "initial_admin_username", "envadmin")
        monkeypatch.setattr(
            config.settings, "initial_admin_email", "envadmin@example.com"
        )
        monkeypatch.setattr(config.settings, "initial_admin_password", "EnvPass123")

        # Verify no users exist
        from app.db.repositories import UserRepository

        user_repo = UserRepository(db_session)
        count = await user_repo.count()
        assert count == 0

        # Call the initialization function
        from app.main import initialize_admin_user

        await initialize_admin_user()

        # Verify admin user was created
        admin_user = await user_repo.get_by_username("envadmin")
        assert admin_user is not None
        assert admin_user.username == "envadmin"
        assert admin_user.email == "envadmin@example.com"
        assert admin_user.is_admin is True
        assert admin_user.is_active is True

        # Verify password is hashed correctly
        from app.core.security import verify_password

        assert verify_password("EnvPass123", admin_user.password_hash)

    @pytest.mark.asyncio
    async def test_initial_admin_not_created_when_users_exist(
        self, db_session: AsyncSession, test_user, monkeypatch
    ):
        """Test that initial admin is NOT created if users already exist."""
        # Set initial admin credentials in settings
        from app.core import config

        monkeypatch.setattr(config.settings, "initial_admin_username", "envadmin")
        monkeypatch.setattr(
            config.settings, "initial_admin_email", "envadmin@example.com"
        )
        monkeypatch.setattr(config.settings, "initial_admin_password", "EnvPass123")

        # Verify test_user exists
        from app.db.repositories import UserRepository

        user_repo = UserRepository(db_session)
        count = await user_repo.count()
        assert count >= 1

        # Call the initialization function
        from app.main import initialize_admin_user

        await initialize_admin_user()

        # Verify initial admin was NOT created
        admin_user = await user_repo.get_by_username("envadmin")
        assert admin_user is None

        # Verify original user count unchanged
        new_count = await user_repo.count()
        assert new_count == count

    @pytest.mark.asyncio
    async def test_initial_admin_not_created_without_credentials(
        self, db_session: AsyncSession, monkeypatch
    ):
        """Test that initial admin is NOT created if credentials are not provided."""
        # Set empty credentials
        from app.core import config

        monkeypatch.setattr(config.settings, "initial_admin_username", None)
        monkeypatch.setattr(config.settings, "initial_admin_email", None)
        monkeypatch.setattr(config.settings, "initial_admin_password", None)

        # Verify no users exist
        from app.db.repositories import UserRepository

        user_repo = UserRepository(db_session)
        count = await user_repo.count()
        assert count == 0

        # Call the initialization function
        from app.main import initialize_admin_user

        await initialize_admin_user()

        # Verify no users were created
        new_count = await user_repo.count()
        assert new_count == 0

    @pytest.mark.asyncio
    async def test_initial_admin_not_created_with_partial_credentials(
        self, db_session: AsyncSession, monkeypatch
    ):
        """Test that initial admin is NOT created if only partial credentials provided."""
        # Set only partial credentials
        from app.core import config

        monkeypatch.setattr(config.settings, "initial_admin_username", "envadmin")
        monkeypatch.setattr(config.settings, "initial_admin_email", None)
        monkeypatch.setattr(config.settings, "initial_admin_password", "EnvPass123")

        # Verify no users exist
        from app.db.repositories import UserRepository

        user_repo = UserRepository(db_session)
        count = await user_repo.count()
        assert count == 0

        # Call the initialization function
        from app.main import initialize_admin_user

        await initialize_admin_user()

        # Verify no users were created (missing email)
        new_count = await user_repo.count()
        assert new_count == 0
