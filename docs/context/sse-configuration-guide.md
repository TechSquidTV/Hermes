# SSE Configuration Quick Reference

**Related Documents:**
- [Real-Time Updates Research](./real-time-updates-research.md) - Full research and analysis
- [SSE Implementation Guide](./sse-implementation-guide.md) - Step-by-step implementation

---

## Single Feature Flag Design

Hermes uses a **single master switch** for SSE functionality, making configuration simple and deployment predictable.

### Philosophy

**One flag to rule them all** - When you enable SSE, you enable it for ALL real-time features:
- ✓ Download progress updates
- ✓ Queue status changes
- ✓ System notifications
- ✓ Analytics updates (when implemented)

This approach provides:
- **Simplicity** - One setting controls everything
- **Predictability** - No confusion about which features use SSE
- **Easy rollback** - Single flag to disable everything
- **Clear testing** - Test with SSE on or off, not individual features

---

## Environment Variables

### Backend Configuration

**File:** `.env` (in project root)

```bash
# SSE Master Switch
HERMES_ENABLE_SSE=true

# SSE Behavior Settings
HERMES_SSE_HEARTBEAT_INTERVAL=30       # Heartbeat interval in seconds
HERMES_SSE_MAX_CONNECTIONS=1000        # Maximum concurrent SSE connections
HERMES_SSE_CONNECTION_TIMEOUT=300      # Connection timeout in seconds
```

**Default values if not set:**
- `HERMES_ENABLE_SSE`: `false` (SSE disabled by default)
- `HERMES_SSE_HEARTBEAT_INTERVAL`: `30` seconds
- `HERMES_SSE_MAX_CONNECTIONS`: `1000`
- `HERMES_SSE_CONNECTION_TIMEOUT`: `300` seconds

### Frontend Configuration

**File:** `.env` or `.env.local` (in `packages/hermes-app/`)

```bash
# SSE Master Switch
VITE_SSE_ENABLED=true

# API Base URL (if different from default)
VITE_API_BASE_URL=http://localhost:8000
```

**Default values if not set:**
- `VITE_SSE_ENABLED`: `false` (uses polling)
- `VITE_API_BASE_URL`: Empty string (uses relative URLs)

---

## Configuration Scenarios

### Scenario 1: Development with SSE

**When to use:** Local development, testing SSE functionality

**Backend** (`.env`):
```bash
HERMES_ENABLE_SSE=true
HERMES_DEBUG=true
```

**Frontend** (`packages/hermes-app/.env.local`):
```bash
VITE_SSE_ENABLED=true
VITE_API_BASE_URL=http://localhost:8000
```

**Result:**
- ✓ Full SSE functionality
- ✓ Real-time updates for all features
- ✓ Easy debugging with dev tools

---

### Scenario 2: Development without SSE (Polling Only)

**When to use:** Testing fallback behavior, debugging polling issues

**Backend** (`.env`):
```bash
HERMES_ENABLE_SSE=false
# Or simply omit the variable
```

**Frontend** (`packages/hermes-app/.env.local`):
```bash
VITE_SSE_ENABLED=false
# Or simply omit the variable
```

**Result:**
- ✓ Traditional polling behavior
- ✓ No SSE connections attempted
- ✓ Useful for baseline performance testing

---

### Scenario 3: Production with SSE

**When to use:** Production deployment with real-time updates

**Backend** (`.env`):
```bash
HERMES_ENABLE_SSE=true
HERMES_DEBUG=false
HERMES_SSE_HEARTBEAT_INTERVAL=30
HERMES_SSE_MAX_CONNECTIONS=5000
```

**Frontend** (build environment or runtime config):
```bash
VITE_SSE_ENABLED=true
```

**Additional Requirements:**
- ✓ Update Caddyfile with SSE configuration (see implementation guide)
- ✓ Ensure Redis is accessible from API service
- ✓ Configure monitoring for SSE metrics

---

### Scenario 4: Production without SSE (Safe Rollback)

**When to use:** Issues with SSE, need to rollback quickly

**Frontend Change Only (fastest):**
```bash
# In frontend environment or rebuild with:
VITE_SSE_ENABLED=false
```

**Result:**
- ✓ Instant fallback to polling (no backend changes needed)
- ✓ Backend SSE endpoints can stay active (unused)
- ✓ Zero downtime

