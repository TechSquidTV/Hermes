"""
Redis service for storing ephemeral download progress data.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

import redis
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisProgressService:
    """Service for managing download progress in Redis."""

    def __init__(self):
        self._async_redis: Optional[aioredis.Redis] = None
        self._async_redis_loop: Optional[Any] = None
        self._sync_redis: Optional[redis.Redis] = None

    async def get_async_redis(self) -> aioredis.Redis:
        """Get or create async Redis connection for the current event loop."""

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        # Create new connection if:
        # 1. No connection exists yet
        # 2. The connection was created in a different event loop
        # 3. The connection is closed
        if (
            self._async_redis is None
            or self._async_redis_loop != current_loop
            or self._async_redis.connection_pool is None
        ):
            self._async_redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            self._async_redis_loop = current_loop

        return self._async_redis

    def get_sync_redis(self) -> redis.Redis:
        """Get or create sync Redis connection."""
        if self._sync_redis is None:
            self._sync_redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._sync_redis

    def set_progress_sync(
        self,
        download_id: str,
        progress_data: Dict[str, Any],
        ttl: int = 3600,  # 1 hour default
    ) -> None:
        """
        Store download progress in Redis with TTL (synchronous).
        Use this from sync contexts like progress hooks.

        Args:
            download_id: Download ID
            progress_data: Progress information dictionary
            ttl: Time to live in seconds (default 1 hour)
        """
        try:
            r = self.get_sync_redis()
            key = f"download:{download_id}:progress"
            r.setex(key, ttl, json.dumps(progress_data))
        except Exception as e:
            logger.error(
                "Failed to set progress in Redis",
                download_id=download_id,
                error=str(e),
            )

    async def get_progress(self, download_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve download progress from Redis (async).

        Args:
            download_id: Download ID

        Returns:
            Progress data dictionary or None if not found
        """
        try:
            r = await self.get_async_redis()
            key = f"download:{download_id}:progress"
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(
                "Failed to get progress from Redis",
                download_id=download_id,
                error=str(e),
            )
            return None

    async def delete_progress(self, download_id: str) -> None:
        """
        Delete progress data from Redis (async).

        Args:
            download_id: Download ID
        """
        try:
            r = await self.get_async_redis()
            key = f"download:{download_id}:progress"
            await r.delete(key)
        except Exception as e:
            logger.error(
                "Failed to delete progress from Redis",
                download_id=download_id,
                error=str(e),
            )

    def delete_progress_sync(self, download_id: str) -> None:
        """
        Delete progress data from Redis (synchronous).
        Use this from sync contexts.

        Args:
            download_id: Download ID
        """
        try:
            r = self.get_sync_redis()
            key = f"download:{download_id}:progress"
            r.delete(key)
        except Exception as e:
            logger.error(
                "Failed to delete progress from Redis",
                download_id=download_id,
                error=str(e),
            )

    # ============================================================
    # PUB/SUB METHODS FOR SSE
    # ============================================================

    def _serialize_data(
        self, data: Dict[str, Any], depth: int = 0, max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Serialize data for JSON encoding, converting datetime objects to ISO strings.

        Args:
            data: Data dictionary to serialize
            depth: Current recursion depth (internal use)
            max_depth: Maximum recursion depth to prevent stack overflow

        Returns:
            Serialized data dictionary

        Raises:
            ValueError: If max recursion depth is exceeded
        """
        if depth > max_depth:
            raise ValueError(
                f"Max recursion depth ({max_depth}) exceeded in _serialize_data"
            )

        serialized = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_data(value, depth + 1, max_depth)
            else:
                serialized[key] = value
        return serialized

    async def publish_event(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Publish an event to a Redis pub/sub channel.

        Args:
            channel: Redis channel name (e.g., 'download:updates')
            event_type: Event type identifier (e.g., 'progress_update')
            data: Event data to publish
        """
        try:
            r = await self.get_async_redis()
            # Serialize datetime objects before JSON encoding
            serialized_data = self._serialize_data(data)
            message = json.dumps(
                {
                    "type": event_type,
                    "data": serialized_data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            await r.publish(channel, message)
            logger.debug(
                f"Published event to {channel}", event_type=event_type, channel=channel
            )
        except Exception as e:
            logger.error(
                "Failed to publish event to Redis",
                channel=channel,
                event_type=event_type,
                error=str(e),
            )

    async def subscribe_to_channels(
        self, channels: List[str]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Subscribe to Redis pub/sub channels and yield messages.

        Args:
            channels: List of channel names to subscribe to

        Yields:
            Dict with 'channel', 'type', 'data', and 'timestamp'
        """
        r = await self.get_async_redis()
        pubsub = r.pubsub()

        try:
            # Subscribe to all specified channels
            await pubsub.subscribe(*channels)
            logger.info(f"Subscribed to channels: {', '.join(channels)}")

            # Listen for messages
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield {
                            "channel": message["channel"],
                            "type": data.get("type"),
                            "data": data.get("data"),
                            "timestamp": data.get("timestamp"),
                        }
                    except json.JSONDecodeError as e:
                        logger.error(
                            "Failed to decode pub/sub message",
                            error=str(e),
                            message=message["data"],
                        )
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
            logger.info(f"Unsubscribed from channels: {', '.join(channels)}")

    async def publish_download_progress(
        self, download_id: str, progress_data: Dict[str, Any]
    ) -> None:
        """
        Publish download progress update to Redis pub/sub.

        Args:
            download_id: Download ID
            progress_data: Progress information
        """
        await self.publish_event(
            channel="download:updates",
            event_type="download_progress",
            data={"download_id": download_id, **progress_data},
        )

    async def publish_queue_update(
        self, action: str, download_id: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publish queue update to Redis pub/sub.

        Args:
            action: Action type ('added', 'removed', 'status_changed')
            download_id: Download ID
            data: Additional data
        """
        await self.publish_event(
            channel="queue:updates",
            event_type="queue_update",
            data={"action": action, "download_id": download_id, **(data or {})},
        )

    async def publish_system_notification(
        self,
        notification_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Publish system notification to Redis pub/sub.

        Args:
            notification_type: Type of notification ('info', 'warning', 'error')
            message: Notification message
            data: Additional data
        """
        await self.publish_event(
            channel="system:notifications",
            event_type="system_notification",
            data={
                "notification_type": notification_type,
                "message": message,
                **(data or {}),
            },
        )

    async def close(self) -> None:
        """Close Redis connections."""
        if self._async_redis:
            await self._async_redis.close()
        if self._sync_redis:
            self._sync_redis.close()


# Global instance
redis_progress_service = RedisProgressService()
