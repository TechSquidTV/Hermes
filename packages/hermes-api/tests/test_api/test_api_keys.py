"""
Tests for API key repository operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_api_key, hash_api_key
from app.db.repositories import ApiKeyRepository, UserRepository


class TestApiKeyRepository:
    """Test API key repository operations."""

    async def test_create_api_key(self, db_session: AsyncSession, test_user):
        """Test creating an API key in the database."""
        # Use the existing db_session fixture instead of creating new sessions
        api_key_repo = ApiKeyRepository(db_session)

        # Create API key
        api_key = await api_key_repo.create(
            user_id=test_user.id,
            name="Test API Key",
            key_hash=hash_api_key("test-key-123"),
            permissions=["read", "write"],
            rate_limit=100,
        )

        await db_session.commit()
        await db_session.refresh(api_key)

        # Verify creation
        assert api_key.id is not None
        assert api_key.user_id == test_user.id
        assert api_key.name == "Test API Key"
        assert api_key.key_hash == hash_api_key("test-key-123")
        assert api_key.permissions == ["read", "write"]
        assert api_key.rate_limit == 100
        assert api_key.is_active is True
        assert api_key.created_at is not None

    async def test_get_api_key_by_hash(self, db_session: AsyncSession, test_user):
        """Test getting API key by hash."""
        api_key_repo = ApiKeyRepository(db_session)
        plain_key = create_api_key()
        key_hash = hash_api_key(plain_key)

        # Create API key
        created_key = await api_key_repo.create(
            user_id=test_user.id,
            name="Test Key",
            key_hash=key_hash,
            permissions=["read"],
        )

        await db_session.commit()

        # Retrieve by hash
        retrieved_key = await api_key_repo.get_by_key_hash(key_hash)

        assert retrieved_key is not None
        assert retrieved_key.id == created_key.id
        assert retrieved_key.user_id == test_user.id
        assert retrieved_key.name == "Test Key"

    async def test_get_api_key_by_id(self, db_session: AsyncSession, test_user):
        """Test getting API key by ID."""
        api_key_repo = ApiKeyRepository(db_session)

        # Create API key
        created_key = await api_key_repo.create(
            user_id=test_user.id,
            name="Test Key",
            key_hash=hash_api_key("test-key"),
            permissions=["read"],
        )

        await db_session.commit()

        # Retrieve by ID
        retrieved_key = await api_key_repo.get_by_id(created_key.id)

        assert retrieved_key is not None
        assert retrieved_key.id == created_key.id
        assert retrieved_key.user_id == test_user.id

    async def test_get_api_keys_by_user(self, db_session: AsyncSession, test_user):
        """Test getting all API keys for a user."""
        api_key_repo = ApiKeyRepository(db_session)
        user_repo = UserRepository(db_session)

        # Create multiple API keys for the user
        await api_key_repo.create(
            user_id=test_user.id,
            name="Key 1",
            key_hash=hash_api_key("key1"),
            permissions=["read"],
        )
        await api_key_repo.create(
            user_id=test_user.id,
            name="Key 2",
            key_hash=hash_api_key("key2"),
            permissions=["write"],
        )

        # Create key for different user (should not be returned)
        from app.core.security import get_password_hash

        other_user = await user_repo.create(
            username="otheruser",
            email="other@example.com",
            password_hash=get_password_hash("password"),
        )
        await api_key_repo.create(
            user_id=other_user.id,
            name="Other Key",
            key_hash=hash_api_key("other-key"),
            permissions=["read"],
        )

        await db_session.commit()

        # Get keys for test user
        user_keys = await api_key_repo.get_by_user_id(test_user.id)

        assert len(user_keys) == 2
        key_names = [key.name for key in user_keys]
        assert "Key 1" in key_names
        assert "Key 2" in key_names
        assert "Other Key" not in key_names

    async def test_update_last_used(self, db_session: AsyncSession, test_user):
        """Test updating API key last used timestamp."""
        api_key_repo = ApiKeyRepository(db_session)

        # Create API key
        api_key = await api_key_repo.create(
            user_id=test_user.id,
            name="Test Key",
            key_hash=hash_api_key("test-key"),
            permissions=["read"],
        )

        await db_session.commit()

        # Update last used
        updated_key = await api_key_repo.update_last_used(api_key.id)

        assert updated_key is not None
        assert updated_key.last_used is not None

    async def test_get_nonexistent_api_key(self, db_session: AsyncSession):
        """Test getting non-existent API key."""
        api_key_repo = ApiKeyRepository(db_session)

        # Try to get non-existent key
        result = await api_key_repo.get_by_id("nonexistent-id")
        assert result is None

        result = await api_key_repo.get_by_key_hash("nonexistent-hash")
        assert result is None

    async def test_api_key_deactivation(self, db_session: AsyncSession, test_user):
        """Test deactivating API keys."""
        api_key_repo = ApiKeyRepository(db_session)

        # Create API key
        api_key = await api_key_repo.create(
            user_id=test_user.id,
            name="Test Key",
            key_hash=hash_api_key("test-key"),
            permissions=["read"],
        )

        await db_session.commit()

        # Deactivate the key
        api_key.is_active = False
        await api_key_repo.update(api_key)

        await db_session.commit()

        # Verify it's deactivated
        updated_key = await api_key_repo.get_by_id(api_key.id)
        assert updated_key.is_active is False
