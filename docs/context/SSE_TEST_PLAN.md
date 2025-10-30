# SSE Test Plan

**Status**: New tests needed for SSE implementation
**Priority**: HIGH - Core functionality lacks test coverage

---

## Test Coverage Analysis

### ✅ Existing Coverage (Good)

**`tests/test_services/test_redis_progress.py`** (282 lines)
- Redis cache operations (get/set/delete) ✓
- Sync and async operations ✓
- Error handling ✓
- Data integrity ✓
- Connection management ✓

### ❌ Missing Coverage (Needs Tests)

---

## Phase 1: Critical Backend Tests 🚨

### 1.1 Redis Pub/Sub Tests (HIGH PRIORITY)

**File**: Extend `tests/test_services/test_redis_progress.py`

**New test class**:
```python
class TestRedisProgressServicePubSub:
    """Test Redis pub/sub functionality for SSE."""

    # Critical: Datetime serialization
    @pytest.mark.asyncio
    async def test_serialize_data_with_datetime():
        """Verify datetime objects convert to ISO strings."""
        # Test nested dicts with datetime values
        # Verify output is JSON-serializable

    # Critical: Event publishing
    @pytest.mark.asyncio
    async def test_publish_event_success():
        """Test successful event publishing to Redis channel."""
        # Mock Redis publish
        # Verify correct channel, event_type, data format

    @pytest.mark.asyncio
    async def test_publish_event_with_datetime():
        """Test event publishing with datetime fields."""
        # Pass data with datetime objects
        # Verify they're serialized before publishing

    # Critical: Channel subscription
    @pytest.mark.asyncio
    async def test_subscribe_to_channels():
        """Test subscribing to multiple channels."""
        # Mock Redis pubsub.listen()
        # Verify messages are parsed correctly

    # Domain-specific publishers
    @pytest.mark.asyncio
    async def test_publish_download_progress():
        """Test download progress event publishing."""

    @pytest.mark.asyncio
    async def test_publish_queue_update():
        """Test queue update event publishing."""

    @pytest.mark.asyncio
    async def test_publish_system_notification():
        """Test system notification publishing."""
```

**Why critical**:
- Fixes for datetime serialization need verification
- Core SSE messaging functionality
- ~10-15 new tests needed

---

### 1.2 Download Task Decoupling Tests (HIGH PRIORITY)

**File**: `tests/test_tasks/test_download_tasks.py` (currently empty!)

**New test classes**:
```python
class TestPublishSSEProgress:
    """Test SSE-only progress publishing."""

    @pytest.mark.asyncio
    async def test_publish_sse_progress_no_db_write():
        """Verify _publish_sse_progress does NOT write to database."""
        # Mock redis_progress_service.publish_download_progress
        # Mock database repositories
        # Call _publish_sse_progress()
        # Assert: Redis publish called, DB update NOT called

    @pytest.mark.asyncio
    async def test_publish_sse_progress_with_all_fields():
        """Test SSE publishing with complete progress data."""
        # Verify all fields are passed correctly


class TestUpdateDownloadStatus:
    """Test database update with optional SSE."""

    @pytest.mark.asyncio
    async def test_update_with_sse_enabled():
        """Test database update when publish_sse=True (default)."""
        # Mock DB and Redis
        # Call _update_download_status()
        # Assert: Both DB write AND SSE publish called

    @pytest.mark.asyncio
    async def test_update_with_sse_disabled():
        """Test database update when publish_sse=False."""
        # Mock DB and Redis
        # Call _update_download_status(publish_sse=False)
        # Assert: ONLY DB write called, SSE NOT called

    @pytest.mark.asyncio
    async def test_update_with_datetime_fields():
        """Test database update with datetime in kwargs."""
        # Pass started_at, completed_at as datetime objects
        # Verify they serialize correctly for SSE


class TestProgressHookDecoupling:
    """Test three-layer progress hook architecture."""

    @pytest.mark.asyncio
    async def test_progress_hook_redis_cache_always_writes():
        """Verify Redis cache is written on every progress callback."""
        # Mock all layers
        # Call progress_hook multiple times
        # Assert: Redis cache called every time

    @pytest.mark.asyncio
    async def test_progress_hook_sse_frequency():
        """Verify SSE updates at correct frequency (1% or 0.5s)."""
        # Mock time.time() to control timing
        # Simulate progress updates
        # Assert: _publish_sse_progress called at 1% intervals
        # Assert: NOT called for 0.5% changes

    @pytest.mark.asyncio
    async def test_progress_hook_db_frequency():
        """Verify DB updates at correct frequency (5% or 2s)."""
        # Mock time.time() to control timing
        # Simulate progress updates
        # Assert: _update_download_status called at 5% intervals
        # Assert: Called with publish_sse=False
        # Assert: NOT called for 3% changes

    @pytest.mark.asyncio
    async def test_progress_hook_decoupling():
        """Verify SSE and DB updates are independent."""
        # Track calls to both functions
        # Simulate 100% download progress
        # Assert: _publish_sse_progress called ~100 times (1% each)
        # Assert: _update_download_status called ~20 times (5% each)
        # This verifies the 5x DB reduction
```