**Or Backend Change:**
```bash
# In backend .env:
HERMES_ENABLE_SSE=false
```

Then restart API service:
```bash
docker compose restart api
```

**Result:**
- ✓ SSE endpoints return 503 errors
- ✓ Clients automatically fall back to polling
- ✓ Minimal downtime (just API restart)

---

### Scenario 5: Gradual Production Rollout

**When to use:** Testing SSE with subset of users

**Approach 1: Frontend-based rollout**

Deploy multiple frontend builds with different configs:

```bash
# 90% of users (without SSE)
VITE_SSE_ENABLED=false

# 10% of users (with SSE)
VITE_SSE_ENABLED=true
```

Use your CDN or load balancer to route traffic.

**Approach 2: Backend-based rollout**

Enable SSE on backend, but keep frontend flag off by default:

```bash
# Backend: enabled
HERMES_ENABLE_SSE=true

# Frontend: disabled for most users
VITE_SSE_ENABLED=false
```

Then gradually enable for specific users via user-specific config or feature flag service.

---

## How It Works

### When SSE is Enabled

**Frontend Behavior:**
```typescript
// All these hooks automatically use SSE:
useDownloadProgressSSE(downloadId)  // ✓ SSE connection
useQueueUpdatesSSE()                 // ✓ SSE connection
useAnalyticsSSE()                    // ✓ SSE connection

// Polling is automatically disabled
refetchInterval: false  // When SSE is connected
```

**Backend Behavior:**
```python
# All SSE endpoints are active:
GET /api/v1/events/stream              # ✓ Active
GET /api/v1/events/downloads/{id}      # ✓ Active
GET /api/v1/events/queue               # ✓ Active

# Redis pub/sub is active:
await redis_service.publish_download_progress(...)  # ✓ Published
await redis_service.publish_queue_update(...)       # ✓ Published
```

### When SSE is Disabled

**Frontend Behavior:**
```typescript
// All hooks automatically fall back to polling:
useDownloadProgressSSE(downloadId)  // ✓ Uses polling (2s interval)
useQueueUpdatesSSE()                 // ✓ Uses polling (adaptive)
useAnalyticsSSE()                    // ✓ Uses polling (30s interval)

// No SSE connections attempted
// Works exactly like the old polling system
```

**Backend Behavior:**
```python
# SSE endpoints return errors:
GET /api/v1/events/stream
# Response: 503 Service Unavailable
# Body: {"detail": "SSE is not enabled on this server"}

# Redis pub/sub can stay active (no performance impact)
# Or can be disabled for minor resource savings
```

---

## Verification Commands

### Check Backend SSE Status

```bash
# Check if SSE is enabled
curl http://localhost:8000/api/v1/events/health

# Expected response when enabled:
{
  "enabled": true,
  "active_connections": 0,
  "max_connections": 1000,
  "heartbeat_interval": 30
}

# Expected response when disabled:
{
  "enabled": false,
  "active_connections": 0,
  "max_connections": 1000,
  "heartbeat_interval": 30
}
```

### Test SSE Connection

```bash
# Test SSE stream (replace with your API key)
curl -N -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/events/stream

# Expected output (when enabled):
data: {"type":"connected","data":{...}}

event: heartbeat
data: {"timestamp":"2025-10-29T..."}

# Expected output (when disabled):
{"detail":"SSE is not enabled on this server"}
```

### Check Frontend Build

```bash
# Check if SSE is enabled in frontend build
cd packages/hermes-app

# Development:
cat .env.local | grep VITE_SSE_ENABLED

# Production build:
# Check the built files for SSE references
pnpm build
grep -r "SSE_ENABLED" dist/
```

### Monitor Redis Pub/Sub

```bash
# Check active pub/sub channels
docker exec -it hermes-redis redis-cli PUBSUB CHANNELS

# Expected output when SSE is active:
1) "download:updates"
2) "queue:updates"
3) "system:notifications"

# Monitor messages on a channel
docker exec -it hermes-redis redis-cli SUBSCRIBE download:updates

# You should see messages when downloads are active
```

---

## Troubleshooting

### SSE Not Working

**Problem:** Frontend shows "Disconnected" or constantly reconnecting

