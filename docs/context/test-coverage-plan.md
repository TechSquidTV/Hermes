# Test Coverage Improvement Plan

**Date**: 2025-10-29
**Current Coverage**: Frontend 6.68%, Backend 48%, Overall ~27%
**Goal**: Prioritize tests that most impact user experience and core functionality

## Executive Summary

This document outlines a strategic plan to improve test coverage in Hermes, focusing on critical user-facing features and core functionality. Tests are prioritized by user impact, with Tier 1 being the most critical.

## Current State Analysis

### Frontend Coverage: 6.68%
**Well-tested (>80%)**:
- `tokenStorage.ts` (82.53%)
- `auth.ts` (87.3%)
- `ApiKeySettings.tsx` (62.16%)
- Basic UI components (badge, button, card, input, label)

**Critical gaps (0%)**:
- All route components (user-facing pages)
- Download workflow components
- Queue management components
- Authentication context
- Most custom hooks

### Backend Coverage: 48%
**Well-tested (>80%)**:
- Database models (94%)
- Health checks (78-86%)
- Redis progress service (81%)

**Critical gaps (<30%)**:
- Downloads endpoints (28%)
- Queue endpoints (18%)
- History endpoints (18%)
- Info endpoints (27%)
- Cleanup tasks (0%)
- Download tasks (35%)

## Priority Tiers

### Tier 1: Critical User Flows (Highest Impact)

These directly affect core user experience. Without these, users can't accomplish their primary goals.

#### 1. Download Flow (Frontend + Backend)
**User Journey**: User pastes URL → Fetches info → Configures download → Downloads video

**Frontend Components to Test**:
- `src/components/forms/UrlInput.tsx` (0%) - URL input and validation
- `src/components/download/VideoPreview.tsx` (0%) - Video info display
- `src/hooks/useVideoInfo.ts` (0%) - Video info fetching
- `src/hooks/useDownloadActions.ts` (0%) - Download initiation
- `src/routes/index.tsx` (0%) - Main download page

**Backend Endpoints to Test**:
- `app/api/v1/endpoints/info.py` (27%) - GET /info endpoint
- `app/api/v1/endpoints/downloads.py` (28%) - POST /downloads endpoint
- `app/services/yt_dlp_service.py` (29%) - Video extraction service

**Test Scenarios**:
- ✅ Valid YouTube URL submission
- ✅ Invalid URL handling
- ✅ Unsupported site handling
- ✅ Network error handling
- ✅ Video info parsing
- ✅ Download initiation
- ✅ Format selection
- ⚠️ Large video handling
- ⚠️ Playlist detection

**Estimated Impact**: 🔴 CRITICAL - This is the core value proposition

---

#### 2. Queue Management (Frontend + Backend)
**User Journey**: User monitors downloads → Views progress → Manages queue items

**Frontend Components to Test**:
- `src/components/queue/QueueView.tsx` (0%) - Main queue display
- `src/components/queue/QueueCard.tsx` (0%) - Individual queue item
- `src/components/queue/QueueList.tsx` (0%) - Queue list rendering
- `src/hooks/useQueueData.ts` (0%) - Queue data fetching
- `src/hooks/useQueuePolling.ts` (0%) - Real-time updates
- `src/routes/queue.tsx` (0%) - Queue page

**Backend Endpoints to Test**:
- `app/api/v1/endpoints/queue.py` (18%) - GET /queue, DELETE operations
- `app/tasks/download_tasks.py` (35%) - Background processing
- `app/services/redis_progress.py` (81%) - Already well-tested ✅

**Test Scenarios**:
- ✅ Queue list loading
- ✅ Real-time progress updates
- ✅ Queue item deletion
- ✅ Queue filtering
- ✅ Empty queue state
- ⚠️ Large queue pagination
- ⚠️ WebSocket reconnection
- ⚠️ Failed download handling

**Estimated Impact**: 🔴 CRITICAL - Users can't track their downloads without this

---

#### 3. Authentication Flow (Frontend + Backend)
**User Journey**: User signs up → Logs in → Manages API keys

**Frontend Components to Test**:
- `src/contexts/AuthContext.tsx` (0%) - Auth state management
- `src/routes/auth.login.tsx` (0%) - Login page
- `src/routes/auth.signup.tsx` (0%) - Signup page
- `src/components/auth/ProtectedRoute.tsx` (0%) - Route protection