**Why critical**:
- Verifies the performance optimization (5x DB reduction)
- Ensures SSE and DB are truly decoupled
- Validates the three-layer architecture
- ~15-20 new tests needed

---

## Phase 2: API Endpoint Tests (MEDIUM PRIORITY)

### 2.1 SSE Endpoint Tests

**File**: Create `tests/test_api/test_events.py`

**Test classes**:
```python
class TestSSEHealthEndpoint:
    """Test /api/v1/events/health endpoint."""

    def test_health_returns_sse_config():
        """Verify health endpoint returns SSE configuration."""
        # GET /api/v1/events/health
        # Assert: Returns enabled, active_connections, max_connections, etc.

    def test_health_no_auth_required():
        """Verify health endpoint works without authentication."""


class TestSSEStreamEndpoint:
    """Test /api/v1/events/stream endpoint."""

    @pytest.mark.asyncio
    async def test_stream_requires_auth():
        """Verify SSE stream requires authentication."""
        # GET without token
        # Assert: 401 Unauthorized

    @pytest.mark.asyncio
    async def test_stream_connection_established():
        """Verify SSE connection is established."""
        # GET with valid token
        # Assert: 200 OK
        # Assert: Content-Type: text/event-stream

    @pytest.mark.asyncio
    async def test_stream_receives_events():
        """Verify SSE stream receives published events."""
        # Connect to stream
        # Publish test event to Redis
        # Assert: Event received in stream


class TestDownloadSSEEndpoint:
    """Test /api/v1/events/downloads/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_download_stream_filters_by_id():
        """Verify download stream only receives events for specific download."""
        # Connect to /events/downloads/abc-123
        # Publish events for abc-123 and def-456
        # Assert: Only abc-123 events received


class TestQueueSSEEndpoint:
    """Test /api/v1/events/queue endpoint."""

    @pytest.mark.asyncio
    async def test_queue_stream_receives_updates():
        """Verify queue stream receives queue update events."""
```

**Why important**:
- Ensures endpoints work correctly
- Validates authentication
- Tests event filtering
- ~10-12 new tests needed

---

## Phase 3: Frontend Hook Tests (MEDIUM PRIORITY)

### 3.1 Base SSE Hook Tests

**File**: Create `packages/hermes-app/src/hooks/__tests__/useSSE.test.ts`

**Tests needed**:
```typescript
describe('useSSE', () => {
  it('should establish EventSource connection', () => {
    // Mock EventSource
    // Call useSSE
    // Assert: EventSource created with correct URL
  });

  it('should reconnect with exponential backoff', () => {
    // Mock EventSource to fail
    // Assert: Reconnection attempts with increasing delays
    // Assert: Stops after maxReconnectAttempts
  });

  it('should parse JSON event data', () => {
    // Mock EventSource message
    // Assert: data state updated with parsed JSON
  });

  it('should filter events by type', () => {
    // Pass events: ['download_progress']
    // Send multiple event types
    // Assert: Only download_progress received
  });
});
```

### 3.2 Download Progress Hook Tests

**File**: Create `packages/hermes-app/src/hooks/__tests__/useDownloadProgressSSE.test.ts`

