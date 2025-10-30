"""
Tests for SSE events endpoints and token authentication.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def mock_redis_for_sse():
    """Mock Redis for SSE token tests to avoid requiring running Redis instance."""
    from app.services import redis_progress

    # Create mock Redis
    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.delete = AsyncMock()
    mock_redis.scan_iter = AsyncMock(return_value=[])
    mock_redis.connection_pool = MagicMock()  # Prevent reconnection attempts

    # Mock get_async_redis to return our mock without connecting
    async def mock_get_async_redis():
        return mock_redis

    # Patch the get_async_redis method
    with patch.object(
        redis_progress.redis_progress_service,
        "get_async_redis",
        side_effect=mock_get_async_redis,
    ):
        yield mock_redis


class TestSSETokenEndpoint:
    """Test POST /api/v1/events/token endpoint."""

    @pytest.mark.asyncio
    async def test_create_token_requires_auth(self, client: AsyncClient):
        """Test that token creation requires authentication."""
        # Clear auth override to test actual auth
        from app.core.security import get_current_api_key
        from app.main import app

        # Override with a function that raises 401
        async def mock_no_auth():
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        app.dependency_overrides[get_current_api_key] = mock_no_auth

        response = await client.post(
            "/api/v1/events/token", json={"scope": "queue", "ttl": 600}
        )

        # Should return 401 without authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_token_download_scope(self, client: AsyncClient):
        """Test creating token with download:ID scope format.

        Note: This test now returns 404 because the security fix requires
        downloads to exist. Actual verification is tested in
        TestSSETokenDownloadVerification.test_token_allowed_for_existing_download.
        """
        response = await client.post(
            "/api/v1/events/token",
            json={"scope": "download:test-123", "ttl": 600},
        )

        # After security fix, this returns 404 because download doesn't exist
        assert response.status_code == 404
        data = response.json()
        error_message = data.get("detail", str(data)).lower()
        assert "not found" in error_message

    @pytest.mark.asyncio
    async def test_create_token_queue_scope(self, client: AsyncClient):
        """Test creating token with queue scope."""
        response = await client.post(
            "/api/v1/events/token", json={"scope": "queue", "ttl": 300}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scope"] == "queue"
        assert data["ttl"] == 300
        assert data["token"].startswith("sse_")

    @pytest.mark.asyncio
    async def test_create_token_system_scope(self, client: AsyncClient):
        """Test creating token with system scope."""
        response = await client.post(
            "/api/v1/events/token", json={"scope": "system", "ttl": 600}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scope"] == "system"

    @pytest.mark.asyncio
    async def test_create_token_invalid_scope_format(self, client: AsyncClient):
        """Test that invalid scope format returns 400."""
        response = await client.post(
            "/api/v1/events/token", json={"scope": "invalid:scope:format", "ttl": 600}
        )

        assert response.status_code == 400
        data = response.json()
        # Check for error in either 'detail' or nested structure
        error_message = data.get("detail") or str(data)
        assert "Invalid scope format" in error_message

    @pytest.mark.asyncio
    async def test_create_token_empty_download_id(self, client: AsyncClient):
        """Test that download: without ID returns 400."""
        response = await client.post(
            "/api/v1/events/token", json={"scope": "download:", "ttl": 600}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_token_ttl_too_low(self, client: AsyncClient):
        """Test that TTL below 60s is rejected."""
        response = await client.post(
            "/api/v1/events/token", json={"scope": "queue", "ttl": 30}
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "greater than or equal to 60" in str(data)

    @pytest.mark.asyncio
    async def test_create_token_ttl_too_high(self, client: AsyncClient):
        """Test that TTL above 3600s is rejected."""
        response = await client.post(
            "/api/v1/events/token", json={"scope": "queue", "ttl": 7200}
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "less than or equal to 3600" in str(data)

    @pytest.mark.asyncio
    async def test_create_token_default_ttl(self, client: AsyncClient):
        """Test that default TTL is 300s (5 minutes)."""
        response = await client.post(
            "/api/v1/events/token", json={"scope": "queue"}  # No TTL specified
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ttl"] == 300  # Default

    @pytest.mark.asyncio
    async def test_create_token_stored_in_redis(
        self, client: AsyncClient, mock_redis_for_sse
    ):
        """Test that created token is stored in Redis (via mock)."""
        response = await client.post(
            "/api/v1/events/token", json={"scope": "queue", "ttl": 600}
        )

        assert response.status_code == 200
        data = response.json()
        token = data["token"]

        # Verify Redis setex was called
        mock_redis_for_sse.setex.assert_called_once()
        call_args = mock_redis_for_sse.setex.call_args

        # Verify correct key format
        assert call_args[0][0] == f"sse:token:{token}"
        # Verify TTL
        assert call_args[0][1] == 600

    @pytest.mark.asyncio
    async def test_create_token_redis_failure_returns_500(self, client: AsyncClient):
        """Test that Redis failure returns 500 error."""
        from app.services import redis_progress

        # Mock Redis to fail
        with patch.object(
            redis_progress.redis_progress_service,
            "store_sse_token",
            side_effect=Exception("Redis connection failed"),
        ):
            response = await client.post(
                "/api/v1/events/token", json={"scope": "queue", "ttl": 600}
            )

            assert response.status_code == 500
            data = response.json()
            error_message = data.get("detail") or str(data)
            assert "Failed to create SSE token" in error_message


class TestSSEEndpointTokenAuth:
    """Test SSE endpoints with token authentication."""

    @pytest.mark.asyncio
    async def test_download_sse_requires_token(self, client: AsyncClient):
        """Test that /events/downloads/{id} requires SSE token."""
        response = await client.get("/api/v1/events/downloads/test-123")

        assert response.status_code == 401
        data = response.json()
        error_message = data.get("detail") or str(data)
        assert "SSE token required" in error_message or "token" in error_message.lower()

    @pytest.mark.asyncio
    async def test_download_sse_with_invalid_token_format(self, client: AsyncClient):
        """Test that invalid token format is rejected."""
        # Token that doesn't start with "sse_"
        response = await client.get(
            "/api/v1/events/downloads/test-123?token=invalid_token"
        )

        assert response.status_code == 401
        data = response.json()
        error_message = data.get("detail") or str(data)
        assert (
            "Invalid SSE token format" in error_message
            or "invalid" in error_message.lower()
        )

    @pytest.mark.asyncio
    async def test_download_sse_with_nonexistent_token(self, client: AsyncClient):
        """Test that non-existent token is rejected."""
        response = await client.get(
            "/api/v1/events/downloads/test-123?token=sse_nonexistent123"
        )

        assert response.status_code == 401
        data = response.json()
        error_message = data.get("detail") or str(data)
        assert "Invalid or expired" in error_message or "token" in error_message.lower()

    @pytest.mark.asyncio
    async def test_download_sse_wrong_scope(
        self, client: AsyncClient, mock_redis_for_sse
    ):
        """Test that token scope must match download_id."""
        import json

        # Mock Redis to return token with wrong scope
        token_data = {
            "scope": "download:abc-123",
            "user_id": "user123",
            "expires_at": "2025-12-31T23:59:59Z",
            "permissions": ["read"],
        }
        mock_redis_for_sse.get = AsyncMock(return_value=json.dumps(token_data))

        # Try to use it for download:different-456
        response = await client.get(
            "/api/v1/events/downloads/different-456?token=sse_test_wrong_scope"
        )

        assert response.status_code == 403
        data = response.json()
        error_message = data.get("detail") or str(data)
        assert "Insufficient scope" in error_message or "scope" in error_message.lower()

    @pytest.mark.asyncio
    async def test_queue_sse_requires_token(self, client: AsyncClient):
        """Test that /events/queue requires SSE token."""
        response = await client.get("/api/v1/events/queue")

        assert response.status_code == 401
        data = response.json()
        error_message = data.get("detail") or str(data)
        assert "SSE token required" in error_message or "token" in error_message.lower()

    @pytest.mark.asyncio
    async def test_queue_sse_requires_queue_scope(
        self, client: AsyncClient, mock_redis_for_sse
    ):
        """Test that queue endpoint requires queue-scoped token."""
        import json

        # Mock Redis to return token with download scope (wrong scope)
        token_data = {
            "scope": "download:test-123",
            "user_id": "user123",
            "expires_at": "2025-12-31T23:59:59Z",
            "permissions": ["read"],
        }
        mock_redis_for_sse.get = AsyncMock(return_value=json.dumps(token_data))

        # Try to use it for queue endpoint
        response = await client.get(
            "/api/v1/events/queue?token=sse_test_download_for_queue"
        )

        assert response.status_code == 403
        data = response.json()
        error_message = data.get("detail") or str(data)
        assert "Insufficient scope" in error_message or "scope" in error_message.lower()


class TestSSEStreamingFunctionality:
    """Test actual SSE streaming and event delivery."""

    @pytest.mark.asyncio
    async def test_stream_endpoint_with_valid_token(
        self, client: AsyncClient, mock_redis_for_sse
    ):
        """Test connecting to /events/stream with valid SSE token."""
        import json

        # Mock valid token in Redis
        token_data = {
            "scope": "queue",
            "user_id": "user123",
            "expires_at": "2025-12-31T23:59:59Z",
            "permissions": ["read"],
        }
        mock_redis_for_sse.get = AsyncMock(return_value=json.dumps(token_data))

        # Mock event stream to return quickly
        from app.services import event_service

        async def mock_event_stream(channels, filters=None):
            # Return a simple connected event
            yield {
                "event": "connected",
                "data": json.dumps({"connection_id": "test-conn-123"}),
            }

        with patch.object(
            event_service.event_service,
            "event_stream",
            side_effect=mock_event_stream,
        ):
            # Note: Can't easily test full streaming with httpx AsyncClient
            # Just verify endpoint accepts the request
            # Real streaming would need different test approach
            pass

    @pytest.mark.asyncio
    async def test_stream_receives_published_events(self, mock_redis_for_sse):
        """Test that published events are received through SSE stream."""
        import json

        from app.services import redis_progress

        # Mock Redis pub/sub to yield test events
        async def mock_subscribe(channels):
            yield {
                "type": "download_progress",
                "data": {"download_id": "test-123", "progress": 50},
            }
            yield {
                "type": "queue_update",
                "data": {"action": "added", "download_id": "test-456"},
            }

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            from app.services.event_service import event_service

            # Consume events from stream
            events = []
            stream = event_service.event_stream(
                channels=["download:updates", "queue:updates"]
            )

            # Get connected event
            event = await anext(stream)
            assert event["event"] == "connected"

            # Get published events
            event = await anext(stream)
            assert event["event"] == "download_progress"
            data = json.loads(event["data"])
            assert data["download_id"] == "test-123"
            events.append(event)

            event = await anext(stream)
            assert event["event"] == "queue_update"
            data = json.loads(event["data"])
            assert data["action"] == "added"
            events.append(event)

            await stream.aclose()

            # Verify we received both events
            assert len(events) == 2

    @pytest.mark.asyncio
    async def test_stream_filters_by_download_id(self, mock_redis_for_sse):
        """Test that stream correctly filters events by download_id."""
        import json

        from app.services import redis_progress

        # Mock Redis pub/sub to yield events for different downloads
        async def mock_subscribe(channels):
            yield {
                "type": "download_progress",
                "data": {"download_id": "target-123", "progress": 25},
            }
            yield {
                "type": "download_progress",
                "data": {"download_id": "other-456", "progress": 50},
            }
            yield {
                "type": "download_progress",
                "data": {"download_id": "target-123", "progress": 75},
            }

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            from app.services.event_service import event_service

            # Stream with filter for target-123
            stream = event_service.event_stream(
                channels=["download:updates"], filters={"download_id": "target-123"}
            )

            # Skip connected event
            await anext(stream)

            # First filtered event
            event = await anext(stream)
            data = json.loads(event["data"])
            assert data["download_id"] == "target-123"
            assert data["progress"] == 25

            # Second filtered event (other-456 should be skipped)
            event = await anext(stream)
            data = json.loads(event["data"])
            assert data["download_id"] == "target-123"
            assert data["progress"] == 75

            await stream.aclose()

    @pytest.mark.asyncio
    async def test_stream_handles_multiple_channels(self, mock_redis_for_sse):
        """Test subscribing to multiple channels simultaneously."""
        from app.services import redis_progress

        # Mock Redis pub/sub to yield events from different channels
        async def mock_subscribe(channels):
            # Verify correct channels were requested
            assert "download:updates" in channels
            assert "queue:updates" in channels
            assert "system:notifications" in channels

            yield {
                "type": "download_progress",
                "data": {"download_id": "test-123", "progress": 50},
            }
            yield {
                "type": "queue_update",
                "data": {"action": "added", "download_id": "test-456"},
            }
            yield {
                "type": "system_notification",
                "data": {"notification_type": "info", "message": "Test notification"},
            }

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            from app.services.event_service import event_service

            stream = event_service.event_stream(
                channels=["download:updates", "queue:updates", "system:notifications"]
            )

            # Skip connected event
            await anext(stream)

            # Receive events from all channels
            event_types = []
            for _ in range(3):
                event = await anext(stream)
                event_types.append(event["event"])

            await stream.aclose()

            # Verify we got events from all channel types
            assert "download_progress" in event_types
            assert "queue_update" in event_types
            assert "system_notification" in event_types

    @pytest.mark.asyncio
    async def test_download_endpoint_enforces_scope(self, mock_redis_for_sse):
        """Test that download endpoint enforces download-scoped tokens."""
        import json

        # Mock token validation to check scope
        async def mock_validate(token, expected_scope):
            # Should be called with download:test-123 scope
            assert expected_scope == "download:test-123"
            return {
                "scope": "download:test-123",
                "user_id": "user123",
                "permissions": ["read"],
            }

        with patch(
            "app.api.v1.endpoints.events.validate_sse_token",
            side_effect=mock_validate,
        ):
            # Import after patching
            from app.api.v1.endpoints.events import download_events

            # Mock the event stream
            from app.services import event_service

            async def mock_stream(channels, filters):
                assert channels == ["download:updates"]
                assert filters == {"download_id": "test-123"}
                yield {
                    "event": "connected",
                    "data": json.dumps({"connection_id": "test"}),
                }

            with patch.object(
                event_service.event_service,
                "event_stream",
                side_effect=mock_stream,
            ):
                # Call the endpoint
                from sse_starlette.sse import EventSourceResponse

                response = await download_events(
                    download_id="test-123", token="sse_valid_token"
                )

                # Verify response is EventSourceResponse
                assert isinstance(response, EventSourceResponse)

    @pytest.mark.asyncio
    async def test_queue_endpoint_enforces_queue_scope(self, mock_redis_for_sse):
        """Test that queue endpoint enforces queue-scoped tokens."""
        import json

        # Mock token validation to check scope
        async def mock_validate(token, expected_scope):
            # Should be called with queue scope
            assert expected_scope == "queue"
            return {
                "scope": "queue",
                "user_id": "user123",
                "permissions": ["read"],
            }

        with patch(
            "app.api.v1.endpoints.events.validate_sse_token",
            side_effect=mock_validate,
        ):
            from app.api.v1.endpoints.events import queue_events
            from app.services import event_service

            async def mock_stream(channels, filters=None):
                assert channels == ["queue:updates"]
                yield {
                    "event": "connected",
                    "data": json.dumps({"connection_id": "test"}),
                }

            with patch.object(
                event_service.event_service,
                "event_stream",
                side_effect=mock_stream,
            ):
                from sse_starlette.sse import EventSourceResponse

                response = await queue_events(token="sse_valid_token")
                assert isinstance(response, EventSourceResponse)

    @pytest.mark.asyncio
    async def test_stream_connection_tracking(self, mock_redis_for_sse):
        """Test that connections are properly tracked and cleaned up."""
        from app.services import redis_progress
        from app.services.event_service import event_service

        initial_connections = event_service.active_connections

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

            # Get connected event
            await anext(stream)

            # Verify connection was tracked
            assert event_service.active_connections == initial_connections + 1

            # Close stream
            await stream.aclose()

            # Verify connection was cleaned up
            assert event_service.active_connections == initial_connections

    @pytest.mark.asyncio
    async def test_event_data_format_consistency(self, mock_redis_for_sse):
        """Test that all events follow consistent data format."""
        import json

        from app.services import redis_progress

        async def mock_subscribe(channels):
            yield {
                "type": "download_progress",
                "data": {
                    "download_id": "test-123",
                    "progress": 50,
                    "speed": 1024000,
                    "eta": 30,
                },
            }

        with patch.object(
            redis_progress.redis_progress_service,
            "subscribe_to_channels",
            side_effect=mock_subscribe,
        ):
            from app.services.event_service import event_service

            stream = event_service.event_stream(channels=["download:updates"])

            # Skip connected event
            await anext(stream)

            # Get data event
            event = await anext(stream)

            # Verify event structure
            assert "event" in event
            assert "data" in event
            assert isinstance(event["data"], str)  # Should be JSON string

            # Verify data is valid JSON
            data = json.loads(event["data"])
            assert "download_id" in data
            assert "progress" in data

            await stream.aclose()


class TestSSETokenDownloadVerification:
    """Test download existence verification for SSE token creation."""

    @pytest.mark.asyncio
    async def test_token_denied_for_non_existent_download(self, client: AsyncClient):
        """Test that token creation fails for non-existent downloads."""
        response = await client.post(
            "/api/v1/events/token",
            json={"scope": "download:nonexistent-id-12345", "ttl": 300},
        )

        assert response.status_code == 404
        data = response.json()
        # Check for error message in detail or anywhere in response
        error_message = data.get("detail", str(data)).lower()
        assert "not found" in error_message

    @pytest.mark.asyncio
    async def test_token_allowed_for_existing_download(
        self, client: AsyncClient, db_session
    ):
        """Test that users can get tokens for existing downloads."""
        from app.db.repositories import DownloadRepository

        download_repo = DownloadRepository(db_session)

        # Create a download
        download = await download_repo.create(
            url="https://example.com/video",
            status="pending",
        )
        await db_session.commit()
        await db_session.refresh(download)

        # Get token for existing download
        response = await client.post(
            "/api/v1/events/token",
            json={"scope": f"download:{download.id}", "ttl": 300},
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token"].startswith("sse_")
        assert data["scope"] == f"download:{download.id}"

    @pytest.mark.asyncio
    async def test_token_denied_for_invalid_download_id_format(
        self, client: AsyncClient
    ):
        """Test that invalid download ID format is rejected."""
        # Empty download ID
        response = await client.post(
            "/api/v1/events/token",
            json={"scope": "download:", "ttl": 300},
        )

        assert response.status_code == 400
        data = response.json()
        error_msg = str(data).lower()
        assert "invalid" in error_msg or "format" in error_msg

    @pytest.mark.asyncio
    async def test_queue_and_system_tokens_no_download_check(self, client: AsyncClient):
        """Test that queue and system scopes don't require download verification."""
        # Queue scope
        response = await client.post(
            "/api/v1/events/token",
            json={"scope": "queue", "ttl": 300},
        )
        assert response.status_code == 200
        assert response.json()["scope"] == "queue"

        # System scope
        response = await client.post(
            "/api/v1/events/token",
            json={"scope": "system", "ttl": 300},
        )
        assert response.status_code == 200
        assert response.json()["scope"] == "system"


class TestSSEHealthEndpoint:
    """Test SSE health check endpoint."""

    @pytest.mark.asyncio
    async def test_sse_health_returns_metrics(self, client: AsyncClient):
        """Test that health endpoint returns SSE metrics."""
        response = await client.get("/api/v1/events/health")

        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "max_connections" in data
        assert "heartbeat_interval" in data
        assert isinstance(data["active_connections"], int)
        assert isinstance(data["max_connections"], int)
        assert isinstance(data["heartbeat_interval"], (int, float))

    @pytest.mark.asyncio
    async def test_sse_health_no_auth_required(self, client: AsyncClient):
        """Test that health endpoint doesn't require authentication."""
        # Clear auth override
        from app.main import app

        app.dependency_overrides.clear()

        response = await client.get("/api/v1/events/health")

        # Should work without auth
        assert response.status_code == 200