**Backend Endpoints to Test**:
- `app/api/v1/endpoints/auth.py` (49%) - Needs more edge cases
- `app/core/security.py` (65%) - Token validation edge cases

**Test Scenarios**:
- ✅ Login with valid credentials (already tested)
- ✅ Login with invalid credentials (already tested)
- ⚠️ Session persistence
- ⚠️ Token refresh flow
- ⚠️ Logout flow
- ⚠️ Protected route redirection
- ⚠️ Auth state restoration on page reload

**Estimated Impact**: 🟡 HIGH - Critical for multi-user deployments

---

### Tier 2: Secondary User Flows (High Impact)

These enhance user experience but aren't required for core functionality.

#### 4. Download History
**Frontend Components**:
- `src/hooks/useAnalytics.ts` (0%)
- History display components (need to identify)

**Backend Endpoints**:
- `app/api/v1/endpoints/history.py` (18%)
- `app/api/v1/endpoints/stats.py` (28%)

**Test Scenarios**:
- ✅ History list loading
- ✅ Date filtering
- ✅ Search functionality
- ⚠️ Pagination
- ⚠️ Export functionality

**Estimated Impact**: 🟡 HIGH - Users want to review past downloads

---

#### 5. Settings & Configuration
**Frontend Components**:
- `src/components/settings/ApiKeySettings.tsx` (62.16%) - Good coverage ✅
- `src/components/settings/AppearanceSettings.tsx` (0%)
- `src/components/settings/GeneralSettings.tsx` (0%)
- `src/hooks/useConfiguration.ts` (0%)

**Backend Endpoints**:
- `app/api/v1/endpoints/config.py` (73%) - Good coverage ✅

**Test Scenarios**:
- ✅ Theme switching
- ✅ Configuration updates
- ⚠️ Settings persistence
- ⚠️ Default value handling

**Estimated Impact**: 🟢 MEDIUM - Nice to have, not critical

---

### Tier 3: Background Operations (Medium Impact)

These run in the background but are critical for system health.

#### 6. Storage & Cleanup
**Backend Components**:
- `app/tasks/cleanup_tasks.py` (0%) - Zero coverage!
- `app/services/storage_service.py` (25%)
- `app/api/v1/endpoints/cleanup.py` (22%)

**Test Scenarios**:
- ✅ Automatic cleanup scheduling
- ✅ Manual cleanup trigger
- ✅ Storage quota enforcement
- ⚠️ Disk space monitoring
- ⚠️ Old file deletion

**Estimated Impact**: 🟡 HIGH - Prevents disk space issues

---

#### 7. File Management
**Backend Endpoints**:
- `app/api/v1/endpoints/files.py` (21%)
- `app/api/v1/endpoints/storage.py` (90%) - Good coverage ✅

**Test Scenarios**:
- ✅ File download
- ✅ File deletion
- ⚠️ Large file streaming
- ⚠️ Concurrent downloads

**Estimated Impact**: 🟢 MEDIUM

---

## Implementation Roadmap

### Phase 1: Critical User Flows (2-3 weeks)
**Goal**: Bring frontend coverage to 30%+, backend to 60%+

1. **Week 1**: Download Flow Tests
   - Frontend: UrlInput, VideoPreview, useVideoInfo
   - Backend: info.py, downloads.py endpoints
   - Integration: End-to-end download flow

2. **Week 2**: Queue Management Tests
   - Frontend: QueueView, QueueCard, useQueuePolling
   - Backend: queue.py endpoints, download_tasks.py
   - Integration: Real-time progress updates

3. **Week 3**: Authentication Flow Tests
   - Frontend: AuthContext, login/signup routes
   - Backend: Additional auth.py edge cases
   - Integration: Complete auth flow with route protection

### Phase 2: Secondary Flows (1-2 weeks)
4. **Week 4**: History & Settings
   - Frontend: History components, settings pages
   - Backend: history.py, stats.py endpoints

### Phase 3: Background Operations (1 week)
5. **Week 5**: Storage & Cleanup
   - Backend: cleanup_tasks.py, storage_service.py
   - Integration: Cleanup scheduling tests

---

## Test Strategy by Component Type

