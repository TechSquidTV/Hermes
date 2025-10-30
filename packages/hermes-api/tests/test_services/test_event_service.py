"""
Tests for SSE event service and streaming functionality.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def mock_redis_pubsub():
    """Mock Redis pub/sub for SSE event tests."""
    from app.services import redis_progress

    # Create mock Redis pub/sub
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()

    # Mock Redis
    mock_redis = MagicMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    async def mock_get_async_redis():
        return mock_redis

    with patch.object(
        redis_progress.redis_progress_service,
        "get_async_redis",
        side_effect=mock_get_async_redis,
    ):
        yield mock_pubsub, mock_redis


class TestEventServiceConnectionManagement:
    """Test event service connection tracking and limits."""

    @pytest.mark.asyncio
    async def test_tracks_active_connections(self, mock_redis_pubsub):
        """Test that active connections are tracked correctly."""
        from app.services.event_service import event_service

        initial_count = event_service.active_connections
        mock_pubsub, mock_redis = mock_redis_pubsub

        # Mock subscribe_to_channels to yield nothing and then stop
        async def mock_subscribe(channels):
            yield  # Immediate stop
            return

        from app.services import redis_progress

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            # Start event stream
            stream = event_service.event_stream(channels=["download:updates"])

            # Consume first event (should be 'connected')
            try:
                event = await anext(stream)
                assert event["event"] == "connected"

                # Connection count should increase
                assert event_service.active_connections == initial_count + 1
            finally:
                # Cleanup
                await stream.aclose()

        # Connection count should decrease after stream closes
        assert event_service.active_connections == initial_count

    @pytest.mark.asyncio
    async def test_enforces_max_connections_limit(self, mock_redis_pubsub):
        """Test that max connections limit is enforced."""
        from app.services.event_service import event_service

        # Temporarily set max to 1
        original_max = event_service.max_connections
        event_service.max_connections = 1
        event_service.active_connections = 1  # Simulate one active connection

        try:
            # Try to create a new connection when at max
            stream = event_service.event_stream(channels=["download:updates"])

            # First event should be error
            event = await anext(stream)
            assert event["event"] == "error"
            data = json.loads(event["data"])
            assert data["code"] == "MAX_CONNECTIONS"
            assert "Maximum connections reached" in data["error"]

            # Stream should stop immediately
            with pytest.raises(StopAsyncIteration):
                await anext(stream)

        finally:
            # Restore original max
            event_service.max_connections = original_max
            event_service.active_connections = 0

    @pytest.mark.asyncio
    async def test_decrements_connection_on_error(self, mock_redis_pubsub):
        """Test that connection count decrements when stream encounters error."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        initial_count = event_service.active_connections

        # Mock subscribe_to_channels to raise an error
        async def mock_subscribe_error(channels):
            raise Exception("Redis connection failed")
            yield  # Never reached

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe_error,
        ):
            stream = event_service.event_stream(channels=["download:updates"])

            try:
                # Consume connected event
                event = await anext(stream)
                assert event["event"] == "connected"

                # Next event should be error
                event = await anext(stream)
                assert event["event"] == "error"

                # Stream should stop
                with pytest.raises(StopAsyncIteration):
                    await anext(stream)
            finally:
                await stream.aclose()

        # Connection count should be back to initial
        assert event_service.active_connections == initial_count


