"""
Server-Sent Events (SSE) endpoints for real-time updates.
"""

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    get_current_api_key,
    get_current_sse_token,
    validate_sse_token,
)
from app.db.repositories import DownloadRepository
from app.db.session import get_database_session
from app.models import (
    CreateSSETokenRequest,
    SSETokenResponse,
    generate_sse_token,
)
from app.services.event_service import event_service
from app.services.redis_progress import redis_progress_service

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
    token_data: dict = Depends(get_current_sse_token),
):
    """
    SSE endpoint for real-time updates.

    Streams events from Redis pub/sub channels to connected clients.
    Automatically reconnects on disconnect with Last-Event-ID support.

    **Authentication:**
    Requires ephemeral SSE token from POST /api/v1/events/token.
    Pass token as query param: `/api/v1/events/stream?token=SSE_TOKEN`

    **Security:**
    - SSE token is ephemeral (5-60 minutes TTL)
    - Scoped to specific resources
    - Read-only permissions
    - Automatically expires

    **Channels:**
    - `download:updates` - Download progress updates
    - `queue:updates` - Queue status changes
    - `system:notifications` - System-wide notifications

    **Example:**
    ```javascript
    // Step 1: Get SSE token (secure - uses main JWT in header)
    const { token } = await fetch('/api/v1/events/token', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${mainJWT}` },
      body: JSON.stringify({ scope: 'queue', ttl: 600 })
    }).then(r => r.json());

    // Step 2: Connect with SSE token
    const eventSource = new EventSource(
      `/api/v1/events/stream?token=${token}&channels=download:updates,queue:updates`
    );

    eventSource.addEventListener('download_progress', (event) => {
      const data = JSON.parse(event.data);
      console.log('Download progress:', data);
    });
    ```
    """
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

    # Validate token scope for requested channels
    token_scope = token_data.get("scope", "")

    # If token is scoped to a specific download, only allow download updates for that download
    if token_scope.startswith("download:"):
        download_id_from_scope = token_scope.split(":", 1)[1]
        channel_list = ["download:updates"]
        filters["download_id"] = download_id_from_scope
        logger.info(
            "SSE stream scoped to download",
            download_id=download_id_from_scope,
            user_id=token_data.get("user_id"),
        )
    elif token_scope == "queue":
        # Queue-scoped token can only access queue updates
        channel_list = ["queue:updates"]
        logger.info(
            "SSE stream scoped to queue",
            user_id=token_data.get("user_id"),
        )
    elif token_scope == "system":
        # System-scoped token can access system notifications
        channel_list = ["system:notifications"]
        logger.info(
            "SSE stream scoped to system",
            user_id=token_data.get("user_id"),
        )

    # Create event stream
    return EventSourceResponse(
        event_service.event_stream(
            channels=channel_list, filters=filters if filters else None
        )
    )


@router.get("/downloads/{download_id}")
async def download_events(
    download_id: str,
    token: Optional[str] = Query(None, description="SSE token"),
):
    """
    SSE endpoint for a specific download's events.

    Streams only events related to the specified download ID.

    **Authentication:**
    Requires ephemeral SSE token scoped to this download.
    Get token from POST /api/v1/events/token with scope `download:{download_id}`

    **Example:**
    ```javascript
    // Step 1: Get SSE token for this specific download
    const { token } = await fetch('/api/v1/events/token', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${mainJWT}` },
      body: JSON.stringify({
        scope: `download:${downloadId}`,
        ttl: 600  // 10 minutes
      })
    }).then(r => r.json());

    // Step 2: Connect to SSE with scoped token
    const eventSource = new EventSource(
      `/api/v1/events/downloads/${downloadId}?token=${token}`
    );

    eventSource.addEventListener('download_progress', (event) => {
      const data = JSON.parse(event.data);
      updateProgressBar(data.progress);
    });
    ```
    """
    # Validate SSE token with specific download scope
    if not token:
        logger.warning(
            f"SSE connection attempted without token for download {download_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SSE token required",
        )

    # Validate token and scope
    token_data = await validate_sse_token(token, f"download:{download_id}")

    logger.info(
        "Download SSE connection established",
        download_id=download_id,
        user_id=token_data.get("user_id"),
    )

    return EventSourceResponse(
        event_service.event_stream(
            channels=["download:updates"], filters={"download_id": download_id}
        )
    )


@router.get("/queue")
async def queue_events(
    token: Optional[str] = Query(None, description="SSE token"),
):
    """
    SSE endpoint for queue updates.

    Streams queue-related events (additions, removals, status changes).

    **Authentication:**
    Requires ephemeral SSE token scoped to 'queue'.
    Get token from POST /api/v1/events/token with scope `queue`

    **Example:**
    ```javascript
    // Step 1: Get SSE token for queue updates
    const { token } = await fetch('/api/v1/events/token', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${mainJWT}` },
      body: JSON.stringify({
        scope: 'queue',
        ttl: 600  // 10 minutes
      })
    }).then(r => r.json());

    // Step 2: Connect to SSE with queue token
    const eventSource = new EventSource(`/api/v1/events/queue?token=${token}`);

    eventSource.addEventListener('queue_update', (event) => {
      const data = JSON.parse(event.data);
      refreshQueue();
    });
    ```
    """
    # Validate SSE token with queue scope
    if not token:
        logger.warning("SSE connection attempted without token for queue")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SSE token required",
        )

    # Validate token and scope
    token_data = await validate_sse_token(token, "queue")

    logger.info(
        "Queue SSE connection established",
        user_id=token_data.get("user_id"),
    )

    return EventSourceResponse(event_service.event_stream(channels=["queue:updates"]))


