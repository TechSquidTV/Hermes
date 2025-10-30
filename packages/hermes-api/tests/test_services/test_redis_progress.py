"""
Tests for RedisProgressService
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.redis_progress import RedisProgressService


@pytest.fixture
def redis_service():
    """Create a RedisProgressService instance for testing."""
    return RedisProgressService()


@pytest.fixture
def mock_sync_redis():
    """Mock synchronous Redis client."""
    return MagicMock()


@pytest.fixture
def mock_async_redis():
    """Mock asynchronous Redis client."""
    mock = MagicMock()
    # Add connection_pool attribute to prevent get_async_redis from recreating connection
    mock.connection_pool = MagicMock()
    return mock


def setup_async_redis_mock(redis_service, mock_redis):
    """
    Helper to properly configure mocked async redis with event loop tracking.

    Args:
        redis_service: RedisProgressService instance
        mock_redis: Mock redis client
    """
    redis_service._async_redis = mock_redis
    try:
        redis_service._async_redis_loop = asyncio.get_running_loop()
    except RuntimeError:
        redis_service._async_redis_loop = None


class TestRedisProgressServiceSync:
    """Test synchronous Redis operations."""

    def test_set_progress_sync_success(self, redis_service, mock_sync_redis):
        """Test setting progress data synchronously."""
        redis_service._sync_redis = mock_sync_redis
        download_id = "test-download-123"
        progress_data = {
            "percentage": 45.5,
            "downloaded_bytes": 1024000,
            "total_bytes": 2048000,
            "speed": 512000.0,
        }

        redis_service.set_progress_sync(download_id, progress_data, ttl=1800)

        # Verify Redis setex was called with correct parameters
        mock_sync_redis.setex.assert_called_once()
        call_args = mock_sync_redis.setex.call_args
        assert call_args[0][0] == f"download:{download_id}:progress"
        assert call_args[0][1] == 1800
        stored_data = json.loads(call_args[0][2])
        assert stored_data == progress_data

    def test_set_progress_sync_default_ttl(self, redis_service, mock_sync_redis):
        """Test setting progress with default TTL."""
        redis_service._sync_redis = mock_sync_redis
        download_id = "test-download-123"
        progress_data = {"percentage": 50.0}

        redis_service.set_progress_sync(download_id, progress_data)

        # Should use default TTL of 3600 seconds (1 hour)
        call_args = mock_sync_redis.setex.call_args
        assert call_args[0][1] == 3600

    def test_set_progress_sync_redis_error(self, redis_service, mock_sync_redis):
        """Test error handling when Redis sync set fails."""
        redis_service._sync_redis = mock_sync_redis
        mock_sync_redis.setex.side_effect = Exception("Redis connection failed")
        download_id = "test-download-123"
        progress_data = {"percentage": 50.0}

        # Should not raise exception, just log error
        redis_service.set_progress_sync(download_id, progress_data)
        mock_sync_redis.setex.assert_called_once()

    def test_get_sync_redis_creates_connection(self, redis_service):
        """Test that get_sync_redis creates connection on first call."""
        with patch("app.services.redis_progress.redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis

            result = redis_service.get_sync_redis()

            assert result == mock_redis
            mock_from_url.assert_called_once()
            # Subsequent calls should return same instance
            result2 = redis_service.get_sync_redis()
            assert result2 == mock_redis
            assert mock_from_url.call_count == 1  # Only called once


class TestRedisProgressServiceAsync:
    """Test asynchronous Redis operations."""

    @pytest.mark.asyncio
    async def test_delete_progress_async_success(self, redis_service, mock_async_redis):
        """Test deleting progress data asynchronously."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        download_id = "test-download-456"

        await redis_service.delete_progress(download_id)

        # Verify async delete was called
        mock_async_redis.delete.assert_called_once_with(
            f"download:{download_id}:progress"
        )

    @pytest.mark.asyncio
    async def test_get_progress_success(self, redis_service):
        """Test retrieving progress data."""
        download_id = "test-download-789"
        expected_data = {
            "percentage": 90.0,
            "downloaded_bytes": 9216000,
            "total_bytes": 10240000,
            "speed": 1024000.0,
        }

        # Create async mock
        mock_redis = AsyncMock()
        mock_redis.connection_pool = MagicMock()
        mock_redis.get.return_value = json.dumps(expected_data)
        setup_async_redis_mock(redis_service, mock_redis)

        result = await redis_service.get_progress(download_id)

        assert result == expected_data
        mock_redis.get.assert_called_once_with(f"download:{download_id}:progress")

    @pytest.mark.asyncio
    async def test_get_progress_not_found(self, redis_service, mock_async_redis):
        """Test retrieving progress when key doesn't exist."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.get.return_value = None
        download_id = "nonexistent-download"

        result = await redis_service.get_progress(download_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_progress_invalid_json(self, redis_service, mock_async_redis):
        """Test handling invalid JSON from Redis."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.get.return_value = "invalid-json-data"
        download_id = "test-download-bad"

        result = await redis_service.get_progress(download_id)

        # Should return None on JSON decode error
        assert result is None

    @pytest.mark.asyncio
    async def test_get_progress_redis_error(self, redis_service, mock_async_redis):
        """Test error handling when Redis get fails."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.get.side_effect = Exception("Redis connection lost")
        download_id = "test-download-error"

        result = await redis_service.get_progress(download_id)

        # Should return None on error
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_progress_success(self, redis_service, mock_async_redis):
        """Test deleting progress data."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        download_id = "test-download-delete"

        await redis_service.delete_progress(download_id)

        mock_async_redis.delete.assert_called_once_with(
            f"download:{download_id}:progress"
        )

    @pytest.mark.asyncio
    async def test_delete_progress_error(self, redis_service, mock_async_redis):
        """Test error handling when Redis delete fails."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.delete.side_effect = Exception("Redis error")
        download_id = "test-download-delete-error"

        # Should not raise exception
        await redis_service.delete_progress(download_id)
        mock_async_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_redis_creates_connection(self, redis_service):
        """Test that get_async_redis creates connection on first call."""
        with patch("app.services.redis_progress.aioredis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis

            result = await redis_service.get_async_redis()

            assert result == mock_redis
            mock_from_url.assert_called_once()
            # Subsequent calls should return same instance
            result2 = await redis_service.get_async_redis()
            assert result2 == mock_redis
            assert mock_from_url.call_count == 1


class TestRedisProgressServiceKeys:
    """Test Redis key formatting."""

    @pytest.mark.asyncio
    async def test_progress_key_format(self, redis_service, mock_async_redis):
        """Test that progress keys use correct format."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        download_id = "abc-123-def-456"

        await redis_service.get_progress(download_id)

        # Should use format: download:{id}:progress
        expected_key = "download:abc-123-def-456:progress"
        mock_async_redis.get.assert_called_once_with(expected_key)

    def test_sync_progress_key_format(self, redis_service, mock_sync_redis):
        """Test that sync progress keys use correct format."""
        redis_service._sync_redis = mock_sync_redis
        download_id = "xyz-789-abc-012"

        redis_service.set_progress_sync(download_id, {"percentage": 50})

        # Should use format: download:{id}:progress
        call_args = mock_sync_redis.setex.call_args
        assert call_args[0][0] == "download:xyz-789-abc-012:progress"