class TestEventServiceStreaming:
    """Test SSE event streaming functionality."""

    @pytest.mark.asyncio
    async def test_sends_connected_event_on_start(self, mock_redis_pubsub):
        """Test that 'connected' event is sent when stream starts."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe to stop immediately
        async def mock_subscribe(channels):
            return
            yield  # Never reached

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            stream = event_service.event_stream(channels=["download:updates"])

            # First event should be connected
            event = await anext(stream)
            assert event["event"] == "connected"
            data = json.loads(event["data"])
            assert "connection_id" in data
            assert data["connection_id"].startswith("conn_")
            assert "timestamp" in data

            await stream.aclose()

    @pytest.mark.asyncio
    async def test_streams_redis_events(self, mock_redis_pubsub):
        """Test that events from Redis are streamed to client."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe_to_channels to yield test events
        async def mock_subscribe(channels):
            yield {
                "type": "download_progress",
                "data": {
                    "download_id": "test-123",
                    "progress": 50,
                    "status": "downloading",
                },
            }
            yield {
                "type": "queue_update",
                "data": {"queue_size": 5, "active": 2},
            }

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            stream = event_service.event_stream(channels=["download:updates"])

            # Skip connected event
            await anext(stream)

            # First event: download_progress
            event = await anext(stream)
            assert event["event"] == "download_progress"
            data = json.loads(event["data"])
            assert data["download_id"] == "test-123"
            assert data["progress"] == 50

            # Second event: queue_update
            event = await anext(stream)
            assert event["event"] == "queue_update"
            data = json.loads(event["data"])
            assert data["queue_size"] == 5

            await stream.aclose()

    @pytest.mark.asyncio
    async def test_handles_stream_cancellation(self, mock_redis_pubsub):
        """Test that stream handles cancellation gracefully."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe that never stops
        async def mock_subscribe_infinite(channels):
            while True:
                await asyncio.sleep(0.01)
                yield {
                    "type": "heartbeat",
                    "data": {"timestamp": "2025-01-01T00:00:00Z"},
                }

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe_infinite,
        ):
            stream = event_service.event_stream(channels=["download:updates"])

            # Get connected event
            await anext(stream)

            # Cancel the stream
            await stream.aclose()

            # Connection should be cleaned up
            # (tracked by connection count tests)


class TestEventServiceFiltering:
    """Test event filtering functionality."""

    @pytest.mark.asyncio
    async def test_filters_events_by_download_id(self, mock_redis_pubsub):
        """Test that events are filtered by download_id."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe to yield events with different download_ids
        async def mock_subscribe(channels):
            yield {
                "type": "download_progress",
                "data": {"download_id": "test-123", "progress": 50},
            }
            yield {
                "type": "download_progress",
                "data": {"download_id": "test-456", "progress": 75},
            }
            yield {
                "type": "download_progress",
                "data": {"download_id": "test-123", "progress": 100},
            }

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            stream = event_service.event_stream(
                channels=["download:updates"],
                filters={"download_id": "test-123"},
            )

            # Skip connected event
            await anext(stream)

            # First filtered event
            event = await anext(stream)
            data = json.loads(event["data"])
            assert data["download_id"] == "test-123"
            assert data["progress"] == 50

            # Second filtered event (test-456 should be skipped)
            event = await anext(stream)
            data = json.loads(event["data"])
            assert data["download_id"] == "test-123"
            assert data["progress"] == 100

            await stream.aclose()

    @pytest.mark.asyncio
    async def test_filters_with_multiple_criteria(self, mock_redis_pubsub):
        """Test filtering with multiple filter criteria."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe to yield events with various attributes
        async def mock_subscribe(channels):
            yield {
                "type": "download_progress",
                "data": {
                    "download_id": "test-123",
                    "status": "downloading",
                    "progress": 50,
                },
            }
            yield {
                "type": "download_progress",
                "data": {
                    "download_id": "test-123",
                    "status": "completed",
                    "progress": 100,
                },
            }
            yield {
                "type": "download_progress",
                "data": {
                    "download_id": "test-456",
                    "status": "downloading",
                    "progress": 30,
                },
            }

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            stream = event_service.event_stream(
                channels=["download:updates"],
                filters={"download_id": "test-123", "status": "downloading"},
            )

            # Skip connected event
            await anext(stream)

            # Only one event should match both filters
            event = await anext(stream)
            data = json.loads(event["data"])
            assert data["download_id"] == "test-123"
            assert data["status"] == "downloading"

            # No more matching events - stream ends
            with pytest.raises(StopAsyncIteration):
                # Set timeout to prevent hanging
                await asyncio.wait_for(anext(stream), timeout=0.1)

            await stream.aclose()

    @pytest.mark.asyncio
    async def test_no_filters_passes_all_events(self, mock_redis_pubsub):
        """Test that no filters allows all events through."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe to yield various events
        async def mock_subscribe(channels):
            yield {"type": "event1", "data": {"id": 1}}
            yield {"type": "event2", "data": {"id": 2}}
            yield {"type": "event3", "data": {"id": 3}}

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            stream = event_service.event_stream(
                channels=["download:updates"],
                filters=None,  # No filters
            )

            # Skip connected event
            await anext(stream)

            # All events should come through
            event = await anext(stream)
            assert event["event"] == "event1"

            event = await anext(stream)
            assert event["event"] == "event2"

            event = await anext(stream)
            assert event["event"] == "event3"

            await stream.aclose()