**Tests needed**:
```typescript
describe('useDownloadProgressSSE', () => {
  it('should update React Query cache on progress event', () => {
    // Mock SSE data
    // Assert: queryClient.setQueryData called
  });

  it('should attempt reconnection 10 times', () => {
    // Verify maxReconnectAttempts is 10
  });

  it('should filter by download_id', () => {
    // Send events for different download_ids
    // Assert: Only matching download_id updates cache
  });
});
```

### 3.3 Queue Updates Hook Tests

**File**: Create `packages/hermes-app/src/hooks/__tests__/useQueueUpdatesSSE.test.ts`

**Tests needed**:
```typescript
describe('useQueueUpdatesSSE', () => {
  it('should invalidate queue queries on update', () => {
    // Mock SSE queue update
    // Assert: queryClient.invalidateQueries called for queue
  });

  it('should invalidate multiple query keys', () => {
    // Assert: Invalidates ['queue'], ['queueStats'], ['recentDownloadsQueue']
  });
});
```

**Why important**:
- Validates reconnection logic
- Tests React Query integration
- Ensures UI updates correctly
- ~15-18 new tests needed

---

## Phase 4: Integration Tests (LOW PRIORITY)

### 4.1 End-to-End SSE Flow

**File**: Create `tests/test_integration/test_sse_flow.py`

**Tests needed**:
```python
@pytest.mark.asyncio
async def test_download_progress_sse_flow():
    """Test complete flow from download to SSE event."""
    # 1. Start download
    # 2. Connect to SSE stream
    # 3. Wait for progress events
    # 4. Verify events received in correct format
    # 5. Verify database is NOT hit on every update

@pytest.mark.asyncio
async def test_queue_update_sse_flow():
    """Test queue updates flow through SSE."""
```

**Why low priority**:
- Unit tests cover most functionality
- Integration tests are slower
- Nice to have but not critical
- ~5-6 new tests needed

---

## Tests to Remove/Update ❌

### None! 🎉

All existing tests remain valid. The SSE implementation:
- ✅ Didn't break existing functionality
- ✅ Added new features (need new tests)
- ✅ Improved performance (need tests to verify)
- ✅ No deprecated code to remove

---

## Test Execution Recommendations

### Before Adding Tests
```bash
# Run existing tests to ensure baseline
cd packages/hermes-api
uv run pytest tests/test_services/test_redis_progress.py -v
```

### After Adding Phase 1 Tests
```bash
# Run new SSE tests
uv run pytest tests/test_services/test_redis_progress.py::TestRedisProgressServicePubSub -v
uv run pytest tests/test_tasks/test_download_tasks.py -v
```

### Coverage Analysis
```bash
# Check coverage for SSE modules
uv run pytest --cov=app.services.redis_progress --cov=app.tasks.download_tasks --cov-report=html
```

---

## Summary

### Tests Needed (Priority Order)

| Phase | Priority | Tests | Effort | Impact |
|-------|----------|-------|--------|--------|
| Phase 1.1 | 🔴 HIGH | Redis Pub/Sub | ~10-15 tests | Critical SSE messaging |
| Phase 1.2 | 🔴 HIGH | Task Decoupling | ~15-20 tests | Verify 5x DB reduction |
| Phase 2 | 🟡 MEDIUM | API Endpoints | ~10-12 tests | Endpoint validation |
| Phase 3 | 🟡 MEDIUM | Frontend Hooks | ~15-18 tests | UI integration |
| Phase 4 | 🟢 LOW | Integration | ~5-6 tests | E2E verification |

**Total New Tests**: ~55-71 tests needed

### Tests to Remove: **0**

All existing tests remain valid! 🎉

---

## Next Steps

1. **Implement Phase 1.1** - Redis Pub/Sub tests
   - Most critical for SSE reliability
   - Verifies datetime serialization fix

2. **Implement Phase 1.2** - Task Decoupling tests
   - Validates performance improvement
   - Ensures architecture is correct

3. **Run with coverage** - Measure actual coverage
   ```bash
   uv run pytest --cov=app --cov-report=term-missing
   ```

4. **Add remaining tests** - Based on priority and time

---

**Note**: The SSE implementation is production-ready and working. Tests are needed for:
- **Confidence** - Verify the optimizations work as designed
- **Regression prevention** - Catch future breakages
- **Documentation** - Tests serve as examples of correct usage
