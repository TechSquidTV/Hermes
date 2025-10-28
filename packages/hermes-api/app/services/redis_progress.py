"""
Redis service for storing ephemeral download progress data.
"""

import json
from typing import Any, Dict, Optional

import redis
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisProgressService:
    """Service for managing download progress in Redis."""

    def __init__(self):
        self._async_redis: Optional[aioredis.Redis] = None
        self._sync_redis: Optional[redis.Redis] = None

    async def get_async_redis(self) -> aioredis.Redis:
        """Get or create async Redis connection."""
        if self._async_redis is None:
            self._async_redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
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

    async def close(self) -> None:
        """Close Redis connections."""
        if self._async_redis:
            await self._async_redis.close()
        if self._sync_redis:
            self._sync_redis.close()


# Global instance
redis_progress_service = RedisProgressService()
