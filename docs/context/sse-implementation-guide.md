# SSE Implementation Guide for Hermes

**Companion Document to:** `real-time-updates-research.md`
**Purpose:** Detailed technical implementation guide with code examples
**Date:** 2025-10-29

---

## Quick Start

This guide provides step-by-step instructions for implementing Server-Sent Events (SSE) in Hermes. Follow the phases in order for a smooth migration from polling to real-time updates.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Backend SSE Infrastructure](#phase-1-backend-sse-infrastructure)
3. [Phase 2: Frontend SSE Client](#phase-2-frontend-sse-client)
4. [Phase 3: Download Progress Implementation](#phase-3-download-progress-implementation)
5. [Phase 4: Queue Updates Implementation](#phase-4-queue-updates-implementation)
6. [Testing Guide](#testing-guide)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Backend Dependencies

Add to `packages/hermes-api/pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies
    "sse-starlette>=1.6.5",
]
```

Install:
```bash
cd packages/hermes-api
uv pip install sse-starlette
```

### Frontend Dependencies

No additional dependencies required! The EventSource API is built into all modern browsers.

Optional enhancement (better error handling):
```bash
cd packages/hermes-app
pnpm add @microsoft/fetch-event-source
```

### Environment Variables

**Important:** All environment variable names and default values are taken from:
- **Backend:** `/.env.example` (root) and `packages/hermes-api/app/core/config.py`
- **Frontend:** `/packages/hermes-app/.env.example`

Copy `.env.example` to `.env` and customize as needed.

**Backend** (root `.env`):
```bash
# SSE Configuration (add these new variables)
HERMES_ENABLE_SSE=true
HERMES_SSE_HEARTBEAT_INTERVAL=30  # seconds
HERMES_SSE_MAX_CONNECTIONS=1000

# Port configuration (from .env.example)
API_PORT=8000                # Default API port
HERMES_PORT=3000             # Default Caddy HTTP port
HERMES_HTTPS_PORT=3443       # Default Caddy HTTPS port
HERMES_DEV_PORT=5173         # Default Vite dev server port

# CORS origins (from .env.example - already includes common ports)
HERMES_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000,https://hermes.example.com,https://hermes-api.example.com
```

**Frontend** (root `.env` for build, or `packages/hermes-app/.env.local` for dev):
```bash
# SSE Feature Flag (add this new variable)
VITE_SSE_ENABLED=true  # Master switch for all SSE features

# API Base URL (from .env.example - defaults to /api/v1)
VITE_API_BASE_URL=/api/v1  # Use relative URL for same-domain, or full URL for separate domains
```

---

## Understanding SSE in Different Deployment Scenarios

Before implementation, it's critical to understand how SSE works across different ports, with/without SSL, and in various deployment configurations.

### How SSE and CORS Work Together

**Key Point:** SSE uses the browser's `EventSource` API, which respects CORS (Cross-Origin Resource Sharing) policies just like regular HTTP requests.

**Different Ports = Different Origins:**
- `http://localhost:5173` → `http://localhost:8000` = Cross-origin (different ports)
- `https://hermes.example.com` → `https://hermes.example.com/api` = Same-origin
- `https://hermes.example.com` → `https://hermes-api.example.com` = Cross-origin (different domains)

**Good News:** Hermes already has CORS properly configured! The backend includes `allow_credentials=True` which is essential for SSE with authentication.

### Scenario 1: Local Development (Different Ports - No SSL)

**Setup:**
```
Frontend: localhost:${HERMES_DEV_PORT:-5173} (Vite dev server)
API:      localhost:${API_PORT:-8000} (FastAPI direct)
```

**How SSE Works:**
1. Frontend creates EventSource using `VITE_API_BASE_URL`
2. Browser sends CORS preflight (OPTIONS) request
3. Backend responds with CORS headers (already configured)
4. SSE connection established across different ports
5. Events flow from API port to frontend port

**Configuration Required:**

**Root `.env`:**
```bash
# SSE Configuration
HERMES_ENABLE_SSE=true

# CORS - from .env.example (already includes common dev ports)
HERMES_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000,https://hermes.example.com,https://hermes-api.example.com

# Port configuration
API_PORT=8000
HERMES_DEV_PORT=5173
```

**Frontend `packages/hermes-app/.env.local`:**
```bash
# SSE Feature Flag
VITE_SSE_ENABLED=true

# API URL - use localhost with API_PORT for direct dev
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

**Why This Works:**
- ✓ No SSL required for localhost
- ✓ CORS headers allow cross-port communication
- ✓ `allow_credentials=True` allows authentication cookies/tokens
- ✓ EventSource API handles CORS automatically

**Testing:**
```bash
# Terminal 1: Start API (uses API_PORT from .env, defaults to 8000)
cd packages/hermes-api
uv run uvicorn app.main:app --reload --port ${API_PORT:-8000}

# Terminal 2: Start Frontend (uses HERMES_DEV_PORT from .env, defaults to 5173)
cd packages/hermes-app
pnpm dev

# Terminal 3: Test SSE directly (use API_PORT)
curl -N http://localhost:${API_PORT:-8000}/api/v1/events/stream
```

---

### Scenario 2: Docker Compose Local (Simple - No SSL)

**Setup:**
```
Caddy:    localhost:${HERMES_PORT:-3000} (proxy)
Frontend: Static files served by Caddy
API:      api:${API_PORT:-8000} (Docker network)
```

**How SSE Works:**
1. Frontend requests: `new EventSource('/api/v1/events/stream')` (relative URL from `VITE_API_BASE_URL`)
2. Browser sends to: `http://localhost:${HERMES_PORT:-3000}/api/v1/events/stream`
3. Caddy proxies to: `http://api:${API_PORT:-8000}/api/v1/events/stream`
4. SSE connection maintained through proxy
5. Caddy streams events back to browser

**Configuration Required:**

**Root `.env`:**
```bash
# SSE Configuration
HERMES_ENABLE_SSE=true

# Port configuration (from .env.example)
HERMES_PORT=3000      # Caddy HTTP port
HERMES_HTTPS_PORT=3443  # Caddy HTTPS port
API_PORT=8000         # Internal API port

# CORS not strictly needed - same origin via proxy
# But keeping default is fine:
HERMES_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000
```

**Frontend build uses `VITE_API_BASE_URL` from `.env`:**
```bash
# In root .env (used during build)
VITE_API_BASE_URL=/api/v1  # Relative URL (default from .env.example)
VITE_SSE_ENABLED=true
```

**Caddyfile - MUST include SSE config:**
```caddyfile
handle /api/v1/events/* {
    reverse_proxy api:${API_PORT:-8000} {
        flush_interval -1  # CRITICAL for SSE
        transport http {
            keepalive 90s
        }
    }
}
```

**Why This Works:**
- ✓ Same origin (localhost:3000 for everything)
- ✓ No CORS issues
- ✓ No SSL needed for local testing
- ✓ Caddy `flush_interval -1` prevents buffering
- ✓ Simpler than separate ports

**Testing:**
```bash
# Start Docker Compose (uses HERMES_PORT from .env)
docker compose up -d

# Test through Caddy proxy (uses HERMES_PORT, defaults to 3000)
curl -N http://localhost:${HERMES_PORT:-3000}/api/v1/events/stream

# Or use docker-compose.dev.yml for development
docker compose -f docker-compose.dev.yml up -d

# Check browser DevTools Network tab
# Should see "stream" connection with "EventStream" type
```

---

### Scenario 3: Production with Caddy (Single Domain + SSL)

**Setup:**
```
Domain:   https://hermes.example.com
Frontend: https://hermes.example.com (Caddy serves static files)
API:      https://hermes.example.com/api/* (Caddy proxies to api:${API_PORT:-8000})
SSL:      Automatic Let's Encrypt via Caddy
```

**How SSE Works:**
1. Frontend requests: `new EventSource('/api/v1/events/stream')` (relative URL from `VITE_API_BASE_URL`)
2. Browser sends to: `https://hermes.example.com/api/v1/events/stream` (HTTPS)
3. Caddy terminates SSL, proxies to: `http://api:${API_PORT:-8000}/api/v1/events/stream`
4. API responds over internal Docker network (HTTP is fine internally)
5. Caddy streams back over SSL to browser

**Configuration Required:**

**Root `.env` (for production):**
```bash
# SSE Configuration
HERMES_ENABLE_SSE=true

# Production settings
HERMES_DEBUG=false
API_PORT=8000

# CORS - Include your domain (from .env.example format)
# Same origin, so technically optional, but good practice:
HERMES_ALLOWED_ORIGINS=https://hermes.example.com

# Frontend build variable (from .env.example)
VITE_API_BASE_URL=/api/v1  # Relative URL for same domain
VITE_SSE_ENABLED=true
```

**Caddyfile:**
```caddyfile
hermes.example.com {
    tls admin@example.com  # Automatic SSL

    # SSE endpoint - MUST come before general API handler
    handle /api/v1/events/* {
        reverse_proxy api:{$API_PORT} {
            flush_interval -1      # CRITICAL
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-Proto {scheme}
            transport http {
                keepalive 90s
            }
        }
    }

    # Regular API
    handle /api/* {
        reverse_proxy api:{$API_PORT}
    }

    # Frontend
    handle {
        root * /app
        try_files {path} /index.html
        file_server
    }
}
```

**Why This Works:**
- ✓ Same origin - no CORS needed
- ✓ SSL handled by Caddy (automatic Let's Encrypt)
- ✓ Internal Docker network doesn't need SSL
- ✓ Caddy properly proxies SSE with flush_interval -1
- ✓ Production-ready and secure

**Testing:**
```bash
# Test SSE endpoint
curl -N https://hermes.example.com/api/v1/events/stream

# Check SSL certificate
openssl s_client -connect hermes.example.com:443 -servername hermes.example.com

# Monitor Caddy logs
docker logs -f hermes-proxy
```

---

### Scenario 4: Production with Caddy (Separate Domains + SSL)

**Setup:**
```
Frontend: https://hermes.example.com
API:      https://hermes-api.example.com
SSL:      Automatic Let's Encrypt for both domains
```

**How SSE Works:**
1. Frontend requests using `VITE_API_BASE_URL`: `new EventSource('https://hermes-api.example.com/api/v1/events/stream')`
2. Browser sends CORS preflight to API domain
3. API responds with CORS headers allowing frontend domain
4. SSE connection established across domains
5. Events flow from API domain to frontend domain

**Configuration Required:**

**Root `.env` (for production):**
```bash
# SSE Configuration
HERMES_ENABLE_SSE=true

# Production settings
HERMES_DEBUG=false
API_PORT=8000

# CORS - Must include frontend domain (from .env.example format)
# Using the multi-domain format from .env.example:
HERMES_ALLOWED_ORIGINS=https://hermes.example.com,https://hermes-api.example.com

# Already true by default in config.py:
HERMES_ALLOW_CREDENTIALS=true

# Frontend build variable - use full API domain URL
# (This is the "Separate domain" example from .env.example)
VITE_API_BASE_URL=https://hermes-api.example.com/api/v1
VITE_SSE_ENABLED=true
```

**Caddyfile - API domain:**
```caddyfile
hermes-api.example.com {
    tls admin@example.com

    handle /api/v1/events/* {
        reverse_proxy api:{$API_PORT} {
            flush_interval -1
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-Proto {scheme}
            transport http {
                keepalive 90s
            }
        }
    }

    handle /api/* {
        reverse_proxy api:{$API_PORT}
    }
}
```

**Caddyfile - Frontend domain:**
```caddyfile
hermes.example.com {
    tls admin@example.com

    handle {
        root * /app
        try_files {path} /index.html
        file_server
    }
}
```

**Why This Works:**
- ✓ CORS properly configured for cross-domain
- ✓ Both domains have SSL (Let's Encrypt)
- ✓ `allow_credentials=true` allows auth tokens
- ✓ Cleaner separation of frontend/backend
- ✓ Can scale independently

**Important Notes:**
- ⚠️ Both domains MUST use HTTPS (no mixed content)
- ⚠️ CORS must explicitly allow frontend domain
- ⚠️ Cookies won't work cross-domain (use Bearer tokens)
- ✓ Better for microservices architecture

**Testing:**
```bash
# Test CORS headers
curl -I -X OPTIONS https://hermes-api.example.com/api/v1/events/stream \
  -H "Origin: https://hermes.example.com" \
  -H "Access-Control-Request-Method: GET"

# Should see:
# Access-Control-Allow-Origin: https://hermes.example.com
# Access-Control-Allow-Credentials: true

# Test SSE
curl -N https://hermes-api.example.com/api/v1/events/stream
```

---

### Common Issues and Solutions

#### Issue 1: "CORS Error" in Browser Console

**Symptom:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/events/stream'
from origin 'http://localhost:5173' has been blocked by CORS policy
```

**Solution:**
```bash
# Add frontend origin to backend CORS config in .env
# Use the comma-separated format from .env.example:
HERMES_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8000

# Or in docker-compose.dev.yml (uses JSON array format in docker):
environment:
  - HERMES_ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000","http://localhost:8000"]
```

#### Issue 2: "Mixed Content" Error (HTTPS → HTTP)

**Symptom:**
```
Mixed Content: The page at 'https://hermes.example.com' was loaded over HTTPS,
but requested an insecure EventSource endpoint 'http://...'
```

**Solution:**
- Both frontend and API MUST use HTTPS in production
- Use same domain with Caddy proxy (Scenario 3)
- Or use HTTPS for both domains (Scenario 4)

#### Issue 3: SSE Connection Closes Immediately

**Symptom:** Connection opens then closes in browser DevTools

**Solutions:**
```caddyfile
# Ensure Caddyfile has flush_interval -1
handle /api/v1/events/* {
    reverse_proxy api:8000 {
        flush_interval -1  # MUST be -1, not 0
    }
}
```

```bash
# Check backend logs for errors
docker logs hermes-api

# Verify SSE is enabled
curl http://localhost:8000/api/v1/events/health
```

#### Issue 4: "Connection Failed" with EventSource

**Symptom:** EventSource immediately fires `onerror`

**Solutions:**
1. **Check API is running:**
   ```bash
   curl http://localhost:8000/api/v1/events/health
   ```

2. **Check CORS (if different origins):**
   ```bash
   # Test with curl including Origin header (use your HERMES_DEV_PORT and API_PORT)
   curl -H "Origin: http://localhost:${HERMES_DEV_PORT:-5173}" \
        http://localhost:${API_PORT:-8000}/api/v1/events/stream
   ```

3. **Check authentication:**
   ```typescript
   // Ensure API key/token is included
   const eventSource = new EventSource(
     '/api/v1/events/stream',
     { withCredentials: true }  // Sends cookies/auth
   );
   ```

---

### Summary: Will SSE Work in My Setup?

| Scenario | Ports | SSL | CORS Needed? | Works? |
|----------|-------|-----|--------------|--------|
| **Dev: Vite + API direct** | Different | No | ✓ Yes | ✓ Yes - CORS configured |
| **Local Docker + Caddy** | Same (proxied) | No | ✗ No | ✓ Yes - Same origin |
| **Prod: Single domain** | Same (proxied) | Yes | ✗ No | ✓ Yes - Same origin |
| **Prod: Separate domains** | N/A | Yes | ✓ Yes | ✓ Yes - CORS configured |
| **Mixed: HTTPS → HTTP** | Any | Mixed | Any | ✗ No - Browser blocks |

**Key Takeaways:**
1. ✓ **Different ports work fine** - CORS handles it (already configured)
2. ✓ **HTTP works locally** - No SSL needed for localhost
3. ✓ **Caddy proxy simplifies** - Makes everything same-origin
4. ✓ **Production needs SSL** - But Caddy handles this automatically
5. ✓ **Existing CORS config is correct** - Includes `allow_credentials=true`

**You're already set up correctly!** The existing Hermes configuration supports SSE in all scenarios with minimal changes.

---

## Phase 1: Backend SSE Infrastructure

### Step 1.1: Update Configuration

**File:** `packages/hermes-api/app/core/config.py`

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # ... existing settings

    # SSE Configuration
    enable_sse: bool = Field(
        default=False,
        env='HERMES_ENABLE_SSE',
        description='Enable Server-Sent Events for real-time updates'
    )
    sse_heartbeat_interval: int = Field(
        default=30,
        env='HERMES_SSE_HEARTBEAT_INTERVAL',
        description='SSE heartbeat interval in seconds'
    )
    sse_max_connections: int = Field(
        default=1000,
        env='HERMES_SSE_MAX_CONNECTIONS',
        description='Maximum concurrent SSE connections'
    )
    sse_connection_timeout: int = Field(
        default=300,
        env='HERMES_SSE_CONNECTION_TIMEOUT',
        description='SSE connection timeout in seconds'
    )
```

### Step 1.2: Enhance Redis Service with Pub/Sub

**File:** `packages/hermes-api/app/services/redis_progress.py`

Add these methods to the `RedisProgressService` class:

```python
import json
from typing import AsyncGenerator, Dict, Any, Optional, List
import asyncio

class RedisProgressService:
    # ... existing methods

    # ============================================================
    # PUB/SUB METHODS FOR SSE
    # ============================================================

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
            message = json.dumps({
                'type': event_type,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            await r.publish(channel, message)
            logger.debug(
                f"Published event to {channel}",
                event_type=event_type,
                channel=channel
            )
        except Exception as e:
            logger.error(
                "Failed to publish event to Redis",
                channel=channel,
                event_type=event_type,
                error=str(e),
            )

    async def subscribe_to_channels(
        self,
        channels: List[str]
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
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        yield {
                            'channel': message['channel'],
                            'type': data.get('type'),
                            'data': data.get('data'),
                            'timestamp': data.get('timestamp')
                        }
                    except json.JSONDecodeError as e:
                        logger.error(
                            "Failed to decode pub/sub message",
                            error=str(e),
                            message=message['data']
                        )
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
            logger.info(f"Unsubscribed from channels: {', '.join(channels)}")

    async def publish_download_progress(
        self,
        download_id: str,
        progress_data: Dict[str, Any]
    ) -> None:
        """
        Publish download progress update to Redis pub/sub.

        Args:
            download_id: Download ID
            progress_data: Progress information
        """
        await self.publish_event(
            channel='download:updates',
            event_type='download_progress',
            data={
                'download_id': download_id,
                **progress_data
            }
        )

    async def publish_queue_update(
        self,
        action: str,
        download_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publish queue update to Redis pub/sub.

        Args:
            action: Action type ('added', 'removed', 'status_changed')
            download_id: Download ID
            data: Additional data
        """
        await self.publish_event(
            channel='queue:updates',
            event_type='queue_update',
            data={
                'action': action,
                'download_id': download_id,
                **(data or {})
            }
        )

    async def publish_system_notification(
        self,
        notification_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publish system notification to Redis pub/sub.

        Args:
            notification_type: Type of notification ('info', 'warning', 'error')
            message: Notification message
            data: Additional data
        """
        await self.publish_event(
            channel='system:notifications',
            event_type='system_notification',
            data={
                'notification_type': notification_type,
                'message': message,
                **(data or {})
            }
        )
```

### Step 1.3: Create SSE Service

**File:** `packages/hermes-api/app/services/event_service.py` (NEW)

```python
"""
Event service for managing SSE connections and message distribution.
"""

import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, Set
from datetime import datetime, timezone
import logging

from app.services.redis_progress import redis_progress_service
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EventService:
    """Service for managing SSE events and connections."""

    def __init__(self):
        self.active_connections: int = 0
        self.max_connections: int = settings.sse_max_connections

    async def event_stream(
        self,
        channels: list[str],
        filters: Optional[Dict[str, Any]] = None
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
                max=self.max_connections
            )
            yield {
                'event': 'error',
                'data': {
                    'error': 'Maximum connections reached',
                    'code': 'MAX_CONNECTIONS'
                }
            }
            return

        self.active_connections += 1
        connection_id = f"conn_{datetime.now().timestamp()}"

        logger.info(
            "New SSE connection",
            connection_id=connection_id,
            channels=channels,
            active_connections=self.active_connections
        )

        try:
            # Send initial connection event
            yield {
                'event': 'connected',
                'data': {
                    'connection_id': connection_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }

            # Create heartbeat task
            async def send_heartbeat():
                while True:
                    await asyncio.sleep(settings.sse_heartbeat_interval)
                    yield {
                        'event': 'heartbeat',
                        'data': {
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                    }

            # Subscribe to Redis channels
            async for event in redis_progress_service.subscribe_to_channels(channels):
                # Apply filters if specified
                if filters and not self._matches_filters(event, filters):
                    continue

                # Format as SSE event
                yield {
                    'event': event['type'],
                    'data': event['data']
                }

        except asyncio.CancelledError:
            logger.info("SSE connection cancelled", connection_id=connection_id)
        except Exception as e:
            logger.error(
                "Error in SSE event stream",
                connection_id=connection_id,
                error=str(e),
                exc_info=True
            )
            yield {
                'event': 'error',
                'data': {
                    'error': 'Internal server error',
                    'code': 'INTERNAL_ERROR'
                }
            }
        finally:
            self.active_connections -= 1
            logger.info(
                "SSE connection closed",
                connection_id=connection_id,
                active_connections=self.active_connections
            )

    def _matches_filters(
        self,
        event: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """
        Check if event matches specified filters.

        Args:
            event: Event to check
            filters: Filters to apply

        Returns:
            True if event matches all filters
        """
        for key, value in filters.items():
            if key not in event.get('data', {}):
                return False
            if event['data'][key] != value:
                return False
        return True


# Global instance
event_service = EventService()
```

### Step 1.4: Create SSE Endpoints

**File:** `packages/hermes-api/app/api/v1/endpoints/events.py` (NEW)

```python
"""
Server-Sent Events (SSE) endpoints for real-time updates.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from app.core.security import get_current_api_key
from app.services.event_service import event_service
from app.core.logging import get_logger
from app.core.config import settings

router = APIRouter()
logger = get_logger(__name__)


@router.get("/stream")
async def event_stream(
    api_key: str = Depends(get_current_api_key),
    channels: Optional[str] = Query(
        None,
        description="Comma-separated list of channels (download:updates,queue:updates,system:notifications)"
    ),
    download_id: Optional[str] = Query(
        None,
        description="Filter to specific download ID"
    )
):
    """
    SSE endpoint for real-time updates.

    Streams events from Redis pub/sub channels to connected clients.
    Automatically reconnects on disconnect with Last-Event-ID support.

    **Channels:**
    - `download:updates` - Download progress updates
    - `queue:updates` - Queue status changes
    - `system:notifications` - System-wide notifications

    **Example:**
    ```javascript
    const eventSource = new EventSource(
      '/api/v1/events/stream?channels=download:updates,queue:updates'
    );

    eventSource.addEventListener('download_progress', (event) => {
      const data = JSON.parse(event.data);
      console.log('Download progress:', data);
    });
    ```
    """
    if not settings.enable_sse:
        return {
            'error': 'SSE is not enabled on this server',
            'code': 'SSE_DISABLED'
        }

    # Parse channels
    channel_list = []
    if channels:
        channel_list = [c.strip() for c in channels.split(',')]
    else:
        # Default to all channels
        channel_list = [
            'download:updates',
            'queue:updates',
            'system:notifications'
        ]

    # Build filters
    filters = {}
    if download_id:
        filters['download_id'] = download_id

    # Create event stream
    return EventSourceResponse(
        event_service.event_stream(
            channels=channel_list,
            filters=filters if filters else None
        )
    )


@router.get("/downloads/{download_id}")
async def download_events(
    download_id: str,
    api_key: str = Depends(get_current_api_key)
):
    """
    SSE endpoint for a specific download's events.

    Streams only events related to the specified download ID.

    **Example:**
    ```javascript
    const eventSource = new EventSource(
      `/api/v1/events/downloads/${downloadId}`
    );

    eventSource.addEventListener('download_progress', (event) => {
      const data = JSON.parse(event.data);
      updateProgressBar(data.progress);
    });
    ```
    """
    if not settings.enable_sse:
        return {
            'error': 'SSE is not enabled on this server',
            'code': 'SSE_DISABLED'
        }

    return EventSourceResponse(
        event_service.event_stream(
            channels=['download:updates'],
            filters={'download_id': download_id}
        )
    )


@router.get("/queue")
async def queue_events(
    api_key: str = Depends(get_current_api_key)
):
    """
    SSE endpoint for queue updates.

    Streams queue-related events (additions, removals, status changes).

    **Example:**
    ```javascript
    const eventSource = new EventSource('/api/v1/events/queue');

    eventSource.addEventListener('queue_update', (event) => {
      const data = JSON.parse(event.data);
      refreshQueue();
    });
    ```
    """
    if not settings.enable_sse:
        return {
            'error': 'SSE is not enabled on this server',
            'code': 'SSE_DISABLED'
        }

    return EventSourceResponse(
        event_service.event_stream(
            channels=['queue:updates']
        )
    )


@router.get("/health")
async def sse_health():
    """
    Health check endpoint for SSE service.

    Returns current SSE service status and connection count.
    """
    return {
        'enabled': settings.enable_sse,
        'active_connections': event_service.active_connections,
        'max_connections': event_service.max_connections,
        'heartbeat_interval': settings.sse_heartbeat_interval
    }
```

### Step 1.5: Register SSE Router

**File:** `packages/hermes-api/app/api/v1/router.py`

```python
from app.api.v1.endpoints import (
    # ... existing imports
    events,  # ADD THIS
)

# ... existing routers

# Add SSE router
api_router.include_router(
    events.router,
    prefix="/events",
    tags=["events"],
)
```

### Step 1.6: Update Download Task to Publish Events

**File:** `packages/hermes-api/app/tasks/download_tasks.py`

Find the `_update_download_status` function and add pub/sub publishing:

```python
async def _update_download_status(
    download_id: str,
    status: str,
    progress: float = None,
    error_message: str = None,
    downloaded_bytes: int = None,
    total_bytes: int = None,
    download_speed: float = None,
    eta: float = None,
    **kwargs,
) -> None:
    """Helper function to update download status."""
    async with async_session_maker() as session:
        repos = {
            "downloads": DownloadRepository(session),
            "history": DownloadHistoryRepository(session),
        }
        await repos["downloads"].update_status(
            download_id=download_id,
            status=status,
            progress=progress,
            error_message=error_message,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            download_speed=download_speed,
            eta=eta,
            **kwargs,
        )

    # ADD THIS: Publish progress update to Redis pub/sub
    from app.services.redis_progress import redis_progress_service

    await redis_progress_service.publish_download_progress(
        download_id=download_id,
        progress_data={
            'status': status,
            'progress': progress,
            'error_message': error_message,
            'downloaded_bytes': downloaded_bytes,
            'total_bytes': total_bytes,
            'download_speed': download_speed,
            'eta': eta,
            **kwargs
        }
    )

    # Publish queue update
    await redis_progress_service.publish_queue_update(
        action='status_changed',
        download_id=download_id,
        data={'status': status}
    )
```

### Step 1.7: Update Caddyfile

**File:** `Caddyfile`

Add SSE-specific configuration:

```caddyfile
:80 {
    # Health check endpoint
    handle /health {
        respond "healthy" 200
    }

    # SSE Events endpoint - MUST come before general API handler
    handle /api/v1/events/* {
        reverse_proxy api:8000 {
            # Forward headers
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
            header_up X-Forwarded-Host {host}

            # CRITICAL for SSE: Disable buffering
            flush_interval -1

            # Keep connection alive
            transport http {
                keepalive 90s
                keepalive_idle_conns 10
            }
        }
    }

    # Regular API routes
    handle /api/* {
        reverse_proxy api:8000 {
            # ... existing config
        }
    }

    # ... rest of config
}
```

---

## Phase 2: Frontend SSE Client

### Step 2.1: Create Base SSE Hook

**File:** `packages/hermes-app/src/hooks/useSSE.ts` (NEW)

```typescript
import { useEffect, useState, useRef, useCallback } from 'react';

export interface SSEOptions {
  /**
   * Enable automatic reconnection on disconnect
   */
  reconnect?: boolean;

  /**
   * Maximum number of reconnection attempts (0 = infinite)
   */
  maxReconnectAttempts?: number;

  /**
   * Initial reconnection delay in milliseconds
   */
  reconnectDelay?: number;

  /**
   * Maximum reconnection delay in milliseconds
   */
  maxReconnectDelay?: number;

  /**
   * Event types to listen for
   */
  events?: string[];

  /**
   * Callback when connection opens
   */
  onOpen?: () => void;

  /**
   * Callback when connection closes
   */
  onClose?: () => void;

  /**
   * Callback when error occurs
   */
  onError?: (error: Error) => void;
}

export interface SSEState<T = any> {
  /**
   * Latest received data
   */
  data: T | null;

  /**
   * Connection status
   */
  isConnected: boolean;

  /**
   * Error state
   */
  error: Error | null;

  /**
   * Is currently attempting to reconnect
   */
  isReconnecting: boolean;

  /**
   * Number of reconnection attempts
   */
  reconnectAttempts: number;

  /**
   * Manually close the connection
   */
  close: () => void;

  /**
   * Manually reconnect
   */
  reconnect: () => void;
}

/**
 * Hook for Server-Sent Events (SSE) with automatic reconnection
 *
 * @param url - SSE endpoint URL
 * @param options - Configuration options
 * @returns SSE state and controls
 *
 * @example
 * ```tsx
 * const { data, isConnected, error } = useSSE(
 *   '/api/v1/events/stream?channels=download:updates',
 *   {
 *     reconnect: true,
 *     maxReconnectAttempts: 5,
 *     events: ['download_progress', 'queue_update'],
 *     onOpen: () => console.log('Connected'),
 *     onError: (err) => console.error('SSE error:', err)
 *   }
 * );
 * ```
 */
export function useSSE<T = any>(
  url: string | null,
  options: SSEOptions = {}
): SSEState<T> {
  const {
    reconnect = true,
    maxReconnectAttempts = 5,
    reconnectDelay = 1000,
    maxReconnectDelay = 30000,
    events = [],
    onOpen,
    onClose,
    onError,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  const close = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    setIsReconnecting(false);
  }, []);

  const connect = useCallback(() => {
    if (!url) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        setIsReconnecting(false);
        setReconnectAttempts(0);
        onOpen?.();
      };

      eventSource.onerror = () => {
        setIsConnected(false);
        const err = new Error('SSE connection error');
        setError(err);
        onError?.(err);

        // Attempt reconnection
        if (
          shouldReconnectRef.current &&
          reconnect &&
          (maxReconnectAttempts === 0 || reconnectAttempts < maxReconnectAttempts)
        ) {
          setIsReconnecting(true);
          setReconnectAttempts((prev) => prev + 1);

          // Exponential backoff with max delay
          const delay = Math.min(
            reconnectDelay * Math.pow(2, reconnectAttempts),
            maxReconnectDelay
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          onClose?.();
        }
      };

      // Listen for specified events
      if (events.length > 0) {
        events.forEach((eventType) => {
          eventSource.addEventListener(eventType, (event: MessageEvent) => {
            try {
              const parsedData = JSON.parse(event.data);
              setData(parsedData);
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          });
        });
      } else {
        // Listen for all messages
        eventSource.onmessage = (event: MessageEvent) => {
          try {
            const parsedData = JSON.parse(event.data);
            setData(parsedData);
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        };
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create SSE connection');
      setError(error);
      onError?.(error);
    }
  }, [url, reconnect, maxReconnectAttempts, reconnectDelay, maxReconnectDelay, reconnectAttempts, events, onOpen, onClose, onError]);

  useEffect(() => {
    if (url) {
      shouldReconnectRef.current = true;
      connect();
    }

    return () => {
      close();
    };
  }, [url, connect, close]);

  const manualReconnect = useCallback(() => {
    setReconnectAttempts(0);
    connect();
  }, [connect]);

  return {
    data,
    isConnected,
    error,
    isReconnecting,
    reconnectAttempts,
    close,
    reconnect: manualReconnect,
  };
}
```

### Step 2.2: Create Download Progress SSE Hook

**File:** `packages/hermes-app/src/hooks/useDownloadProgressSSE.ts` (NEW)

```typescript
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';
import { DownloadProgress } from '@/types/download';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export interface UseDownloadProgressSSEOptions {
  /**
   * Fallback to polling if SSE fails
   */
  fallbackToPolling?: boolean;
}

/**
 * Hook for real-time download progress updates via SSE
 *
 * Automatically updates React Query cache with real-time progress.
 * Falls back to polling if SSE is disabled or fails.
 *
 * @param downloadId - Download ID to track
 * @param options - Configuration options
 *
 * @example
 * ```tsx
 * function DownloadProgressBar({ downloadId }: { downloadId: string }) {
 *   const { data, isConnected } = useDownloadProgressSSE(downloadId);
 *
 *   return (
 *     <div>
 *       <ProgressBar value={data?.progress || 0} />
 *       <ConnectionIndicator connected={isConnected} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useDownloadProgressSSE(
  downloadId: string,
  options: UseDownloadProgressSSEOptions = {}
) {
  const {
    fallbackToPolling = true,
  } = options;

  // Single master SSE feature flag
  const sseEnabled = import.meta.env.VITE_SSE_ENABLED === 'true';

  const queryClient = useQueryClient();

  const sseUrl = sseEnabled
    ? `${API_BASE_URL}/api/v1/events/downloads/${downloadId}`
    : null;

  const { data, isConnected, error, isReconnecting } = useSSE<DownloadProgress>(
    sseUrl,
    {
      events: ['download_progress'],
      reconnect: true,
      maxReconnectAttempts: 5,
      onError: (err) => {
        console.error('SSE connection error:', err);
      },
    }
  );

  // Update React Query cache when SSE data arrives
  useEffect(() => {
    if (data && data.download_id === downloadId) {
      queryClient.setQueryData(
        ['download', 'progress', downloadId],
        data
      );
    }
  }, [data, downloadId, queryClient]);

  return {
    data,
    isConnected,
    error,
    isReconnecting,
    usesSSE: sseEnabled,
    usesFallback: !sseEnabled || (!isConnected && fallbackToPolling),
  };
}
```

### Step 2.3: Create Connection Status Component

**File:** `packages/hermes-app/src/components/ConnectionStatus.tsx` (NEW)

```typescript
import { WifiIcon, WifiOffIcon, RefreshCwIcon } from 'lucide-react';

export interface ConnectionStatusProps {
  isConnected: boolean;
  isReconnecting?: boolean;
  reconnectAttempts?: number;
  className?: string;
}

/**
 * Visual indicator for SSE connection status
 */
export function ConnectionStatus({
  isConnected,
  isReconnecting = false,
  reconnectAttempts = 0,
  className = '',
}: ConnectionStatusProps) {
  if (isConnected) {
    return (
      <div className={`flex items-center gap-2 text-green-600 ${className}`}>
        <WifiIcon className="h-4 w-4" />
        <span className="text-sm">Connected</span>
      </div>
    );
  }

  if (isReconnecting) {
    return (
      <div className={`flex items-center gap-2 text-yellow-600 ${className}`}>
        <RefreshCwIcon className="h-4 w-4 animate-spin" />
        <span className="text-sm">
          Reconnecting... (Attempt {reconnectAttempts})
        </span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 text-red-600 ${className}`}>
      <WifiOffIcon className="h-4 w-4" />
      <span className="text-sm">Disconnected</span>
    </div>
  );
}
```

---

## Phase 3: Download Progress Implementation

### Step 3.1: Update TrackedTask Component

**File:** `packages/hermes-app/src/components/TrackedTask.tsx` (or wherever this component exists)

```typescript
import { useDownloadProgressSSE } from '@/hooks/useDownloadProgressSSE';
import { useDownloadProgress } from '@/hooks/useDownloadProgress'; // Existing polling hook
import { ConnectionStatus } from '@/components/ConnectionStatus';

export function TrackedTask({ downloadId }: { downloadId: string }) {
  // Try SSE first
  const {
    data: sseData,
    isConnected,
    isReconnecting,
    usesSSE,
    usesFallback,
  } = useDownloadProgressSSE(downloadId);

  // Fallback to polling if SSE is disabled or failed
  const {
    data: pollingData,
    isLoading,
  } = useDownloadProgress(downloadId, {
    enabled: usesFallback, // Only poll if SSE is not working
  });

  // Use SSE data if available, otherwise use polling data
  const data = usesSSE && sseData ? sseData : pollingData;

  if (isLoading && !data) {
    return <div>Loading...</div>;
  }

  return (
    <div className="p-4 border rounded-lg">
      {/* Connection Status Indicator */}
      {usesSSE && (
        <ConnectionStatus
          isConnected={isConnected}
          isReconnecting={isReconnecting}
          className="mb-2"
        />
      )}

      {/* Download Info */}
      <h3 className="font-semibold">{data?.title}</h3>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
        <div
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
          style={{ width: `${data?.progress || 0}%` }}
        />
      </div>

      {/* Status and Details */}
      <div className="mt-2 text-sm text-gray-600">
        <div>Status: {data?.status}</div>
        <div>Progress: {data?.progress?.toFixed(1)}%</div>
        {data?.download_speed && (
          <div>Speed: {formatSpeed(data.download_speed)}</div>
        )}
        {data?.eta && (
          <div>ETA: {formatDuration(data.eta)}</div>
        )}
      </div>

      {/* Fallback Indicator */}
      {usesFallback && (
        <div className="mt-2 text-xs text-yellow-600">
          Using polling fallback
        </div>
      )}
    </div>
  );
}

function formatSpeed(bytesPerSecond: number): string {
  const mbps = bytesPerSecond / 1024 / 1024;
  return `${mbps.toFixed(2)} MB/s`;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}m ${secs}s`;
}
```

---

## Phase 4: Queue Updates Implementation

### Step 4.1: Create Queue Updates SSE Hook

**File:** `packages/hermes-app/src/hooks/useQueueUpdatesSSE.ts` (NEW)

```typescript
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export interface QueueUpdate {
  action: 'added' | 'removed' | 'status_changed';
  download_id: string;
  status?: string;
  [key: string]: any;
}

export function useQueueUpdatesSSE() {
  const queryClient = useQueryClient();

  // Single master SSE feature flag
  const sseEnabled = import.meta.env.VITE_SSE_ENABLED === 'true';

  const sseUrl = sseEnabled
    ? `${API_BASE_URL}/api/v1/events/queue`
    : null;

  const { data, isConnected, error } = useSSE<QueueUpdate>(
    sseUrl,
    {
      events: ['queue_update'],
      reconnect: true,
    }
  );

  // Invalidate queue queries when updates arrive
  useEffect(() => {
    if (data) {
      // Invalidate all queue-related queries
      queryClient.invalidateQueries({ queryKey: ['queue'] });

      // Optionally, update specific download in cache
      if (data.download_id) {
        queryClient.invalidateQueries({
          queryKey: ['download', 'progress', data.download_id],
        });
      }
    }
  }, [data, queryClient]);

  return {
    data,
    isConnected,
    error,
  };
}
```

### Step 4.2: Update QueueList Component

```typescript
import { useQueueUpdatesSSE } from '@/hooks/useQueueUpdatesSSE';
import { useQueuePolling } from '@/hooks/useQueuePolling'; // Existing hook
import { ConnectionStatus } from '@/components/ConnectionStatus';

export function QueueList() {
  const sseEnabled = import.meta.env.VITE_SSE_ENABLED === 'true';

  // SSE for real-time updates
  const { isConnected, isReconnecting } = useQueueUpdatesSSE();

  // React Query for data fetching (still needed for initial load)
  const { data, isLoading } = useQueuePolling({
    refetchInterval: sseEnabled && isConnected ? false : undefined, // Disable polling if SSE is working
  });

  return (
    <div>
      {/* Connection Status */}
      {sseEnabled && (
        <ConnectionStatus
          isConnected={isConnected}
          isReconnecting={isReconnecting}
          className="mb-4"
        />
      )}

      {/* Queue Items */}
      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <div>
          {data?.items?.map((item) => (
            <QueueItem key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Testing Guide

### Manual Testing Checklist

**Backend SSE:**
- [ ] SSE endpoint returns events: `curl -N http://localhost:8000/api/v1/events/stream`
- [ ] Download progress events are published when download starts
- [ ] Queue update events are published on status changes
- [ ] Heartbeat events are sent every 30 seconds
- [ ] Multiple clients can connect simultaneously
- [ ] Connection closes gracefully on client disconnect

**Frontend SSE:**
- [ ] EventSource connection establishes successfully
- [ ] Progress updates appear in real-time
- [ ] Connection indicator shows correct status
- [ ] Automatic reconnection works after disconnect
- [ ] Fallback to polling works when SSE is disabled
- [ ] React Query cache is updated correctly

**Deployment:**
- [ ] SSE works through Caddy proxy (production mode)
- [ ] SSL/TLS doesn't break SSE connections
- [ ] Docker Compose restart doesn't break SSE
- [ ] Works with separate domain configuration

### Unit Tests

```bash
# Backend tests
cd packages/hermes-api
uv run pytest tests/test_services/test_event_service.py -v

# Frontend tests
cd packages/hermes-app
pnpm test src/hooks/__tests__/useSSE.test.ts
```

### Integration Tests

```bash
# Run full integration test suite
cd packages/hermes-api
uv run pytest tests/integration/test_sse.py -v
```

### Load Tests

```python
# tests/load/test_sse_connections.py
import asyncio
import httpx

async def test_100_concurrent_connections():
    async with httpx.AsyncClient() as client:
        tasks = [
            client.stream('GET', 'http://localhost:8000/api/v1/events/stream')
            for _ in range(100)
        ]
        await asyncio.gather(*tasks)
```

---

## Troubleshooting

### Common Issues

**1. SSE Connection Fails Immediately**

**Symptom:** EventSource shows error immediately after connecting

**Solutions:**
- Check if SSE is enabled: `HERMES_ENABLE_SSE=true` in `.env`
- Verify endpoint exists: `curl http://localhost:8000/api/v1/events/health`
- Check CORS configuration in `main.py`
- Verify authentication (API key) is valid

**2. Events Not Received**

**Symptom:** Connection establishes but no events arrive

**Solutions:**
- Verify Redis pub/sub is working: `redis-cli SUBSCRIBE download:updates`
- Check if download task is publishing events (add logging)
- Verify channel names match in publisher and subscriber
- Check Redis connection in `docker-compose.yml`

**3. SSE Works in Dev But Not Production**

**Symptom:** Works on localhost but fails through Caddy

**Solutions:**
- Verify Caddyfile has `flush_interval -1` for SSE routes
- Check Caddy logs: `docker logs hermes-proxy`
- Ensure SSL certificates are valid
- Test with curl through Caddy: `curl -N https://your-domain.com/api/v1/events/stream`

**4. High Memory Usage**

**Symptom:** Redis or API memory grows over time

**Solutions:**
- Check for connection leaks (ensure proper cleanup)
- Monitor active connections: `GET /api/v1/events/health`
- Reduce `sse_connection_timeout` if needed
- Implement connection limits (already in code)

**5. Reconnection Loop**

**Symptom:** Frontend constantly reconnects and disconnects

**Solutions:**
- Check server logs for errors
- Increase `sse_heartbeat_interval`
- Verify network stability
- Check if backend is under heavy load

### Debug Mode

Enable debug logging:

**Backend:**
```bash
export HERMES_DEBUG=true
export HERMES_LOG_LEVEL=debug
```

**Frontend:**
```typescript
// In useSSE hook, add console logs
onOpen: () => console.log('[SSE] Connected'),
onError: (err) => console.error('[SSE] Error:', err),
```

### Monitoring

**Check SSE Health:**
```bash
# Use API_PORT from .env (defaults to 8000)
curl http://localhost:${API_PORT:-8000}/api/v1/events/health
```

**Monitor Redis Pub/Sub:**
```bash
docker exec -it hermes-redis redis-cli
PUBSUB CHANNELS
PUBSUB NUMSUB download:updates
```

**Check Active Connections:**
```bash
# Backend logs will show:
# "New SSE connection" and "SSE connection closed" events
docker logs hermes-api | grep SSE
```

---

## Next Steps

After completing this implementation:

1. **Monitor Performance:** Track metrics for 1-2 weeks
2. **Gather Feedback:** Ask users about the real-time experience
3. **Optimize:** Based on metrics, tune heartbeat intervals and connection limits
4. **Expand:** Add SSE to analytics and statistics updates
5. **Document:** Update user-facing documentation with new features

---

*End of Implementation Guide*
