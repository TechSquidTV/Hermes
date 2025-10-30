"""
Server-Sent Events (SSE) endpoints for real-time updates.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sse_starlette.sse import EventSourceResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_current_api_key_optional
from app.services.event_service import event_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/stream")
async def event_stream(
    channels: Optional[str] = Query(
        None,
        description="Comma-separated list of channels (download:updates,queue:updates,system:notifications)",
    ),
    download_id: Optional[str] = Query(
        None, description="Filter to specific download ID"
    ),
    api_key: Optional[str] = Depends(get_current_api_key_optional),
):
    """
    SSE endpoint for real-time updates.

    Streams events from Redis pub/sub channels to connected clients.
    Automatically reconnects on disconnect with Last-Event-ID support.

    **Authentication:**
    Since EventSource cannot send custom headers, pass token as query param:
    `/api/v1/events/stream?token=YOUR_TOKEN`

    **Channels:**
    - `download:updates` - Download progress updates
    - `queue:updates` - Queue status changes
    - `system:notifications` - System-wide notifications

    **Example:**
    ```javascript
    const token = getAuthToken(); // Your JWT token
    const eventSource = new EventSource(
      `/api/v1/events/stream?token=${token}&channels=download:updates,queue:updates`
    );

    eventSource.addEventListener('download_progress', (event) => {
      const data = JSON.parse(event.data);
      console.log('Download progress:', data);
    });
    ```
    """
    # Check authentication
    if not api_key:
        logger.warning("SSE connection attempted without authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Parse channels
    channel_list = []
    if channels:
        channel_list = [c.strip() for c in channels.split(",")]
    else:
        # Default to all channels
        channel_list = ["download:updates", "queue:updates", "system:notifications"]

    # Build filters
    filters = {}
    if download_id:
        filters["download_id"] = download_id

    # Create event stream
    return EventSourceResponse(
        event_service.event_stream(
            channels=channel_list, filters=filters if filters else None
        )
    )


@router.get("/downloads/{download_id}")
async def download_events(
    download_id: str,
    api_key: Optional[str] = Depends(get_current_api_key_optional),
):
    """
    SSE endpoint for a specific download's events.

    Streams only events related to the specified download ID.

    **Authentication:**
    Pass token as query param: `/api/v1/events/downloads/${downloadId}?token=YOUR_TOKEN`

    **Example:**
    ```javascript
    const token = getAuthToken();
    const eventSource = new EventSource(
      `/api/v1/events/downloads/${downloadId}?token=${token}`
    );

    eventSource.addEventListener('download_progress', (event) => {
      const data = JSON.parse(event.data);
      updateProgressBar(data.progress);
    });
    ```
    """
    # Check authentication
    if not api_key:
        logger.warning(
            f"SSE connection attempted without authentication for download {download_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return EventSourceResponse(
        event_service.event_stream(
            channels=["download:updates"], filters={"download_id": download_id}
        )
    )


@router.get("/queue")
async def queue_events(
    api_key: Optional[str] = Depends(get_current_api_key_optional),
):
    """
    SSE endpoint for queue updates.

    Streams queue-related events (additions, removals, status changes).

    **Authentication:**
    Pass token as query param: `/api/v1/events/queue?token=YOUR_TOKEN`

    **Example:**
    ```javascript
    const token = getAuthToken();
    const eventSource = new EventSource(`/api/v1/events/queue?token=${token}`);

    eventSource.addEventListener('queue_update', (event) => {
      const data = JSON.parse(event.data);
      refreshQueue();
    });
    ```
    """
    # Check authentication
    if not api_key:
        logger.warning("SSE connection attempted without authentication for queue")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return EventSourceResponse(event_service.event_stream(channels=["queue:updates"]))


@router.get("/health")
async def sse_health():
    """
    Health check endpoint for SSE service.

    Returns current SSE connection metrics.

    Note: If this endpoint responds, SSE is operational.
    SSE is a core requirement and cannot be disabled.
    """
    return {
        "active_connections": event_service.active_connections,
        "max_connections": event_service.max_connections,
        "heartbeat_interval": settings.sse_heartbeat_interval,
    }