**Check:**
1. Backend SSE enabled: `curl http://localhost:8000/api/v1/events/health`
2. Frontend SSE enabled: `echo $VITE_SSE_ENABLED` or check `.env.local`
3. Caddy configuration: Verify `flush_interval -1` is set for SSE routes
4. Network: Check browser console for errors

### High Resource Usage

**Problem:** High CPU or memory usage after enabling SSE

**Solutions:**
1. Reduce `HERMES_SSE_HEARTBEAT_INTERVAL` if too low (increase to 60s)
2. Lower `HERMES_SSE_MAX_CONNECTIONS` if needed
3. Check for connection leaks: `curl /api/v1/events/health` (watch active_connections)
4. Monitor Redis memory: `docker exec -it hermes-redis redis-cli INFO memory`

### Want to Disable SSE Temporarily

**Fastest Method (Frontend only):**
```bash
# Update frontend environment
VITE_SSE_ENABLED=false

# Rebuild (if needed)
cd packages/hermes-app
pnpm build

# Or restart dev server
pnpm dev
```

**Backend Method:**
```bash
# Update .env
HERMES_ENABLE_SSE=false

# Restart API
docker compose restart api
```

---

## Production Deployment Checklist

Before enabling SSE in production:

**Backend:**
- [ ] Set `HERMES_ENABLE_SSE=true` in `.env`
- [ ] Set appropriate `HERMES_SSE_MAX_CONNECTIONS` based on expected users
- [ ] Configure monitoring for `/api/v1/events/health`
- [ ] Test Redis pub/sub is working: `PUBSUB CHANNELS`
- [ ] Update Caddyfile with SSE configuration
- [ ] Test SSE endpoint: `curl -N /api/v1/events/stream`

**Frontend:**
- [ ] Set `VITE_SSE_ENABLED=true` in build environment
- [ ] Rebuild frontend: `pnpm build`
- [ ] Test SSE connection in browser DevTools
- [ ] Verify polling stops when SSE connects
- [ ] Test automatic reconnection (simulate network disconnect)

**Infrastructure:**
- [ ] Update Caddy config (see implementation guide)
- [ ] Restart Caddy: `docker compose restart proxy`
- [ ] Test through reverse proxy
- [ ] Test with SSL/TLS (if applicable)
- [ ] Configure load balancer (if applicable)
- [ ] Set up monitoring and alerting

**Rollback Plan:**
- [ ] Document rollback steps
- [ ] Test rollback in staging environment
- [ ] Prepare communication for users
- [ ] Have monitoring dashboard ready

---

## Performance Impact

### Expected Resource Changes

**With SSE Enabled:**
- ✓ ~97% fewer HTTP requests
- ✓ Lower network bandwidth usage
- ✓ Reduced backend CPU (no constant request processing)
- ⚠ Increased memory (persistent connections)
- ⚠ Redis memory usage (pub/sub overhead)

**Recommended Resources:**
- **Small deployment** (1-10 users): Current resources sufficient
- **Medium deployment** (10-100 users): +256MB RAM, current CPU sufficient
- **Large deployment** (100-1000 users): +1GB RAM, +20% CPU for connection management

### Monitoring Metrics

**Key Metrics to Track:**
- Active SSE connections: `GET /api/v1/events/health`
- Redis memory usage: `redis-cli INFO memory`
- API CPU usage: `docker stats hermes-api`
- API memory usage: `docker stats hermes-api`
- Network bandwidth: Monitor total bytes sent/received

**Alerts to Configure:**
- Active connections > 90% of max
- Redis memory > 80% of limit
- API memory > 80% of container limit
- SSE connection errors > 5% of attempts

---

## Summary

**Simple Configuration:**
- One backend flag: `HERMES_ENABLE_SSE`
- One frontend flag: `VITE_SSE_ENABLED`
- Both must be `true` for SSE to work

**Safe Rollback:**
- Set frontend flag to `false` - instant fallback, zero downtime
- Set backend flag to `false` - graceful fallback, minimal downtime

**All-or-Nothing:**
- SSE enabled = All features use real-time updates
- SSE disabled = All features use traditional polling
- No partial configurations to worry about

---

*For detailed implementation instructions, see [SSE Implementation Guide](./sse-implementation-guide.md)*