### Frontend Testing Approach

#### Route Components (Pages)
**Tools**: React Testing Library, Mock Service Worker (MSW)
**Pattern**:
```typescript
// Test user interactions, not implementation
describe('Download Page', () => {
  it('allows user to submit a URL', async () => {
    render(<DownloadPage />)
    const input = screen.getByRole('textbox', { name: /url/i })
    await userEvent.type(input, 'https://youtube.com/watch?v=test')
    await userEvent.click(screen.getByRole('button', { name: /fetch/i }))

    await waitFor(() => {
      expect(screen.getByText(/video title/i)).toBeInTheDocument()
    })
  })
})
```

#### Custom Hooks
**Tools**: @testing-library/react-hooks
**Pattern**:
```typescript
describe('useVideoInfo', () => {
  it('fetches video info for valid URL', async () => {
    const { result } = renderHook(() => useVideoInfo())

    act(() => {
      result.current.fetchInfo('https://youtube.com/watch?v=test')
    })

    await waitFor(() => {
      expect(result.current.data).toBeDefined()
      expect(result.current.isLoading).toBe(false)
    })
  })
})
```

#### Context Providers
**Tools**: React Testing Library with custom render
**Pattern**:
```typescript
const wrapper = ({ children }) => (
  <AuthProvider>{children}</AuthProvider>
)

describe('AuthContext', () => {
  it('provides login function', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.login).toBeDefined()
  })
})
```

### Backend Testing Approach

#### API Endpoints
**Tools**: pytest, httpx, pytest-asyncio
**Pattern**:
```python
@pytest.mark.asyncio
async def test_download_endpoint_success(client, auth_headers):
    response = await client.post(
        "/api/v1/downloads",
        json={"url": "https://youtube.com/watch?v=test"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert "id" in response.json()
```

#### Background Tasks
**Tools**: pytest, celery test utilities
**Pattern**:
```python
@pytest.mark.asyncio
async def test_download_task_completion(mock_ytdlp):
    task_id = await process_download("https://youtube.com/watch?v=test")
    result = await get_task_result(task_id)

    assert result.status == "completed"
    assert result.file_path is not None
```

---

## Success Metrics

### Coverage Targets
- **Phase 1 Complete**: Frontend 30%, Backend 60%, Overall 45%
- **Phase 2 Complete**: Frontend 45%, Backend 70%, Overall 57%
- **Phase 3 Complete**: Frontend 50%, Backend 75%, Overall 62%

### Quality Metrics
- All critical user flows have integration tests
- Zero untested critical paths (download, queue, auth)
- Flaky test rate < 2%
- Test execution time < 2 minutes

---

## Quick Wins (Can implement immediately)

These provide high value with minimal effort:

1. **UrlInput validation tests** (30 min)
   - Test URL regex patterns
   - Test supported/unsupported domains

2. **Queue filtering tests** (45 min)
   - Test filter state management
   - Test filter combinations

3. **TokenStorage edge cases** (30 min)
   - Already 82%, bring to 100%
   - Test localStorage errors
   - Test expired token handling

4. **Cleanup task basic tests** (1 hour)
   - Currently 0%, easy to bring to 40%+
   - Test file age calculations
   - Test deletion logic

5. **Download endpoint error cases** (45 min)
   - Invalid URLs
   - Network timeouts
   - Rate limiting

**Total time**: ~4 hours for ~5% overall coverage boost

---

## Resources & References

### Testing Documentation
- [Vitest Docs](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)

### Existing Tests (Good Examples)
- `src/services/__tests__/auth.test.ts` - Well-structured auth tests
- `tests/test_api/test_auth.py` - Comprehensive backend auth tests
- `src/components/settings/__tests__/ApiKeySettings.test.tsx` - Component testing pattern

### Test Utilities
- `src/test/setup.ts` - Frontend test setup
- `tests/conftest.py` - Backend fixtures

---

## Notes

- Focus on **user behavior** tests, not implementation details
- Use **integration tests** for critical paths (download flow, auth flow)
- Keep **unit tests** for business logic and utilities
- Mock external dependencies (yt-dlp, Redis, file system)
- Maintain test independence (no test should depend on another)

**Remember**: 100% coverage is not the goal. The goal is confidence that critical user flows work correctly.
