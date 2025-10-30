# SSE Token Security Testing Guide

## Overview

This guide provides commands and steps to test the new ephemeral SSE token system that replaces JWT-in-query-params authentication for SSE connections.

## What Was Implemented

✅ **Ephemeral SSE Tokens**: Short-lived (60s - 3600s), scoped, read-only tokens for SSE
✅ **Scope-Based Access**: Tokens limited to specific resources (download:ID, queue, system)
✅ **Automatic Revocation**: Tokens revoked when downloads complete/fail
✅ **Secure Token Flow**: Main JWT only used in Authorization header, never in URLs

---

## Prerequisites

1. Backend running: `docker compose up` or `uv run uvicorn app.main:app --reload`
2. Frontend running: `cd packages/hermes-app && pnpm dev`
3. Valid JWT token (login through UI or get from localStorage)

---

## Testing Steps

### 1. Test Token Creation

**Get your JWT token from browser:**
```javascript
// In browser console
const token = localStorage.getItem('access_token')
console.log(token)
```

**Create SSE token for a download:**
```bash
# Replace YOUR_JWT_TOKEN with actual token
curl -X POST http://localhost:8000/api/v1/events/token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "download:test-123",
    "ttl": 600
  }'
```

**Expected Response:**
```json
{
  "token": "sse_AbCdEf123...",
  "expires_at": "2025-01-15T10:15:00Z",
  "scope": "download:test-123",
  "permissions": ["read"],
  "ttl": 600
}
```

---

### 2. Test SSE Connection with Token

**Connect to SSE endpoint with ephemeral token:**
```bash
# Use the token from step 1
curl -N http://localhost:8000/api/v1/events/downloads/test-123?token=sse_AbCdEf123...
```

**Expected Output:**
```
data: {"type":"connected","data":{"connection_id":"conn_...","timestamp":"..."}}

event: heartbeat
data: {"timestamp":"..."}
```

---

### 3. Test Token Scope Validation

**Try to access wrong download with scoped token:**
```bash
# Token scoped to "download:test-123"
# Try to access "download:different-456" - should FAIL
curl -N http://localhost:8000/api/v1/events/downloads/different-456?token=sse_AbCdEf123...
```

**Expected:** HTTP 403 Forbidden (scope mismatch)

---

### 4. Test Queue SSE Token

**Create queue token:**
```bash
curl -X POST http://localhost:8000/api/v1/events/token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "queue",
    "ttl": 600
  }'
```

**Connect to queue SSE:**
```bash
curl -N http://localhost:8000/api/v1/events/queue?token=QUEUE_SSE_TOKEN
```

---

### 5. Test Token Expiration

**Create short-lived token:**
```bash
curl -X POST http://localhost:8000/api/v1/events/token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "queue",
    "ttl": 60
  }'
```

**Wait 61 seconds, then try to connect:**
```bash
# Should fail with 401 Unauthorized
curl -N http://localhost:8000/api/v1/events/queue?token=EXPIRED_TOKEN
```

---

### 6. Test Token Revocation on Download Complete

**Start a real download and watch SSE:**

1. Start download through UI
2. Get download ID from response
3. Create SSE token for that download
4. Connect to SSE endpoint
5. Wait for download to complete
6. Try to reconnect with same token after completion

**Expected:** Token should be invalid after download completes (revoked)

---

### 7. Test Frontend Integration

**In browser DevTools:**

1. Open Network tab → Filter by "EventStream"
2. Start a download
3. Observe:
   - POST to `/api/v1/events/token` (uses JWT in header)
   - EventSource connection to `/api/v1/events/downloads/{id}?token=sse_...`
   - No JWT in SSE URL (only SSE token)

---

## Verification Checklist

- [ ] POST /api/v1/events/token creates tokens (requires JWT in header)
- [ ] SSE endpoints accept ephemeral tokens (in query param)
- [ ] SSE endpoints reject JWT tokens (security improvement)
- [ ] Tokens are scoped correctly (can't access other resources)
- [ ] Tokens expire after TTL
- [ ] Tokens are revoked when downloads complete/fail
- [ ] Frontend fetches SSE tokens automatically
- [ ] No JWT tokens appear in browser logs (only SSE tokens)

---

## Redis Verification

**Check tokens in Redis:**
```bash
# Connect to Redis
docker exec -it hermes-redis redis-cli

# List all SSE tokens
KEYS sse:token:*

# Get token details
GET sse:token:sse_AbCdEf123...

# Check TTL
TTL sse:token:sse_AbCdEf123...
```

---

## Security Properties Validated

✅ **No JWT in logs**: Main JWT never appears in URL/logs
✅ **Limited scope**: Tokens only access specified resources
✅ **Short-lived**: Auto-expire via Redis TTL
✅ **Read-only**: Cannot trigger downloads or modify data
✅ **Revocable**: Cleaned up when tasks complete

---

## Troubleshooting

**Token creation fails (401):**
- Check JWT is valid and not expired
- Verify JWT in Authorization header (not query param)

**SSE connection fails (403):**
- Check token scope matches endpoint
- Verify token not expired (check TTL)

**Token not found (401):**
- Token may have expired (check Redis TTL)
- Token may have been revoked (download completed)

**Frontend not connecting:**
- Check browser console for token fetch errors
- Verify apiClient.createSSEToken() is being called
- Check Network tab for failed requests

---

## Performance Testing

**Test token creation throughput:**
```bash
# Use your JWT token
JWT="your_jwt_token_here"

# Create 100 tokens rapidly
for i in {1..100}; do
  curl -s -X POST http://localhost:8000/api/v1/events/token \
    -H "Authorization: Bearer $JWT" \
    -H "Content-Type: application/json" \
    -d "{\"scope\":\"download:test-$i\",\"ttl\":300}" &
done
wait

# Check how many tokens are in Redis
docker exec hermes-redis redis-cli KEYS "sse:token:*" | wc -l
```

---

## Next Steps

1. Run through all test cases above
2. Verify security properties hold
3. Test with real downloads in UI
4. Monitor Redis memory usage for token storage
5. Consider adding token refresh mechanism for long downloads (>60 min)

---

**Questions or issues?** Check backend logs for SSE token operations:
```bash
docker logs hermes-api | grep "SSE token"
```