class TestEventServiceHeartbeat:
    """Test heartbeat functionality."""

    @pytest.mark.asyncio
    async def test_sends_heartbeat_after_interval(self, mock_redis_pubsub):
        """Test that heartbeats are sent at configured intervals."""
        from app.core import config
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe that yields events quickly to allow heartbeat checks
        async def mock_subscribe_with_events(channels):
            # Yield events at short intervals to allow heartbeat logic to run
            for i in range(20):
                await asyncio.sleep(0.1)  # Short delay between events
                yield {"type": "test_event", "data": {"count": i}}

        # Patch heartbeat interval to be testable
        original_interval = config.settings.sse_heartbeat_interval
        config.settings.sse_heartbeat_interval = 0.5  # 500ms for testing

        try:
            with patch.object(
                redis_progress.redis_progress_service,
                "subscribe_to_channels",
                side_effect=mock_subscribe_with_events,
            ):
                stream = event_service.event_stream(channels=["download:updates"])

                # Skip connected event
                await anext(stream)

                # Collect events until we find a heartbeat
                found_heartbeat = False
                for _ in range(15):  # Check up to 15 events
                    event = await asyncio.wait_for(anext(stream), timeout=5)
                    if event["event"] == "heartbeat":
                        data = json.loads(event["data"])
                        assert "timestamp" in data
                        found_heartbeat = True
                        break

                await stream.aclose()

                # Verify we found a heartbeat
                assert found_heartbeat, "No heartbeat event was sent"
        finally:
            # Restore original interval
            config.settings.sse_heartbeat_interval = original_interval


class TestEventServiceErrorHandling:
    """Test error handling in event service."""

    @pytest.mark.asyncio
    async def test_handles_redis_exception(self, mock_redis_pubsub):
        """Test that Redis exceptions are handled gracefully."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe to raise exception
        async def mock_subscribe_error(channels):
            raise Exception("Redis connection lost")
            yield  # Never reached

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe_error,
        ):
            stream = event_service.event_stream(channels=["download:updates"])

            # Skip connected event
            await anext(stream)

            # Should receive error event
            event = await anext(stream)
            assert event["event"] == "error"
            data = json.loads(event["data"])
            assert "error" in data
            assert data["code"] == "INTERNAL_ERROR"

            await stream.aclose()

    @pytest.mark.asyncio
    async def test_generates_unique_connection_ids(self, mock_redis_pubsub):
        """Test that each connection gets a unique connection_id."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        # Mock subscribe to stop immediately
        async def mock_subscribe(channels):
            return
            yield

        connection_ids = []

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            # Create multiple connections
            for _ in range(3):
                stream = event_service.event_stream(channels=["download:updates"])
                event = await anext(stream)
                data = json.loads(event["data"])
                connection_ids.append(data["connection_id"])
                await stream.aclose()

        # All connection IDs should be unique
        assert len(connection_ids) == len(set(connection_ids))
        # All should start with 'conn_'
        assert all(cid.startswith("conn_") for cid in connection_ids)


class TestEventServiceDataIntegrity:
    """Test data formatting and integrity."""

    @pytest.mark.asyncio
    async def test_data_is_json_serialized(self, mock_redis_pubsub):
        """Test that event data is properly JSON serialized."""
        from app.services.event_service import event_service
        from app.services import redis_progress

        test_data = {
            "download_id": "test-123",
            "progress": 75.5,
            "eta_seconds": 120,
            "nested": {"key": "value"},
        }

        async def mock_subscribe(channels):
            yield {"type": "download_progress", "data": test_data}

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            stream = event_service.event_stream(channels=["download:updates"])

            # Skip connected event
            await anext(stream)

            # Get data event
            event = await anext(stream)
            assert isinstance(event["data"], str)  # Should be JSON string

            # Should be parseable
            parsed = json.loads(event["data"])
            assert parsed == test_data

            await stream.aclose()
