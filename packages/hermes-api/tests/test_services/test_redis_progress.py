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


class TestRedisSSETokenStorage:
    """Test Redis SSE token storage operations."""

    @pytest.mark.asyncio
    async def test_store_sse_token(self, redis_service, mock_async_redis):
        """Test storing SSE token with TTL in Redis."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.setex = AsyncMock()

        token = "sse_test123abc"
        token_data = {
            "scope": "download:abc-123",
            "user_id": "user123",
            "expires_at": "2025-01-15T10:00:00Z",
            "permissions": ["read"],
        }
        ttl = 600

        await redis_service.store_sse_token(token, token_data, ttl)

        # Verify Redis setex was called
        mock_async_redis.setex.assert_called_once()
        call_args = mock_async_redis.setex.call_args
        assert call_args[0][0] == f"sse:token:{token}"
        assert call_args[0][1] == ttl
        stored_data = json.loads(call_args[0][2])
        assert stored_data["scope"] == token_data["scope"]
        assert stored_data["user_id"] == token_data["user_id"]

    @pytest.mark.asyncio
    async def test_store_sse_token_with_datetime(self, redis_service, mock_async_redis):
        """Test storing SSE token with datetime fields serializes correctly."""
        from datetime import datetime, timedelta, timezone

        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.setex = AsyncMock()

        token = "sse_test456def"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        created_at = datetime.now(timezone.utc)
        token_data = {
            "scope": "queue",
            "user_id": "user456",
            "expires_at": expires_at,  # Datetime object
            "created_at": created_at,  # Datetime object
            "permissions": ["read"],
        }

        await redis_service.store_sse_token(token, token_data, 600)

        # Verify datetime was serialized to ISO string
        call_args = mock_async_redis.setex.call_args
        stored_json = call_args[0][2]
        stored_data = json.loads(stored_json)
        assert isinstance(stored_data["expires_at"], str)
        assert isinstance(stored_data["created_at"], str)
        # Verify it's valid ISO format
        assert "T" in stored_data["expires_at"]
        assert "Z" in stored_data["expires_at"] or "+" in stored_data["expires_at"]

    @pytest.mark.asyncio
    async def test_get_sse_token(self, redis_service, mock_async_redis):
        """Test retrieving stored SSE token from Redis."""
        setup_async_redis_mock(redis_service, mock_async_redis)

        token = "sse_test789ghi"
        token_data = {
            "scope": "download:test-123",
            "user_id": "user789",
            "expires_at": "2025-01-15T10:00:00Z",
            "permissions": ["read"],
        }

        mock_async_redis.get = AsyncMock(return_value=json.dumps(token_data))

        result = await redis_service.get_sse_token(token)

        # Verify Redis get was called with correct key
        mock_async_redis.get.assert_called_once_with(f"sse:token:{token}")
        assert result == token_data
        assert result["scope"] == "download:test-123"
        assert result["user_id"] == "user789"

    @pytest.mark.asyncio
    async def test_get_nonexistent_sse_token(self, redis_service, mock_async_redis):
        """Test retrieving non-existent token returns None."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.get = AsyncMock(return_value=None)

        token = "sse_nonexistent"
        result = await redis_service.get_sse_token(token)

        assert result is None
        mock_async_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_sse_token(self, redis_service, mock_async_redis):
        """Test deleting SSE token from Redis."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.delete = AsyncMock()

        token = "sse_delete_me"

        await redis_service.delete_sse_token(token)

        # Verify Redis delete was called with correct key
        mock_async_redis.delete.assert_called_once_with(f"sse:token:{token}")

    @pytest.mark.asyncio
    async def test_revoke_user_sse_tokens_by_scope(
        self, redis_service, mock_async_redis
    ):
        """Test revoking SSE tokens filtered by scope prefix."""
        setup_async_redis_mock(redis_service, mock_async_redis)

        # Mock scan_iter to return token keys
        token_keys = [
            "sse:token:sse_abc123",
            "sse:token:sse_def456",
            "sse:token:sse_ghi789",
        ]

        async def mock_scan_iter(match):
            for key in token_keys:
                yield key

        mock_async_redis.scan_iter = mock_scan_iter

        # Mock get to return token data
        token_data = [
            json.dumps({"user_id": "user123", "scope": "download:test-123"}),  # Match
            json.dumps({"user_id": "user123", "scope": "download:test-456"}),  # Match
            json.dumps({"user_id": "user123", "scope": "queue"}),  # No match
        ]

        mock_async_redis.get = AsyncMock(side_effect=token_data)
        mock_async_redis.delete = AsyncMock()

        # Revoke tokens with scope prefix "download:test-"
        revoked = await redis_service.revoke_user_sse_tokens(
            user_id="user123", scope_prefix="download:test-"
        )

        # Should revoke 2 tokens (those starting with "download:test-")
        assert revoked == 2
        # Verify delete was called twice
        assert mock_async_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_revoke_all_user_tokens_no_scope_filter(
        self, redis_service, mock_async_redis
    ):
        """Test revoking all SSE tokens for a user (no scope filter)."""
        setup_async_redis_mock(redis_service, mock_async_redis)

        # Mock scan_iter to return token keys
        token_keys = [
            "sse:token:sse_aaa111",
            "sse:token:sse_bbb222",
            "sse:token:sse_ccc333",
        ]

        async def mock_scan_iter(match):
            for key in token_keys:
                yield key

        mock_async_redis.scan_iter = mock_scan_iter

        # Mock get to return token data (different users)
        token_data = [
            json.dumps({"user_id": "user123", "scope": "download:abc"}),  # Match
            json.dumps({"user_id": "user456", "scope": "queue"}),  # Different user
            json.dumps({"user_id": "user123", "scope": "system"}),  # Match
        ]

        mock_async_redis.get = AsyncMock(side_effect=token_data)
        mock_async_redis.delete = AsyncMock()

        # Revoke all tokens for user123
        revoked = await redis_service.revoke_user_sse_tokens(
            user_id="user123", scope_prefix=None
        )

        # Should revoke 2 tokens (both belonging to user123)
        assert revoked == 2
        assert mock_async_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_store_sse_token_raises_on_redis_error(
        self, redis_service, mock_async_redis
    ):
        """Test that store_sse_token raises exception on Redis error."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.setex = AsyncMock(
            side_effect=Exception("Redis connection failed")
        )

        token = "sse_error_test"
        token_data = {"scope": "queue", "user_id": "user123"}

        with pytest.raises(Exception, match="Redis connection failed"):
            await redis_service.store_sse_token(token, token_data, 300)

    @pytest.mark.asyncio
    async def test_get_sse_token_handles_json_decode_error(
        self, redis_service, mock_async_redis
    ):
        """Test that get_sse_token handles invalid JSON gracefully."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        # Return invalid JSON
        mock_async_redis.get = AsyncMock(return_value="not valid json{")

        token = "sse_bad_json"
        result = await redis_service.get_sse_token(token)

        # Should return None on JSON decode error
        assert result is None


class TestRedisProgressServicePubSub:
    """Test Redis pub/sub functionality for SSE."""

    @pytest.mark.asyncio
    async def test_serialize_data_with_datetime(self, redis_service):
        """Verify datetime objects are converted to ISO strings."""
        from datetime import datetime, timezone

        data = {
            "download_id": "test-123",
            "created_at": datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
            "progress": 50.5,
        }

        serialized = redis_service._serialize_data(data)

        # Datetime should be converted to ISO strings
        assert serialized["created_at"] == "2025-01-15T10:30:00+00:00"
        assert serialized["updated_at"] == "2025-01-15T10:35:00+00:00"
        # Other types should remain unchanged
        assert serialized["download_id"] == "test-123"
        assert serialized["progress"] == 50.5

    @pytest.mark.asyncio
    async def test_serialize_data_with_nested_datetime(self, redis_service):
        """Verify nested datetime objects are serialized."""
        from datetime import datetime, timezone

        data = {
            "download_id": "test-123",
            "metadata": {
                "started_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "nested": {
                    "completed_at": datetime(
                        2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc
                    ),
                },
            },
        }

        serialized = redis_service._serialize_data(data)

        # Check nested datetime serialization
        assert serialized["metadata"]["started_at"] == "2025-01-15T10:00:00+00:00"
        assert (
            serialized["metadata"]["nested"]["completed_at"]
            == "2025-01-15T11:00:00+00:00"
        )

    @pytest.mark.asyncio
    async def test_serialize_data_max_depth_protection(self, redis_service):
        """Verify max recursion depth protection."""
        # Create deeply nested dict
        data = {"level": 1}
        current = data
        for i in range(2, 15):
            current["nested"] = {"level": i}
            current = current["nested"]

        # Should raise ValueError when exceeding max depth
        with pytest.raises(ValueError, match="Max recursion depth"):
            redis_service._serialize_data(data, max_depth=10)

    @pytest.mark.asyncio
    async def test_publish_event_success(self, redis_service, mock_async_redis):
        """Test successful event publishing to Redis channel."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.publish = AsyncMock()

        channel = "download:updates"
        event_type = "download_progress"
        data = {"download_id": "test-123", "progress": 50}

        await redis_service.publish_event(channel, event_type, data)

        # Verify Redis publish was called
        mock_async_redis.publish.assert_called_once()
        call_args = mock_async_redis.publish.call_args
        assert call_args[0][0] == channel

        # Verify message format
        message = json.loads(call_args[0][1])
        assert message["type"] == event_type
        assert message["data"]["download_id"] == "test-123"
        assert message["data"]["progress"] == 50
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def test_publish_event_with_datetime(self, redis_service, mock_async_redis):
        """Test event publishing with datetime fields."""
        from datetime import datetime, timezone

        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.publish = AsyncMock()

        data = {
            "download_id": "test-123",
            "started_at": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        }

        await redis_service.publish_event("download:updates", "download_started", data)

        # Verify datetime was serialized before publishing
        call_args = mock_async_redis.publish.call_args
        message = json.loads(call_args[0][1])
        assert message["data"]["started_at"] == "2025-01-15T10:00:00+00:00"

    @pytest.mark.asyncio
    async def test_publish_event_handles_redis_error(
        self, redis_service, mock_async_redis
    ):
        """Test that Redis publish errors are handled gracefully."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.publish = AsyncMock(
            side_effect=Exception("Redis connection lost")
        )

        # Should not raise exception, just log error
        await redis_service.publish_event(
            "download:updates", "test_event", {"test": "data"}
        )

        # Verify publish was attempted
        mock_async_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_to_channels(self, redis_service, mock_async_redis):
        """Test subscribing to multiple channels."""
        setup_async_redis_mock(redis_service, mock_async_redis)

        # Mock pubsub
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_async_redis.pubsub = MagicMock(return_value=mock_pubsub)

        # Mock pubsub.listen() to yield test messages
        async def mock_listen():
            # First message: subscription confirmation (skip)
            yield {"type": "subscribe", "channel": "download:updates"}
            # Second message: actual message
            yield {
                "type": "message",
                "channel": "download:updates",
                "data": json.dumps(
                    {
                        "type": "download_progress",
                        "data": {"download_id": "test-123", "progress": 50},
                        "timestamp": "2025-01-15T10:00:00Z",
                    }
                ),
            }

        mock_pubsub.listen = mock_listen

        # Subscribe and consume messages
        channels = ["download:updates", "queue:updates"]
        messages = []
        async for message in redis_service.subscribe_to_channels(channels):
            messages.append(message)
            break  # Just get first message

        # Verify subscription was called
        mock_pubsub.subscribe.assert_called_once_with(*channels)

        # Verify message was parsed correctly
        assert len(messages) == 1
        assert messages[0]["type"] == "download_progress"
        assert messages[0]["data"]["download_id"] == "test-123"
        assert messages[0]["data"]["progress"] == 50

    @pytest.mark.asyncio
    async def test_subscribe_handles_json_decode_error(
        self, redis_service, mock_async_redis
    ):
        """Test that invalid JSON messages are skipped gracefully."""
        setup_async_redis_mock(redis_service, mock_async_redis)

        # Mock pubsub
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_async_redis.pubsub = MagicMock(return_value=mock_pubsub)

        # Mock pubsub.listen() to yield invalid JSON
        async def mock_listen():
            yield {"type": "message", "channel": "test", "data": "not valid json{"}
            # Stop after invalid message
            return

        mock_pubsub.listen = mock_listen

        # Should not raise exception
        messages = []
        async for message in redis_service.subscribe_to_channels(["test"]):
            messages.append(message)

        # No messages should be yielded (invalid JSON was skipped)
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_publish_download_progress(self, redis_service, mock_async_redis):
        """Test download progress event publishing."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.publish = AsyncMock()

        download_id = "test-download-123"
        progress_data = {
            "progress": 75.5,
            "speed": 512000,
            "eta": 120,
        }

        await redis_service.publish_download_progress(download_id, progress_data)

        # Verify publish was called
        mock_async_redis.publish.assert_called_once()
        call_args = mock_async_redis.publish.call_args

        # Verify correct channel
        assert call_args[0][0] == "download:updates"

        # Verify message format
        message = json.loads(call_args[0][1])
        assert message["type"] == "download_progress"
        assert message["data"]["download_id"] == download_id
        assert message["data"]["progress"] == 75.5
        assert message["data"]["speed"] == 512000
        assert message["data"]["eta"] == 120

    @pytest.mark.asyncio
    async def test_publish_queue_update(self, redis_service, mock_async_redis):
        """Test queue update event publishing."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.publish = AsyncMock()

        action = "added"
        download_id = "test-download-456"
        data = {"position": 3, "total": 5}

        await redis_service.publish_queue_update(action, download_id, data)

        # Verify publish was called
        mock_async_redis.publish.assert_called_once()
        call_args = mock_async_redis.publish.call_args

        # Verify correct channel
        assert call_args[0][0] == "queue:updates"

        # Verify message format
        message = json.loads(call_args[0][1])
        assert message["type"] == "queue_update"
        assert message["data"]["action"] == "added"
        assert message["data"]["download_id"] == download_id
        assert message["data"]["position"] == 3
        assert message["data"]["total"] == 5

    @pytest.mark.asyncio
    async def test_publish_queue_update_without_data(
        self, redis_service, mock_async_redis
    ):
        """Test queue update with no additional data."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.publish = AsyncMock()

        await redis_service.publish_queue_update("removed", "test-123")

        # Should still work with data=None
        mock_async_redis.publish.assert_called_once()
        call_args = mock_async_redis.publish.call_args
        message = json.loads(call_args[0][1])
        assert message["data"]["action"] == "removed"
        assert message["data"]["download_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_publish_system_notification(self, redis_service, mock_async_redis):
        """Test system notification publishing."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.publish = AsyncMock()

        notification_type = "warning"
        message_text = "Storage is running low"
        data = {"available_space_gb": 5.2}

        await redis_service.publish_system_notification(
            notification_type, message_text, data
        )

        # Verify publish was called
        mock_async_redis.publish.assert_called_once()
        call_args = mock_async_redis.publish.call_args

        # Verify correct channel
        assert call_args[0][0] == "system:notifications"

        # Verify message format
        message = json.loads(call_args[0][1])
        assert message["type"] == "system_notification"
        assert message["data"]["notification_type"] == "warning"
        assert message["data"]["message"] == "Storage is running low"
        assert message["data"]["available_space_gb"] == 5.2

    @pytest.mark.asyncio
    async def test_publish_system_notification_without_data(
        self, redis_service, mock_async_redis
    ):
        """Test system notification without additional data."""
        setup_async_redis_mock(redis_service, mock_async_redis)
        mock_async_redis.publish = AsyncMock()

        await redis_service.publish_system_notification("info", "System is healthy")

        # Should work with data=None
        mock_async_redis.publish.assert_called_once()
        call_args = mock_async_redis.publish.call_args
        message = json.loads(call_args[0][1])
        assert message["data"]["notification_type"] == "info"
        assert message["data"]["message"] == "System is healthy"
