"""Pytest configuration and fixtures."""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Set test environment variables BEFORE any imports
os.environ.setdefault("HERMES_DEBUG", "true")
os.environ.setdefault("HERMES_DATABASE_URL", "sqlite+aiosqlite:///./test_hermes.db")
os.environ.setdefault("HERMES_REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault(
    "HERMES_SECRET_KEY", "test-secret-key-min-32-chars-long-for-testing"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_database():
    """Set up test database before each test."""
    # Import all models to ensure they're registered with Base
    from app.db.base import create_tables, drop_tables, engine

    # Create all tables before test
    await create_tables()

    yield

    # Drop all tables after test
    await drop_tables()

    # Dispose of the engine to close connections
    await engine.dispose()

    # Clean up test database files
    test_files = ["test_hermes.db", "test_hermes.db-shm", "test_hermes.db-wal"]
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except OSError:
                pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for tests."""
    from app.db.base import async_session_maker

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(setup_test_database) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing with auth mocked."""
    from app.core.security import get_current_api_key
    from app.main import app

    # Override authentication dependency for testing
    async def mock_get_api_key():
        return "test-api-key"

    app.dependency_overrides[get_current_api_key] = mock_get_api_key

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user for authentication tests."""
    from app.core.security import get_password_hash
    from app.db.repositories import UserRepository

    user_repo = UserRepository(db_session)

    # Create test user
    user = await user_repo.create(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpass123"),
    )

    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def test_user2(db_session: AsyncSession):
    """Create a second test user for isolation tests."""
    from app.core.security import get_password_hash
    from app.db.repositories import UserRepository

    user_repo = UserRepository(db_session)

    # Create second test user
    user = await user_repo.create(
        username="testuser2",
        email="test2@example.com",
        password_hash=get_password_hash("testpass123"),
    )

    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def auth_token(test_user):
    """Create an authentication token for a test user."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={"sub": test_user.username, "user_id": test_user.id}
    )

    return token


@pytest_asyncio.fixture
async def auth_token2(test_user2):
    """Create an authentication token for the second test user."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={"sub": test_user2.username, "user_id": test_user2.id}
    )

    return token
