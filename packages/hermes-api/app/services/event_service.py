"""
Event service for managing SSE connections and message distribution.
"""

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.redis_progress import redis_progress_service

logger = get_logger(__name__)


class EventService:
    """Service for managing SSE events and connections."""

    def __init__(self) -> None:
        self.active_connections: int = 0
        self.max_connections: int = settings.sse_max_connections

    async def event_stream(
        self,
        channels: list[str],
        filters: Optional[Dict[str, Any]] = None,
        authorize: Callable[[], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate SSE event stream.

        Args:
            channels: List of Redis channels to subscribe to
            filters: Optional filters to apply to events

        Yields:
            SSE event dictionaries
        """
        if self.active_connections >= self.max_connections:
            logger.warning(
                "Max SSE connections reached",
                active=self.active_connections,
                max=self.max_connections,
            )
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "error": "Maximum connections reached",
                        "code": "MAX_CONNECTIONS",
                    }
                ),
            }
            return

        self.active_connections += 1
        connection_id = f"conn_{uuid.uuid4()}"

        logger.info(
            "New SSE connection",
            connection_id=connection_id,
            channels=channels,
            active_connections=self.active_connections,
        )

        try:
            if authorize:
                await authorize()
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps(
                    {
                        "connection_id": connection_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            }

            # Track last heartbeat time
            last_heartbeat = asyncio.get_event_loop().time()

            # Subscribe to Redis channels
            async for event in self._events(channels, authorize):
                # Send heartbeat if interval has elapsed
                current_time = asyncio.get_event_loop().time()
                if current_time - last_heartbeat >= settings.sse_heartbeat_interval:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps(
                            {"timestamp": datetime.now(timezone.utc).isoformat()}
                        ),
                    }
                    last_heartbeat = current_time

                # Apply filters if specified
                if filters and not self._matches_filters(event, filters):
                    continue

                # Format as SSE event - data must be JSON string for sse-starlette
                yield {"event": event["type"], "data": json.dumps(event["data"])}

        except asyncio.CancelledError:
            logger.info("SSE connection cancelled", connection_id=connection_id)
        except Exception as e:
            logger.error(
                "Error in SSE event stream",
                connection_id=connection_id,
                error=str(e),
                exc_info=True,
            )
            yield {
                "event": "error",
                "data": json.dumps(
                    {"error": "Internal server error", "code": "INTERNAL_ERROR"}
                ),
            }
        finally:
            self.active_connections -= 1
            logger.info(
                "SSE connection closed",
                connection_id=connection_id,
                active_connections=self.active_connections,
            )

    async def _events(
        self, channels: list[str], authorize: Callable[[], Awaitable[None]] | None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        events = redis_progress_service.subscribe_to_channels(channels)
        pending: asyncio.Task[Dict[str, Any]] | None = None
        last_check = asyncio.get_running_loop().time()
        try:
            while True:
                if pending is None:
                    pending = asyncio.create_task(anext(events))
                done, _ = await asyncio.wait({pending}, timeout=1.0)
                now = asyncio.get_running_loop().time()
                if authorize and now - last_check >= 1.0:
                    await authorize()
                    last_check = now
                if done:
                    try:
                        event = pending.result()
                    except StopAsyncIteration:
                        return
                    pending = None
                    yield event
        finally:
            if pending is not None:
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            await events.aclose()

    def _matches_filters(self, event: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if event matches specified filters.

        Args:
            event: Event to check
            filters: Filters to apply

        Returns:
            True if event matches all filters
        """
        for key, value in filters.items():
            if key not in event.get("data", {}):
                return False
            if event["data"][key] != value:
                return False
        return True


# Global instance
event_service = EventService()
