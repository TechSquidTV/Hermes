# Real-Time Updates Research and Implementation Plan

**Document Version:** 1.0
**Date:** 2025-10-29
**Status:** Research Complete - Awaiting Implementation Decision

---

## Executive Summary

This document provides a comprehensive analysis of Hermes' current polling-based real-time update system and proposes migration strategies to more efficient real-time communication protocols. The research covers all existing polling mechanisms, deployment architecture considerations, and provides detailed implementation recommendations for both Server-Sent Events (SSE) and WebSocket solutions.

**Key Findings:**
- 11 distinct React Query polling queries across the frontend
- Polling intervals range from 2 seconds (download progress) to 60 seconds (storage info)
- Current architecture already includes Redis infrastructure suitable for pub/sub
- Both SSE and WebSocket solutions are viable with different trade-offs

---

## Table of Contents

1. [Current Polling Mechanisms](#current-polling-mechanisms)
2. [Architecture Analysis](#architecture-analysis)
3. [Technology Comparison: SSE vs WebSockets](#technology-comparison-sse-vs-websockets)
4. [Recommended Solution](#recommended-solution)
5. [Implementation Plan](#implementation-plan)
6. [Migration Strategy](#migration-strategy)
7. [Testing Considerations](#testing-considerations)
8. [Appendix](#appendix)

---

## Current Polling Mechanisms

### 1. Overview

The application currently uses React Query for polling-based updates across 11 distinct queries. These queries poll various endpoints at different intervals depending on the data freshness requirements.

### 2. Polling Inventory by Component

#### 2.1 Queue Management (Highest Frequency)

**Location:** `packages/hermes-app/src/hooks/useQueuePolling.ts`

**Query 1: Adaptive Queue Polling**
```typescript
Hook: useQueuePolling()
Polling Strategy: Adaptive based on download state
  - 2 seconds: Active downloads (downloading/processing)
  - 10 seconds: Queued downloads
  - 30 seconds: Idle state
  - False: History view (no polling)
Endpoint: GET /api/v1/download/queue()
Query Key: ['queue', status, limit, offset, viewMode]
Stale Time: 1 second
Used In: QueueList component
```

**Query 2: Download Statistics**
```typescript
Hook: useDownloadStatsPolling()
Polling Interval: 30 seconds (fixed)
Endpoint: GET /api/v1/stats/
Query Key: ['queue', 'stats']
Stale Time: 5 seconds
Used In: QueueStats component
```

**Query 3: Download History**
```typescript
Hook: useDownloadHistory()
Polling Interval: false (manual refresh only)
Endpoint: GET /api/v1/history/
Query Key: ['history', filters]
Used In: QueueList (history view)
```

#### 2.2 Individual Download Progress (Critical Real-Time Updates)

**Location:** `packages/hermes-app/src/hooks/useDownloadProgress.ts`

```typescript
Hook: useDownloadProgress(downloadId)
Polling Interval: 2 seconds (default, configurable)
Stops When: Status is 'completed' or 'failed'
Endpoint: GET /api/v1/download/{downloadId}
Query Key: ['download', 'progress', downloadId]
Stale Time: 0 (always fresh)
Used In: TrackedTask component (Dashboard)
File: packages/hermes-app/src/routes/index.tsx
```

**Key Feature:** Automatically stops polling when download completes or fails.

#### 2.3 Analytics and Charts

**Location:** `packages/hermes-app/src/hooks/useAnalyticsPolling.ts`

**Query 4: Analytics Statistics**
```typescript
Hook: useAnalyticsPolling(period)
Polling Interval: 30 seconds
Endpoint: GET /api/v1/stats/?period={period}
Query Key: ['analytics', 'stats', period]
Stale Time: 10 seconds
Periods: 'day' | 'week' | 'month' | 'year'
Used In: QueueCharts component
```

**Query 5: Timeline Data**
```typescript
Hook: useTimelinePolling(period)
Polling Interval: 30 seconds
Endpoint: GET /api/v1/timeline/?period={period}
Query Key: ['timeline', period]
Stale Time: 10 seconds
Used In: QueueCharts (timeline visualization)
```

**Query 6: Timeline Summary**
```typescript
Hook: useTimelineSummaryPolling(period)
Polling Interval: 30 seconds
Endpoint: GET /api/v1/timeline/summary?period={period}
Query Key: ['timeline', 'summary', period]
Stale Time: 10 seconds
Used In: QueueCharts (summary cards)
```

#### 2.4 System Information

**Query 7: Storage Information**
```typescript
Hook: useStorageInfo()
Location: packages/hermes-app/src/hooks/useStorage.ts
Polling Interval: 60 seconds
Endpoint: GET /api/v1/storage
Query Key: ['storage', 'info']
Data: total_space, used_space, free_space
```

**Query 8: API Keys Management**
```typescript
Hook: useApiKeys()
Location: packages/hermes-app/src/hooks/useApiKeys.ts
Polling Interval: 60 seconds
Endpoint: GET /api/v1/auth/api-keys
Query Key: ['settings', 'api-keys']
```

**Query 9: Health Check**
```typescript
Location: packages/hermes-app/src/components/settings/GeneralSettings.tsx
Polling Interval: 30 seconds
Endpoint: GET /api/v1/health/
Query Key: ['health']
Data: API health, version, environment
```

#### 2.5 Legacy/Alternative Hooks

**Query 10: useAnalytics() - Alternative Analytics**
```typescript
Location: packages/hermes-app/src/hooks/useAnalytics.ts
Polling Interval: 30 seconds
Query Key: ['analytics', 'stats', period]
Note: Alternative to useAnalyticsPolling
```

**Query 11: useQueueData() - Simple Queue Data**
```typescript
Location: packages/hermes-app/src/hooks/useQueueData.ts
Polling Interval: 5 seconds (default, configurable)
Query Key: ['queue', status, limit, offset]
Note: Simple version without adaptive intervals
```

### 3. Non-Polling Task Tracking

**Location:** `packages/hermes-app/src/lib/taskTracking.ts`

- **Mechanism:** Event-driven with localStorage cross-tab synchronization
- **Events:** 'taskAdded', 'taskRemoved', 'taskEvent'
- **Purpose:** Track active downloads on dashboard without polling
- **Note:** This is already efficient and doesn't need replacement

### 4. Polling Summary Statistics

| Interval | Number of Queries | Use Cases |
|----------|------------------|-----------|
| 2 seconds | 2 | Download progress, active queue updates |
| 5 seconds | 1 | Simple queue data |
| 10 seconds | 1 | Adaptive queue (when queued items exist) |
| 30 seconds | 6 | Analytics, stats, health, idle queue |
| 60 seconds | 2 | Storage info, API keys |
| Adaptive | 1 | Queue polling (2s/10s/30s/false) |
| Disabled | 1 | History view |

**Total Polling Queries:** 11
**Highest Frequency:** 2 seconds (download progress)
**Most Critical:** Individual download progress and queue updates

---

## Architecture Analysis

### 1. Deployment Configurations

#### 1.1 Development Environment
**File:** `docker-compose.dev.yml`

```yaml
Architecture:
  - Frontend: localhost:5173 (Vite dev server)
  - API: localhost:8000 (direct access)
  - Redis: localhost:6379 (exposed)
  - Network: hermes-network (bridge)

Communication:
  - Frontend → API: Direct HTTP to localhost:8000
  - CORS: Allows multiple origins including localhost:5173
  - Hot Reload: Enabled for both frontend and backend
```

#### 1.2 Production Environment
**Files:** `docker-compose.yml`, `docker-compose.example.yml`

```yaml
Architecture:
  - Caddy Proxy: Port 3000 (HTTP), 3443 (HTTPS)
  - Frontend: Static files served via Caddy
  - API: Port 8000 (exposed and proxied)
  - Redis: Internal network only
  - Network: hermes-network (bridge)

Communication:
  - Browser → Caddy → API (/api/*)
  - All services communicate via Docker network
  - Caddy handles SSL/TLS termination
```

#### 1.3 Caddy Configuration
**File:** `Caddyfile`

```nginx
Key Routes:
  - /health → Caddy health response
  - /api/* → Reverse proxy to api:8000
  - /* → Frontend static files (SPA routing)

SSL Support:
  - Automatic Let's Encrypt certificates for domains
  - Examples for single domain and separate API/frontend domains
  - Headers: X-Real-IP, X-Forwarded-For, X-Forwarded-Proto
```

**Deployment Scenarios Supported:**
1. **Local Development:** Direct port access (5173 + 8000)
2. **Single Domain:** hermes.example.com (Caddy proxies /api/*)
3. **Separate Domains:** hermes.example.com + hermes-api.example.com
4. **Custom Setups:** Users can modify Caddyfile for their needs

### 2. Backend Technology Stack

**Framework:** FastAPI (0.104.1+)
- ASGI application
- Native async/await support
- Built-in WebSocket support
- SSE compatible via StreamingResponse

**ASGI Server:** Uvicorn (0.24.0+)
- Production-ready ASGI server
- WebSocket support included
- HTTP/2 capable with `uvicorn[standard]`

**Task Queue:** Celery (5.4.0-5.6.0)
- Background task processing
- Video download handling
- Progress updates during tasks

**Data Store:** Redis (5.0.0-8.0.0)
- Task queue backend for Celery
- Progress data storage (see `app/services/redis_progress.py`)
- **Pub/Sub capabilities** (not currently used but available)

**Database:** SQLite with SQLAlchemy (AsyncIO)
- Download records and history
- User authentication and API keys
- Persistent storage

### 3. Current Progress Tracking Flow

```
1. User initiates download
   ↓
2. Download task queued in Celery
   ↓
3. Celery worker processes download
   ↓
4. Progress updates stored in Redis
   Key: download:{id}:progress
   TTL: 3600 seconds (1 hour)
   Format: JSON with progress_data
   ↓
5. Frontend polls GET /api/v1/download/{id}
   ↓
6. API reads from Redis + Database
   ↓
7. Returns current progress
   ↓
8. React Query displays in UI
```

**Key Files:**
- `app/services/redis_progress.py` - Redis progress service
- `app/tasks/download_tasks.py` - Celery download tasks
- `app/api/v1/endpoints/downloads.py` - Download API endpoints

### 4. Network Considerations

#### Development Mode
- **Frontend:** Can connect directly to API (same host)
- **WebSocket/SSE:** Simple - ws://localhost:8000 or http://localhost:8000
- **CORS:** Already configured for multiple origins

#### Production Mode (Single Domain)
- **Frontend:** Static files from Caddy
- **API:** Proxied through Caddy at /api/*
- **WebSocket/SSE:** Must route through Caddy proxy
- **Challenge:** Caddy must proxy WebSocket/SSE connections
- **Solution:** Caddy natively supports both protocols

#### Production Mode (Separate Domains)
- **Frontend:** hermes.example.com
- **API:** hermes-api.example.com
- **WebSocket/SSE:** Direct connection to API domain
- **CORS:** Must be configured for cross-domain
- **SSL:** Both domains get certificates

#### Caddy WebSocket/SSE Support

**WebSocket:**
```caddyfile
handle /api/ws/* {
    reverse_proxy api:8000 {
        header_up Connection Upgrade
        header_up Upgrade websocket
    }
}
```

**SSE:**
```caddyfile
handle /api/events/* {
    reverse_proxy api:8000 {
        flush_interval -1  # Disable buffering for SSE
    }
}
```

**Key Point:** Caddy handles both protocols transparently with proper configuration.

---

## Technology Comparison: SSE vs WebSockets

### 1. Server-Sent Events (SSE)

#### Advantages
1. **Simplicity**
   - Built on standard HTTP
   - Easy to implement and debug
   - Works with existing HTTP infrastructure
   - No special libraries required on backend

2. **Automatic Reconnection**
   - Browser automatically reconnects on disconnect
   - Built-in retry mechanism with exponential backoff
   - No client-side reconnection logic needed

3. **Proxy/Load Balancer Friendly**
   - Works through standard HTTP proxies
   - No special configuration needed for Caddy
   - Compatible with all reverse proxies

4. **Browser Support**
   - Widely supported (IE 11+, all modern browsers)
   - Polyfills available for older browsers
   - EventSource API is simple and well-documented

5. **Resource Efficiency**
   - Lower overhead than WebSockets
   - No upgrade handshake required
   - Can use HTTP/2 multiplexing

#### Disadvantages
1. **Unidirectional**
   - Server can send to client only
   - Client must use HTTP requests for sending data
   - Not ideal for bidirectional communication

2. **Text-Only**
   - Only text data (UTF-8)
   - Binary data must be base64 encoded
   - Slight overhead for binary payloads

3. **Browser Limits**
   - Maximum 6 concurrent connections per domain (HTTP/1.1)
   - Less of an issue with HTTP/2
   - May need domain sharding for many streams

#### Best For Hermes
- Download progress updates (unidirectional)
- Queue status updates
- System notifications
- Statistics updates

### 2. WebSockets

#### Advantages
1. **Bidirectional**
   - Full-duplex communication
   - Client and server can send anytime
   - Real-time interactivity

2. **Binary Support**
   - Native binary message support
   - Efficient for binary data
   - Lower overhead for binary payloads

3. **Low Latency**
   - Persistent connection
   - No HTTP overhead per message
   - Ideal for gaming, chat, etc.

4. **No Connection Limits**
   - Not subject to browser HTTP connection limits
   - Can have many concurrent connections

#### Disadvantages
1. **Complexity**
   - Requires WebSocket library
   - More complex error handling
   - Manual reconnection logic needed
   - More complex proxy configuration

2. **Proxy Challenges**
   - Some proxies don't support WebSocket
   - Requires special headers and upgrade
   - May need fallback mechanism
   - Caddy requires explicit configuration

3. **Connection Management**
   - Must handle reconnection manually
   - Need to implement heartbeat/ping-pong
   - Connection state management
   - Memory management for many connections

4. **Browser Support**
   - Good support (IE 10+, all modern)
   - But requires polyfills for some features
   - More complex debugging

#### Best For Hermes
- Real-time bidirectional features (future)
- Collaborative features
- Live chat/comments
- Complex real-time interactions

### 3. Side-by-Side Comparison

| Feature | SSE | WebSocket |
|---------|-----|-----------|
| **Direction** | Unidirectional (server→client) | Bidirectional |
| **Protocol** | HTTP | WS/WSS |
| **Data Format** | Text only | Text + Binary |
| **Reconnection** | Automatic | Manual |
| **Complexity** | Low | Medium-High |
| **Proxy Support** | Excellent | Good (needs config) |
| **Browser Limits** | Yes (6 connections) | No |
| **Overhead** | Low | Very Low |
| **Use Case** | Push updates, notifications | Real-time apps, chat |
| **Caddy Config** | Minimal | Requires explicit setup |
| **Debugging** | Easy (HTTP tools) | Moderate (special tools) |
| **Hermes Fit** | **Excellent** ✓ | Good |

### 4. Hybrid Approach

**Option:** Use both technologies strategically

```
SSE for:
  - Download progress updates
  - Queue status changes
  - Statistics updates
  - System notifications

Regular HTTP for:
  - User actions (start download, cancel, etc.)
  - Configuration changes
  - File operations

WebSocket for (future):
  - Live collaboration features
  - Real-time chat/comments
  - Multi-user queue management
```

---

## Recommended Solution

### Primary Recommendation: Server-Sent Events (SSE)

**Reasoning:**
1. **Perfect fit for Hermes use case** - All current polling is for server→client updates
2. **Simplicity** - Easier to implement, test, and maintain
3. **Proxy compatibility** - Works seamlessly with Caddy and all deployment scenarios
4. **Automatic reconnection** - Browser handles reconnection automatically
5. **Resource efficient** - Lower resource usage than WebSockets
6. **Gradual migration** - Can coexist with polling during migration

### Implementation Architecture

#### Backend (FastAPI)

**1. New SSE Endpoint**
```python
# app/api/v1/endpoints/events.py

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from app.core.config import settings

router = APIRouter()

@router.get("/stream")
async def event_stream(
    api_key: str = Depends(get_current_api_key)
):
    """
    SSE endpoint for real-time updates.
    Streams: download progress, queue changes, system notifications

    Controlled by HERMES_ENABLE_SSE environment variable.
    """
    if not settings.enable_sse:
        raise HTTPException(
            status_code=503,
            detail="SSE is not enabled on this server"
        )

    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('download:updates', 'queue:updates', 'system:notifications')

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    yield {
                        "event": message['channel'],
                        "data": message['data']
                    }
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

    return EventSourceResponse(event_generator())
```

**2. Redis Pub/Sub Integration**
```python
# app/services/redis_progress.py (enhanced)

class RedisProgressService:
    async def publish_progress_update(
        self,
        download_id: str,
        progress_data: Dict[str, Any]
    ):
        """Publish progress update to Redis pub/sub"""
        await self.redis.publish(
            'download:updates',
            json.dumps({
                'download_id': download_id,
                'data': progress_data
            })
        )
```

**3. Celery Task Updates**
```python
# app/tasks/download_tasks.py (enhanced)

async def _update_download_status(...):
    # Update database (existing)
    await repos["downloads"].update_status(...)

    # Publish to Redis pub/sub (new)
    await redis_progress_service.publish_progress_update(
        download_id=download_id,
        progress_data={
            'status': status,
            'progress': progress,
            'downloaded_bytes': downloaded_bytes,
            'total_bytes': total_bytes,
            'download_speed': download_speed,
            'eta': eta
        }
    )
```

#### Frontend (React)

**1. Custom SSE Hook**
```typescript
// src/hooks/useSSE.ts

export function useSSE(url: string, options?: UseSSEOptions) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.addEventListener('download:updates', (event) => {
      const data = JSON.parse(event.data);
      setData(data);
    });

    eventSource.onerror = (err) => {
      setIsConnected(false);
      setError(new Error('SSE connection error'));
    };

    return () => {
      eventSource.close();
    };
  }, [url]);

  return { data, error, isConnected };
}
```

**2. Integration with React Query**
```typescript
// src/hooks/useDownloadProgressSSE.ts

export function useDownloadProgressSSE(downloadId: string) {
  const queryClient = useQueryClient();

  // Single master SSE flag
  const sseEnabled = import.meta.env.VITE_SSE_ENABLED === 'true';

  const { data, isConnected } = useSSE(
    sseEnabled ? `${API_BASE_URL}/api/v1/events/downloads/${downloadId}` : null,
    {
      events: ['download_progress'],
      reconnect: true,
    }
  );

  useEffect(() => {
    if (data && data.download_id === downloadId) {
      // Update React Query cache
      queryClient.setQueryData(
        ['download', 'progress', downloadId],
        data
      );
    }
  }, [data, downloadId, queryClient]);

  // Fallback to polling if SSE is disabled or fails
  const fallbackQuery = useQuery({
    queryKey: ['download', 'progress', downloadId],
    queryFn: () => apiClient.getDownloadStatus(downloadId),
    // Only poll if SSE is disabled or not connected
    refetchInterval: (!sseEnabled || !isConnected) ? 2000 : false,
  });

  return {
    ...fallbackQuery,
    isConnected,
    usesSSE: sseEnabled,
  };
}
```

#### Caddy Configuration

**Production Caddyfile (SSE support)**
```caddyfile
:80 {
    # SSE/Events endpoint
    handle /api/v1/events/* {
        reverse_proxy api:8000 {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}

            # Critical for SSE
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

### Alternative: WebSocket Implementation (Future-Proof)

If you prefer WebSocket for future bidirectional features:

**Backend:**
```python
# app/api/v1/endpoints/websocket.py

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Subscribe to Redis pub/sub
    pubsub = redis_client.pubsub()
    await pubsub.subscribe('download:updates')

    try:
        async for message in pubsub.listen():
            await websocket.send_json({
                'type': message['channel'],
                'data': json.loads(message['data'])
            })
    except WebSocketDisconnect:
        await pubsub.unsubscribe()
```

**Frontend:**
```typescript
// src/hooks/useWebSocket.ts

export function useWebSocket(url: string) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
      setSocket(ws);
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Implement reconnection logic
      setTimeout(() => {
        // Reconnect
      }, 3000);
    };

    return () => ws.close();
  }, [url]);

  return { socket, isConnected };
}
```

**Caddy Configuration:**
```caddyfile
handle /api/v1/ws {
    reverse_proxy api:8000 {
        header_up Connection {>Connection}
        header_up Upgrade {>Upgrade}
    }
}
```

---

## Implementation Plan

### Phase 1: Preparation (Week 1)

**Goal:** Set up infrastructure for real-time updates without breaking existing functionality.

1. **Backend Setup**
   - [ ] Add SSE library: `pip install sse-starlette`
   - [ ] Update `pyproject.toml` with dependency
   - [ ] Create new events router: `app/api/v1/endpoints/events.py`
   - [ ] Enhance Redis service with pub/sub methods
   - [ ] Add environment variable for enabling/disabling SSE

2. **Frontend Setup**
   - [ ] Create SSE hook: `src/hooks/useSSE.ts`
   - [ ] Create connection status component
   - [ ] Add feature flag for SSE (environment variable)

3. **Infrastructure**
   - [ ] Update Caddyfile with SSE configuration
   - [ ] Add SSE testing endpoint
   - [ ] Set up monitoring for SSE connections

4. **Testing**
   - [ ] Unit tests for SSE event generation
   - [ ] Integration tests for Redis pub/sub
   - [ ] Connection handling tests

### Phase 2: Core Download Progress (Week 2)

**Goal:** Replace most critical polling (download progress) with SSE.

1. **Backend Implementation**
   - [ ] Update `redis_progress_service.py` with publish methods
   - [ ] Modify `download_tasks.py` to publish progress updates
   - [ ] Create SSE stream endpoint for download progress
   - [ ] Add filtering by download_id

2. **Frontend Implementation**
   - [ ] Create `useDownloadProgressSSE.ts` hook
   - [ ] Update `TrackedTask` component to use SSE
   - [ ] Implement fallback to polling
   - [ ] Add reconnection indicators

3. **Testing**
   - [ ] Test real-time progress updates
   - [ ] Test automatic reconnection
   - [ ] Test fallback to polling
   - [ ] Load testing with multiple concurrent downloads

4. **Rollout**
   - [ ] Deploy to development environment
   - [ ] Enable for 10% of users (feature flag)
   - [ ] Monitor performance and errors
   - [ ] Gradual increase to 100%

### Phase 3: Queue Updates (Week 3)

**Goal:** Replace queue polling with SSE.

1. **Backend Implementation**
   - [ ] Add queue update events to Redis pub/sub
   - [ ] Publish events on queue changes
   - [ ] Create SSE stream for queue updates
   - [ ] Support filtering by status

2. **Frontend Implementation**
   - [ ] Create `useQueuePollingSSE.ts` hook
   - [ ] Update `QueueList` component
   - [ ] Maintain adaptive behavior based on activity
   - [ ] Implement fallback logic

3. **Testing**
   - [ ] Test queue additions/removals
   - [ ] Test status changes
   - [ ] Test with multiple users
   - [ ] Performance testing

### Phase 4: Statistics and Analytics (Week 4)

**Goal:** Replace low-priority polling with SSE.

1. **Backend Implementation**
   - [ ] Add statistics update events
   - [ ] Publish on statistics changes
   - [ ] Batch updates to reduce noise

2. **Frontend Implementation**
   - [ ] Update analytics hooks to use SSE
   - [ ] Update chart components
   - [ ] Maintain caching for efficiency

3. **Optimization**
   - [ ] Implement event throttling
   - [ ] Add debouncing for rapid updates
   - [ ] Optimize Redis pub/sub channels

### Phase 5: Cleanup and Optimization (Week 5)

**Goal:** Remove old polling code and optimize performance.

1. **Code Cleanup**
   - [ ] Remove old polling hooks (keep as fallback)
   - [ ] Update documentation
   - [ ] Remove feature flags
   - [ ] Clean up unused dependencies

2. **Performance Optimization**
   - [ ] Optimize Redis pub/sub channels
   - [ ] Implement message batching
   - [ ] Add connection pooling
   - [ ] Optimize memory usage

3. **Monitoring**
   - [ ] Add SSE metrics to monitoring dashboard
   - [ ] Track connection counts
   - [ ] Monitor message throughput
   - [ ] Alert on connection failures

4. **Documentation**
   - [ ] Update deployment docs
   - [ ] Document SSE endpoints
   - [ ] Create troubleshooting guide
   - [ ] Update Caddy configuration examples

---

## Migration Strategy

### Gradual Migration Approach

**Why Gradual?**
- Minimize risk of breaking existing functionality
- Allow for easy rollback if issues arise
- Gather feedback and metrics at each stage
- Ensure stability before moving to next component

### Feature Flag System

```typescript
// Frontend - Single master SSE switch
const SSE_ENABLED = import.meta.env.VITE_SSE_ENABLED === 'true';

// When SSE_ENABLED is true:
// - All real-time features use SSE (download progress, queue updates, analytics)
// - Polling is disabled for features with SSE support

// When SSE_ENABLED is false:
// - All features fall back to traditional polling
// - No SSE connections are attempted
```

```python
# Backend - Single master SSE switch
from app.core.config import settings

class Settings(BaseSettings):
    enable_sse: bool = Field(default=False, env='HERMES_ENABLE_SSE')
    sse_heartbeat_interval: int = Field(default=30, env='HERMES_SSE_HEARTBEAT')

# When enable_sse is True:
# - All SSE endpoints are active and functional
# - Redis pub/sub broadcasts events for all features

# When enable_sse is False:
# - SSE endpoints return errors
# - Clients automatically fall back to polling
```

### Rollback Plan

**Immediate Rollback (< 5 minutes):**
1. Set `VITE_SSE_ENABLED=false` in frontend environment
2. Frontend automatically falls back to polling for all features
3. No backend changes needed (SSE endpoints can stay active)

**Backend Disable:**
1. Set `HERMES_ENABLE_SSE=false` in backend environment
2. Restart API service
3. SSE endpoints will return 503 errors
4. Clients will automatically fall back to polling

**Full Rollback:**
1. Revert to previous deployment
2. Remove SSE code in next release
3. Investigate root cause
4. Re-plan implementation

### Success Metrics

**Key Performance Indicators:**

1. **Resource Usage**
   - Target: 50% reduction in API requests
   - Target: 30% reduction in server CPU usage
   - Target: 40% reduction in network bandwidth

2. **User Experience**
   - Target: < 500ms latency for updates
   - Target: 99.9% SSE connection uptime
   - Target: Zero increase in error rates

3. **Scalability**
   - Target: Support 1000 concurrent SSE connections
   - Target: < 10MB memory per SSE connection
   - Target: Stable performance under load

4. **Reliability**
   - Target: < 1% failed SSE connection attempts
   - Target: < 5s average reconnection time
   - Target: Zero data loss during reconnection

### Monitoring Dashboard

**Metrics to Track:**
- Active SSE connections count
- SSE connection duration (avg, p50, p95, p99)
- SSE message throughput (messages/second)
- SSE error rate
- Fallback to polling rate
- Redis pub/sub latency
- Redis memory usage
- API request reduction percentage

---

## Testing Considerations

### 1. Unit Tests

**Backend Tests:**
```python
# tests/test_sse.py

async def test_sse_download_progress_event():
    """Test SSE event generation for download progress"""
    # Test event formatting
    # Test filtering
    # Test authentication

async def test_redis_pubsub_publish():
    """Test publishing to Redis pub/sub"""
    # Test message publishing
    # Test channel selection
    # Test error handling

async def test_sse_connection_lifecycle():
    """Test SSE connection open/close"""
    # Test connection establishment
    # Test heartbeat
    # Test graceful shutdown
```

**Frontend Tests:**
```typescript
// src/hooks/__tests__/useSSE.test.ts

describe('useSSE', () => {
  test('establishes SSE connection', () => {
    // Test connection establishment
  });

  test('receives and processes events', () => {
    // Test event handling
  });

  test('handles connection errors', () => {
    // Test error handling
  });

  test('reconnects on disconnect', () => {
    // Test reconnection logic
  });

  test('falls back to polling on failure', () => {
    // Test fallback mechanism
  });
});
```

### 2. Integration Tests

```python
# tests/integration/test_real_time_updates.py

async def test_end_to_end_download_progress():
    """Test complete flow: download → Redis → SSE → client"""
    # 1. Start download
    # 2. Connect SSE client
    # 3. Verify progress updates received
    # 4. Verify data accuracy
    # 5. Verify update frequency

async def test_multiple_concurrent_downloads():
    """Test SSE with multiple simultaneous downloads"""
    # 1. Start multiple downloads
    # 2. Connect multiple SSE clients
    # 3. Verify correct routing of updates
    # 4. Verify no cross-contamination

async def test_sse_with_caddy_proxy():
    """Test SSE through Caddy reverse proxy"""
    # 1. Set up Caddy proxy
    # 2. Connect SSE client through proxy
    # 3. Verify events received correctly
    # 4. Test connection persistence
```

### 3. Load Tests

```python
# tests/load/test_sse_load.py

async def test_1000_concurrent_connections():
    """Test SSE with 1000 concurrent connections"""
    # Simulate 1000 clients
    # Monitor resource usage
    # Verify all clients receive updates
    # Check for memory leaks

async def test_high_frequency_updates():
    """Test SSE with high-frequency update bursts"""
    # Generate rapid update events
    # Verify throttling works
    # Verify no dropped messages
    # Monitor Redis performance
```

### 4. Deployment Tests

**Development Environment:**
- [ ] Test direct connection (localhost:5173 → localhost:8000)
- [ ] Test hot reload compatibility
- [ ] Test CORS configuration

**Production Environment (Single Domain):**
- [ ] Test through Caddy proxy
- [ ] Test SSL/TLS termination
- [ ] Test with custom domain
- [ ] Test certificate renewal impact

**Production Environment (Separate Domains):**
- [ ] Test cross-domain SSE
- [ ] Test CORS with credentials
- [ ] Test separate SSL certificates

**Docker Compose:**
- [ ] Test in docker-compose.yml setup
- [ ] Test in docker-compose.dev.yml setup
- [ ] Test service restart handling
- [ ] Test network isolation

### 5. Fallback Testing

```typescript
// Test scenarios for polling fallback

test('falls back when SSE not available', () => {
  // Disable SSE on server
  // Verify automatic fallback to polling
  // Verify user sees updates
});

test('falls back on repeated SSE failures', () => {
  // Simulate SSE connection failures
  // Verify fallback after threshold
  // Verify error notification to user
});

test('switches back to SSE when available', () => {
  // Start with polling fallback
  // Re-enable SSE
  // Verify automatic switch back to SSE
});
```

### 6. Browser Compatibility Tests

**Browsers to Test:**
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Safari iOS
- Chrome Android

**Test Cases:**
- [ ] Basic SSE connection
- [ ] Automatic reconnection
- [ ] Tab visibility handling
- [ ] Network change handling
- [ ] Mobile browser background handling

---

## Appendix

### A. React Query Configuration

**Current Configuration:**
```typescript
// packages/hermes-app/src/lib/queryClient.ts

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000,   // 10 minutes
      retry: 3,
    },
  },
});
```

**Recommended SSE Configuration:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: Infinity, // Data kept fresh via SSE
      gcTime: 10 * 60 * 1000,
      retry: 3,
      refetchOnWindowFocus: false, // SSE handles updates
      refetchOnReconnect: false,   // SSE handles reconnection
    },
  },
});
```

### B. API Endpoint Summary

**Current Polling Endpoints:**
```
GET  /api/v1/download/queue           (Queue list)
GET  /api/v1/download/{id}            (Download progress)
GET  /api/v1/stats/                   (Statistics)
GET  /api/v1/timeline/                (Timeline data)
GET  /api/v1/timeline/summary         (Timeline summary)
GET  /api/v1/storage                  (Storage info)
GET  /api/v1/auth/api-keys            (API keys)
GET  /api/v1/health/                  (Health check)
GET  /api/v1/history/                 (Download history)
```

**New SSE Endpoints (Proposed):**
```
GET  /api/v1/events/stream            (Main SSE stream)
GET  /api/v1/events/downloads/{id}    (Specific download)
GET  /api/v1/events/queue             (Queue updates)
GET  /api/v1/events/system            (System events)
```

### C. Redis Pub/Sub Channels

**Proposed Channel Structure:**
```
download:updates          → Individual download progress
download:{id}:progress   → Specific download updates
queue:updates            → Queue changes (add/remove/status)
queue:stats             → Queue statistics updates
system:notifications    → System-wide notifications
analytics:updates       → Analytics data changes
storage:updates         → Storage info changes
```

### D. Dependencies Required

**Backend (Python):**
```toml
[project.dependencies]
# Add to pyproject.toml
"sse-starlette>=1.6.5"  # SSE support for FastAPI
```

**Frontend (TypeScript/React):**
```json
// No additional dependencies required
// EventSource API is built into browsers
// Optional: @microsoft/fetch-event-source for better error handling
```

### E. File Structure Changes

**New Backend Files:**
```
packages/hermes-api/app/api/v1/endpoints/
  └── events.py                    (SSE endpoints)

packages/hermes-api/app/services/
  └── event_service.py             (Event management)
```

**New Frontend Files:**
```
packages/hermes-app/src/hooks/
  ├── useSSE.ts                   (Base SSE hook)
  ├── useDownloadProgressSSE.ts   (Download progress)
  ├── useQueueUpdatesSSE.ts       (Queue updates)
  └── useSystemEventsSSE.ts       (System events)

packages/hermes-app/src/lib/
  └── sse-client.ts               (SSE client utilities)

packages/hermes-app/src/components/
  └── ConnectionStatus.tsx        (Connection indicator)
```

### F. Deployment Checklist

**Development Deployment:**
- [ ] Update docker-compose.dev.yml (no changes needed)
- [ ] Set environment variables (feature flags)
- [ ] Update .env.example with new variables
- [ ] Test hot reload compatibility

**Production Deployment:**
- [ ] Update Caddyfile with SSE configuration
- [ ] Test SSL certificate handling
- [ ] Update load balancer configuration (if applicable)
- [ ] Configure monitoring for SSE metrics
- [ ] Set up alerting for connection failures
- [ ] Update backup/restore procedures
- [ ] Document rollback procedures

**User Communication:**
- [ ] Create changelog entry
- [ ] Update user documentation
- [ ] Prepare release notes
- [ ] Notify users of improvements
- [ ] Provide migration timeline

### G. Performance Benchmarks (Target)

**Current System (Polling):**
```
API Requests/minute (1 active download):
  - Download progress: 30 req/min (2s interval)
  - Queue updates: 6-30 req/min (adaptive)
  - Analytics: 2 req/min (30s interval)
  Total: ~40-60 req/min

With 10 active downloads:
  - Download progress: 300 req/min
  - Queue updates: 30 req/min
  - Analytics: 2 req/min
  Total: ~330 req/min
```

**SSE System (Target):**
```
API Requests/minute (1 active download):
  - SSE connection: 1 initial connection
  - Download progress: 0 (pushed via SSE)
  - Queue updates: 0 (pushed via SSE)
  - Analytics: 0 (pushed via SSE)
  Total: ~1 connection + real-time updates

With 10 active downloads:
  - SSE connections: 10 concurrent connections
  - Total requests: ~10 connections + real-time updates

Request Reduction: ~97% fewer HTTP requests
```

**Resource Usage Estimates:**
```
Current (Polling):
  - CPU: Medium (constant request processing)
  - Memory: Low (stateless requests)
  - Network: High (repeated full payloads)

SSE:
  - CPU: Low (event-driven, idle most of time)
  - Memory: Medium (persistent connections)
  - Network: Very Low (only changes sent)
```

### H. Additional Resources

**SSE Documentation:**
- MDN EventSource API: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- HTML5 SSE Specification: https://html.spec.whatwg.org/multipage/server-sent-events.html
- sse-starlette: https://github.com/sysid/sse-starlette

**WebSocket Documentation:**
- MDN WebSocket API: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- WebSocket Protocol: https://tools.ietf.org/html/rfc6455

**Caddy Documentation:**
- Reverse Proxy: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- WebSocket Proxying: https://caddyserver.com/docs/caddyfile/patterns#websockets

**Redis Pub/Sub:**
- Redis Pub/Sub Commands: https://redis.io/commands/?group=pubsub
- Redis Pub/Sub Best Practices: https://redis.io/docs/manual/pubsub/

---

## Conclusion

### Summary

This research has identified 11 distinct polling mechanisms in Hermes, with polling intervals ranging from 2 seconds to 60 seconds. The current architecture is well-suited for real-time updates using Server-Sent Events (SSE), which is the recommended solution due to:

1. **Perfect fit** - Hermes primarily needs unidirectional server→client updates
2. **Simplicity** - Easier to implement and maintain than WebSockets
3. **Compatibility** - Works seamlessly with all deployment scenarios
4. **Efficiency** - Expected ~97% reduction in HTTP requests
5. **Reliability** - Automatic browser reconnection

### Next Steps

1. **Review and Approve** this research document
2. **Prioritize features** - Determine which polling mechanisms to replace first
3. **Allocate resources** - Assign developers to implementation phases
4. **Set timeline** - Establish realistic deadlines for each phase
5. **Begin Phase 1** - Start with infrastructure preparation

### Questions for Discussion

1. Do we prefer SSE or WebSocket as the primary solution?
2. What is the acceptable timeline for full migration?
3. What are the acceptable performance metrics?
4. How do we want to handle the gradual rollout?
5. What monitoring and alerting do we need?

### Document Maintenance

This document should be updated as:
- Implementation progresses
- New requirements emerge
- Performance data becomes available
- Deployment scenarios change

**Document Owner:** [To be assigned]
**Review Schedule:** Monthly during implementation, quarterly after completion
**Last Updated:** 2025-10-29

---

*End of Document*