class TestRedisProgressServiceDataIntegrity:
    """Test data serialization and integrity."""

    def test_set_progress_preserves_data_types(self, redis_service, mock_sync_redis):
        """Test that different data types are preserved through JSON serialization."""
        redis_service._sync_redis = mock_sync_redis
        download_id = "test-types"
        progress_data = {
            "percentage": 66.7,  # float
            "downloaded_bytes": 2048000,  # int
            "status": "downloading",  # string
            "eta": None,  # null
        }

        redis_service.set_progress_sync(download_id, progress_data)

        call_args = mock_sync_redis.setex.call_args
        stored_data = json.loads(call_args[0][2])

        # Verify types are preserved
        assert isinstance(stored_data["percentage"], float)
        assert isinstance(stored_data["downloaded_bytes"], int)
        assert isinstance(stored_data["status"], str)
        assert stored_data["eta"] is None

    def test_roundtrip_data_integrity(self, redis_service, mock_sync_redis):
        """Test that data survives roundtrip through Redis (sync)."""
        redis_service._sync_redis = mock_sync_redis
        download_id = "test-roundtrip"
        original_data = {
            "percentage": 33.33,
            "downloaded_bytes": 1024000,
            "total_bytes": 3072000,
            "speed": 256000.5,
            "eta": 10.5,
        }

        # Set progress synchronously
        redis_service.set_progress_sync(download_id, original_data)

        # Get the data that would be stored
        call_args = mock_sync_redis.setex.call_args
        stored_json = call_args[0][2]

        # Verify data roundtrips correctly through JSON
        retrieved_data = json.loads(stored_json)

        # Verify data integrity
        assert retrieved_data == original_data
