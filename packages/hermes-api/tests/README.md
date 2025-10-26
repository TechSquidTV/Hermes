# API Tests

## Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test class
uv run pytest tests/test_api/test_auth.py::TestApiKeyManagement

# Run specific test method
uv run pytest tests/test_api/test_auth.py::TestApiKeyManagement::test_create_api_key_success

# Run with verbose output
uv run pytest tests/test_api/test_auth.py -v

# Run integration tests
uv run pytest tests/test_integration/ -v

# Run repository tests
uv run pytest tests/test_api/test_api_keys.py -v
```

## Test Structure

### Backend Tests

#### `test_api/test_auth.py`
- **TestApiKeyManagement**: Tests API key CRUD operations
  - `test_create_api_key_success`: Create API key endpoint
  - `test_create_api_key_no_auth`: Authentication required
  - `test_create_api_key_validation`: Input validation
  - `test_list_api_keys_success`: List API keys endpoint
  - `test_list_api_keys_no_auth`: Authentication required
  - `test_revoke_api_key_success`: Revoke API key endpoint
  - `test_revoke_api_key_not_found`: Handle missing keys
  - `test_revoke_api_key_no_auth`: Authentication required

- **TestApiKeyAuthentication**: Tests API key validation
  - `test_api_key_authentication_success`: API keys work for auth
  - `test_database_api_key_validation`: Database validation in endpoints

- **TestApiKeySecurity**: Tests security and isolation
  - `test_user_isolation_api_keys`: Users only see their own keys

#### `test_api/test_api_keys.py` (Repository Tests)
- **TestApiKeyRepository**: Database operations
  - `test_create_api_key`: Database API key creation
  - `test_get_api_key_by_hash`: Retrieve by hash
  - `test_get_api_key_by_id`: Retrieve by ID
  - `test_get_api_keys_by_user`: User-scoped retrieval
  - `test_update_last_used`: Usage tracking
  - `test_get_nonexistent_api_key`: Error handling
  - `test_api_key_deactivation`: Status management

#### `test_integration/test_api_key_flow.py`
- **TestApiKeyIntegration**: End-to-end flows
  - `test_api_key_full_lifecycle`: Complete create → use → revoke cycle
  - `test_jwt_token_vs_api_key_authentication`: Dual auth systems
  - `test_multiple_users_api_key_isolation`: Multi-user isolation

### Frontend Tests

#### `hooks/__tests__/useApiKeys.test.ts`
- **useApiKeys hook tests**:
  - API key fetching
  - API key creation
  - API key revocation
  - Loading states
  - Error handling

#### `services/__tests__/apiClient.test.ts`
- **API client tests**:
  - `createApiKey()` method
  - `getApiKeys()` method
  - `revokeApiKey()` method
  - HTTP request formatting
  - Error handling

#### `components/settings/__tests__/ApiKeySettings.test.tsx`
- **Component tests**:
  - API keys list display
  - Loading states
  - Empty states
  - Create form interactions
  - Permission selection
  - Copy functionality
  - Revoke functionality
  - Form validation

## Test Coverage

### ✅ What's Tested

1. **API Endpoints**:
   - POST `/auth/api-keys` - Create API keys
   - GET `/auth/api-keys` - List API keys
   - DELETE `/auth/api-keys/{id}` - Revoke API keys
   - Authentication validation in protected endpoints

2. **Database Operations**:
   - API key creation with user association
   - Hash-based retrieval
   - User-scoped queries
   - Usage tracking (last_used)
   - Status management (active/inactive)

3. **Security**:
   - User isolation (users only see their own keys)
   - Authentication requirements
   - Input validation
   - Permission system

4. **Frontend Integration**:
   - Hook functionality
   - API client methods
   - Component interactions
   - Form handling
   - Error states

5. **Authentication Systems**:
   - JWT token authentication
   - Database API key authentication
   - Mixed authentication support

### 🔄 Integration Points

- JWT tokens work as API keys
- Database API keys work with download endpoints
- Frontend properly displays and manages keys
- All endpoints respect user permissions

## Setup Requirements

### Database Setup
```bash
# The tests expect database tables to exist
# Database schema should be created before running tests
# See app/db/ for current schema definitions
```

### Environment Variables
```bash
export HERMES_DEBUG=true
export HERMES_DATABASE_URL="sqlite+aiosqlite:///./test_hermes.db"
export HERMES_REDIS_URL="redis://localhost:6379/1"
```

## Missing Tests (Future)

1. **Performance Tests**:
   - Rate limiting enforcement
   - API key expiration handling
   - Bulk operations

2. **Edge Cases**:
   - Very long API key names
   - Special characters in names
   - Network timeout handling
   - Database connection failures

3. **Security Tests**:
   - SQL injection prevention
   - XSS prevention in frontend
   - Token leakage prevention
   - Audit logging

4. **Database Tests**:
   - Schema compatibility
   - Data integrity
   - Connection handling