@router.post("/token", response_model=SSETokenResponse)
async def create_sse_token(
    request: CreateSSETokenRequest = Body(...),
    api_key: str = Depends(get_current_api_key),
    db_session: AsyncSession = Depends(get_database_session),
):
    """
    Create ephemeral SSE token for secure, scoped SSE connections.

    This endpoint solves the security issue of passing JWT tokens in query parameters
    by generating short-lived, scoped, read-only tokens specifically for SSE connections.

    **Authentication:**
    Requires main JWT token in Authorization header (secure).

    **Token Properties:**
    - **Scoped**: Limited to specific resource (e.g., `download:abc-123`, `queue`)
    - **Short-lived**: TTL 60s - 3600s (default 5 minutes)
    - **Read-only**: Cannot trigger downloads or modify data
    - **Revocable**: Automatically expires via Redis TTL

    **Usage:**
    1. Call this endpoint with main JWT to get SSE token
    2. Use SSE token to connect to SSE endpoints
    3. Token authenticates the connection, updates flow continuously
    4. Token auto-expires or is revoked when task completes

    **Example:**
    ```javascript
    // Step 1: Get SSE token (uses main JWT in header - secure!)
    const response = await fetch('/api/v1/events/token', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${mainJWT}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        scope: 'download:abc-123',
        ttl: 600  // 10 minutes
      })
    });
    const { token } = await response.json();

    // Step 2: Connect to SSE with ephemeral token (in query - acceptable)
    const eventSource = new EventSource(
      `/api/v1/events/downloads/abc-123?token=${token}`
    );
    ```

    **Scopes:**
    - `download:<download_id>` - Single download progress
    - `queue` - Queue updates
    - `system` - System notifications
    """
    # Extract user_id from api_key
    user_id = None
    if api_key.startswith("user:"):
        user_id = api_key.split(":", 1)[1]
    elif api_key.startswith("db_api_key:"):
        # For database API keys, we'd need to look up the user
        # For now, use the API key as identifier
        user_id = api_key
    else:
        # For configured API keys, use the key as identifier
        user_id = f"api_key:{api_key[:8]}"

    # Validate scope format
    scope = request.scope
    if not (
        scope == "queue"
        or scope == "system"
        or (scope.startswith("download:") and len(scope.split(":", 1)[1]) > 0)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scope format. Must be 'download:<id>', 'queue', or 'system'",
        )

    # For download scopes, verify download exists (security: prevent token creation for invalid IDs)
    if scope.startswith("download:"):
        download_id = scope.split(":", 1)[1]

        # SECURITY: Verify download exists before creating token
        # This prevents SSE token creation for non-existent/invalid download IDs
        download_repo = DownloadRepository(db_session)
        download = await download_repo.get_by_id(download_id)

        if not download:
            logger.warning(
                "SSE token denied - download not found",
                download_id=download_id,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download {download_id} not found",
            )

        logger.info(
            "Creating SSE token for download",
            download_id=download_id,
            user_id=user_id,
            download_exists=True,
        )

    # Generate SSE token
    sse_token = generate_sse_token(
        scope=scope,
        user_id=user_id,
        ttl=request.ttl,
    )

    # Store in Redis
    try:
        await redis_progress_service.store_sse_token(
            token=sse_token.token,
            data={
                "scope": sse_token.scope,
                "user_id": sse_token.user_id,
                "expires_at": sse_token.expires_at.isoformat(),
                "permissions": [p.value for p in sse_token.permissions],
                "created_at": sse_token.created_at.isoformat(),
            },
            ttl=request.ttl,
        )
    except Exception as e:
        logger.error("Failed to store SSE token", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create SSE token",
        )

    logger.info(
        "Created SSE token",
        token_prefix=sse_token.token[:12],
        scope=scope,
        user_id=user_id,
        ttl=request.ttl,
    )

    return SSETokenResponse(
        token=sse_token.token,
        expires_at=sse_token.expires_at,
        scope=sse_token.scope,
        permissions=sse_token.permissions,
        ttl=request.ttl,
    )


@router.get("/health")
async def sse_health():
    """
    Health check endpoint for SSE service.

    Returns current SSE connection metrics including active connections,
    maximum allowed connections, and heartbeat interval.
    """
    return {
        "active_connections": event_service.active_connections,
        "max_connections": event_service.max_connections,
        "heartbeat_interval": settings.sse_heartbeat_interval,
    }
