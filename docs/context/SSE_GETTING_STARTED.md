# SSE Implementation - Getting Started Guide

**Date:** 2025-10-29
**Status:** ✅ Implementation Complete - SSE-Only Mode
**Architecture:** No polling fallback - Pure SSE for real-time updates

---

## 📋 What Was Implemented

A complete Server-Sent Events (SSE) system for real-time updates in Hermes. **SSE is the only method for real-time updates** - no polling fallback code exists.

### Backend Changes

✅ **Configuration** (`packages/hermes-api/app/core/config.py`)
- Added SSE settings: `enable_sse`, `sse_heartbeat_interval`, `sse_max_connections`, `sse_connection_timeout`

✅ **Redis Pub/Sub** (`packages/hermes-api/app/services/redis_progress.py`)
- `publish_event()` - Generic event publishing
- `subscribe_to_channels()` - Channel subscription with async generator
- `publish_download_progress()` - Download-specific events
- `publish_queue_update()` - Queue status events
- `publish_system_notification()` - System-wide notifications

✅ **Event Service** (`packages/hermes-api/app/services/event_service.py`)
- Connection management with max limits
- Event filtering
- Automatic heartbeat
- Graceful error handling

✅ **SSE Endpoints** (`packages/hermes-api/app/api/v1/endpoints/events.py`)
- `GET /api/v1/events/stream` - General event stream
- `GET /api/v1/events/downloads/{id}` - Download-specific events
- `GET /api/v1/events/queue` - Queue updates
- `GET /api/v1/events/health` - Health check

✅ **Download Task Updates** (`packages/hermes-api/app/tasks/download_tasks.py`)
- Modified `_update_download_status()` to publish SSE events

✅ **Caddyfile Updates** (`Caddyfile`)
- Added SSE-specific proxy config with `flush_interval -1`

✅ **Dependencies** (`packages/hermes-api/pyproject.toml`)
- Added `sse-starlette>=1.6.5`

### Frontend Changes

✅ **Base SSE Hook** (`packages/hermes-app/src/hooks/useSSE.ts`)
- EventSource wrapper with automatic reconnection
- Exponential backoff
- Event filtering
- Error handling

✅ **Download Progress SSE Hook** (`packages/hermes-app/src/hooks/useDownloadProgressSSE.ts`)
- Real-time download progress via SSE
- Automatic React Query cache updates
- Aggressive reconnection (10 attempts with exponential backoff)

✅ **Queue Updates SSE Hook** (`packages/hermes-app/src/hooks/useQueueUpdatesSSE.ts`)
- Real-time queue changes via SSE
- Automatic cache invalidation on updates

✅ **Connection Status Component** (`packages/hermes-app/src/components/ui/ConnectionStatus.tsx`)
- Visual connection indicator
- Shows connected/reconnecting/disconnected states with attempt count

✅ **Queue List Integration** (`packages/hermes-app/src/components/queue/QueueList.tsx`)
- SSE-only for real-time updates
- Initial data load via React Query (no polling interval)
- SSE invalidates cache to trigger refetch
- Connection status indicator always visible

### Configuration Files

✅ **Environment Templates**
- Updated `.env.example` (root)
- Updated `packages/hermes-app/.env.example`
- Added SSE configuration sections

---

## 🚀 Quick Start: Get SSE Running

**Note:** SSE is **enabled by default** in `.env.example`. These steps ensure everything is configured correctly.

### Step 1: Install Dependencies

```bash
cd packages/hermes-api
uv pip install sse-starlette
```

### Step 2: Verify Configuration

SSE is already enabled by default in `.env.example`. If you copied it to `.env`, verify:

```bash
# Backend SSE (should already be true)
HERMES_ENABLE_SSE=true

# Frontend SSE (should already be true)
VITE_SSE_ENABLED=true

# API URL for frontend
VITE_API_BASE_URL=/api/v1  # or http://localhost:8000/api/v1 for dev
```

**Optional:** Adjust SSE behavior:
```bash
HERMES_SSE_HEARTBEAT_INTERVAL=30      # Lower if proxies timeout
HERMES_SSE_MAX_CONNECTIONS=1000       # Increase for more users
HERMES_SSE_CONNECTION_TIMEOUT=300     # Connection timeout
```

### Step 3: Restart Services

**Docker Compose:**
```bash
docker compose restart
```

**Development Mode:**
```bash
# Terminal 1 - API
cd packages/hermes-api
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd packages/hermes-app
pnpm dev
```

---

## ✅ Verify SSE is Working

### 1. Check Backend Health

```bash
curl http://localhost:8000/api/v1/events/health
```

**Expected Response:**
```json
{
  "enabled": true,
  "active_connections": 0,
  "max_connections": 1000,
  "heartbeat_interval": 30
}
```

### 2. Test SSE Connection

```bash
# Replace YOUR_API_KEY with actual key from settings
curl -N -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/events/stream
```

**Expected Output:**
```
data: {"type":"connected","data":{"connection_id":"...","timestamp":"..."}}

event: heartbeat
data: {"timestamp":"..."}
```

### 3. Check Frontend

1. Open browser DevTools → Network tab
2. Filter for "EventStream" or "events"
3. Start a download
4. You should see:
   - Active SSE connection to `/api/v1/events/...`
   - Connection status showing "🟢 Connected" (green indicator)
   - Real-time progress updates
   - **No polling requests** - SSE is the only update mechanism

### 4. Verify Connection Status

- Queue page shows connection indicator at the top
- Indicator shows "🟢 Connected" when SSE is working
- If reconnecting: "🟡 Reconnecting... (Attempt N)"
- If disconnected: "🔴 Disconnected" (check backend/network)

---

## 🔧 Troubleshooting

### SSE Not Working

**Check 1: Backend SSE Enabled**
```bash
curl http://localhost:8000/api/v1/events/health | jq '.enabled'
# Should return: true
```

**Check 2: Frontend SSE Enabled**
```bash
# Check .env.local
grep VITE_SSE_ENABLED packages/hermes-app/.env.local
# Should show: VITE_SSE_ENABLED=true
```

**Check 3: Caddy Configuration**
```bash
# Verify flush_interval -1 is in Caddyfile
grep -A 5 "handle /api/v1/events" Caddyfile
# Should see: flush_interval -1
```

**Check 4: CORS Configuration**
```bash
# Verify frontend origin is in CORS list
grep HERMES_ALLOWED_ORIGINS .env
# Should include: http://localhost:5173 or your frontend URL
```

### Connection Keeps Dropping

1. **Increase heartbeat interval:**
   ```bash
   HERMES_SSE_HEARTBEAT_INTERVAL=60
   ```

2. **Check proxy timeout:**
   - Caddy: Add `keepalive 90s` (already in Caddyfile)
   - Nginx: Set `proxy_read_timeout 300s;`

3. **Check browser console:**
   - Look for CORS errors
   - Check authentication errors

### No Events Received

1. **Verify Redis pub/sub:**
   ```bash
   docker exec -it hermes-redis redis-cli PUBSUB CHANNELS
   # Should show: download:updates, queue:updates, system:notifications
   ```

2. **Test publishing:**
   ```bash
   # Start a download and monitor Redis
   docker exec -it hermes-redis redis-cli SUBSCRIBE download:updates
   # Should see messages when downloading
   ```

3. **Check backend logs:**
   ```bash
   docker logs hermes-api | grep SSE
   # Look for: "New SSE connection", "Published event"
   ```

---

## 🎯 Testing Checklist

- [ ] Backend health endpoint returns `enabled: true`
- [ ] SSE connection establishes successfully
- [ ] Connection status shows "Connected" in UI
- [ ] Download progress updates in real-time
- [ ] Queue updates appear instantly
- [ ] Polling requests stop when SSE connected
- [ ] Automatic reconnection works (test by restarting API)
- [ ] Fallback to polling works (test by disabling SSE)
- [ ] Multiple tabs work correctly
- [ ] Works through Caddy proxy
- [ ] Works with Docker Compose

---

## 📊 Performance Characteristics

### SSE-Only Architecture

**Benefits:**
- ✅ Minimal HTTP requests (1 connection per feature, not 100s of polls)
- ✅ Sub-second update latency (push-based, not pull-based)
- ✅ Lower server CPU (no constant request processing)
- ✅ Lower network bandwidth (persistent connection vs repeated requests)

**Considerations:**
- ⚠️ Slightly higher memory usage (persistent connections)
- ⚠️ Requires proper proxy configuration (`flush_interval -1`)
- ⚠️ Connections must stay alive (30s heartbeats handle this)

**Metrics to Monitor:**
- Active SSE connections: `curl /api/v1/events/health | jq '.active_connections'`
- Redis memory: `docker exec hermes-redis redis-cli INFO memory`
- API memory: `docker stats hermes-api`

---

## ⚠️ Important: SSE is Required

**Hermes is now SSE-only.** There is no polling fallback. If SSE doesn't work:

### Troubleshooting Connection Issues

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/api/v1/events/health
   ```

2. **Check Caddy flush_interval:**
   ```bash
   grep "flush_interval" Caddyfile
   # Should see: flush_interval -1
   ```

3. **Increase heartbeat frequency** (if proxies timeout):
   ```bash
   # In .env
   HERMES_SSE_HEARTBEAT_INTERVAL=15  # Try 15 seconds instead of 30
   ```

4. **Check CORS** (if different domains):
   ```bash
   # Ensure your frontend URL is in HERMES_ALLOWED_ORIGINS
   HERMES_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
   ```

5. **Monitor reconnection attempts:**
   - Frontend will try 10 times with exponential backoff
   - Check browser console for errors
   - Connection indicator shows attempt count

---

## 📚 Additional Resources

- **Full Research:** `docs/context/real-time-updates-research.md`
- **Implementation Guide:** `docs/context/sse-implementation-guide.md`
- **Configuration Reference:** `docs/context/sse-configuration-guide.md`

---

## ✨ Summary

**Hermes is now SSE-only!**

✅ **Ready to use:** SSE is enabled by default in `.env.example`
✅ **No fallback:** Pure SSE architecture - simpler and more reliable
✅ **Auto-reconnect:** 10 attempts with exponential backoff for resilience
✅ **Always visible:** Connection status shows at all times

**To get started:**
1. Install `sse-starlette` dependency
2. Copy `.env.example` to `.env` (SSE already enabled)
3. Restart services
4. Watch real-time updates flow! 🎉

**If connection issues occur:**
- Check backend health endpoint
- Verify Caddyfile has `flush_interval -1`
- Lower heartbeat interval if behind aggressive proxies
- Monitor connection indicator and attempt count

---

**Questions?** See the troubleshooting section or check the implementation guide for detailed debugging steps.
