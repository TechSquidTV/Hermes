# Hermes App API Client - SDK Guide

## 🎯 Overview

The Hermes app uses a **fully typed TypeScript SDK** that provides type-safe access to all API endpoints. The types are automatically generated from the backend OpenAPI schema to ensure perfect consistency.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Hermes App                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │  Components/     │         │   TanStack       │     │
│  │  Routes          │────────►│   Query Hooks    │     │
│  └──────────────────┘         └────────┬─────────┘     │
│                                         │               │
│                               ┌─────────▼─────────┐     │
│                               │   apiClient       │     │
│                               │  (SDK Instance)   │     │
│                               └────────┬──────────┘     │
│                                        │                │
│  ┌─────────────────────────────────────▼────────────┐  │
│  │           TypeScript Type Definitions             │  │
│  │         (src/types/api.generated.ts - 3,244+ lines)          │  │
│  │                                                    │  │
│  │  • 42 auto-generated schemas from OpenAPI         │  │
│  │  • Complete endpoint type coverage                 │  │
│  │  • Null-safe types matching Python Optional       │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                              │
└─────────────────────────┼──────────────────────────────┘
                          │
                  ┌───────▼────────┐
                  │   fetch API    │
                  │  (HTTP calls)  │
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  Hermes API    │
                  │ (FastAPI 23    │
                  │   endpoints)   │
                  └────────────────┘
```

---

## 🔧 Current Implementation

### Type Definitions (`src/types/api.generated.ts`)

**✅ Fully Typed - 3,244+ Lines**

All types are automatically generated from the backend OpenAPI schema:

```typescript
// Example: Complete type coverage
export interface DownloadHistory {
  total_downloads: number
  success_rate: number
  average_download_time: number
  total_size: number
  popular_extractors: PopularExtractor[]
  daily_stats: DailyStats[]
  items: HistoryItem[]
  total_items: number  // Pagination support
  page: number
  per_page: number
}
```

**Key Features:**
- ✅ All 42 backend schemas auto-generated
- ✅ Nullable types using `| null` (matches Python `Optional`)
- ✅ Union types for status enums
- ✅ Nested object types
- ✅ Array types with proper generic syntax
- ✅ Record types for dynamic keys

### API Client (`src/services/api/client.ts`)

**✅ SDK-Style Client - 250+ Lines**

A singleton class instance providing typed methods for all endpoints:

```typescript
// Usage Example
import { apiClient } from '@/services/api/client'

// Fully typed request and response
const history = await apiClient.getDownloadHistory({
  start_date: '2025-01-01',
  status: 'completed',
  limit: 20
})

// TypeScript knows the exact shape:
console.log(history.total_downloads)  // number
console.log(history.items[0].download_id)  // string
```

**Features:**
- ✅ Automatic JWT token management
- ✅ Token refresh on 401 errors
- ✅ Typed request/response for all endpoints
- ✅ Query parameter helpers
- ✅ Error handling

---

## 📊 Type Coverage Status

| Category | Endpoints | Status |
|----------|-----------|--------|
| **Health** | 3 endpoints | ✅ Complete |
| **Video Info** | 1 endpoint | ✅ Complete |
| **Downloads** | 5 endpoints | ✅ Complete |
| **Queue** | 2 endpoints | ✅ Complete |
| **Files** | 3 endpoints | ✅ Complete |
| **Formats** | 1 endpoint | ✅ Complete |
| **History** | 1 endpoint | ✅ Complete |
| **Storage** | 1 endpoint | ✅ Complete |
| **Statistics** | 3 endpoints | ✅ Complete |
| **Cleanup** | 2 endpoints | ✅ Complete |
| **Configuration** | 2 endpoints | ✅ Complete |
| **Authentication** | 7 endpoints | ✅ Complete |
| **API Keys** | 3 endpoints | ✅ Complete |

**Total: 34 endpoints with complete type coverage**

---

## 🎨 Usage Examples

### 1. Download a Video

```typescript
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

const downloadVideo = async (url: string) => {
  const request: components['schemas']['DownloadRequest'] = {
    url,
    format: 'bestvideo[height<=1080]+bestaudio',
    download_subtitles: true,
    download_thumbnail: true
  }
  
  const response = await apiClient.startDownload(request)
  
  // Response is fully typed
  console.log(`Download ID: ${response.download_id}`)
  console.log(`Status: ${response.status}`)  // Type: 'queued' | 'downloading' | ...
}
```

### 2. Get Download History with Filters

```typescript
const getRecentDownloads = async () => {
  const history = await apiClient.getDownloadHistory({
    start_date: '2025-10-01',
    end_date: '2025-10-22',
    status: 'completed',
    extractor: 'youtube',
    limit: 50,
    offset: 0
  })
  
  // All fields are typed
  console.log(`Total: ${history.total_downloads}`)
  console.log(`Success rate: ${(history.success_rate * 100).toFixed(2)}%`)
  
  history.items.forEach(item => {
    console.log(`${item.title} - ${item.file_size} bytes`)
  })
}
```

### 3. Monitor Storage

```typescript
const checkStorage = async () => {
  const storage = await apiClient.getStorageInfo()
  
  console.log(`Used: ${storage.used_space} / ${storage.total_space} bytes`)
  console.log(`Usage: ${storage.usage_percentage}%`)
  
  if (storage.cleanup_recommendations.length > 0) {
    console.log('Cleanup recommendations:')
    storage.cleanup_recommendations.forEach(rec => {
      console.log(`- ${rec.description}: ${rec.potential_savings} bytes`)
    })
  }
}
```

### 4. Update Configuration

```typescript
import type { components } from '@/types/api.generated'

const updateSettings = async () => {
  const updates: components['schemas']['ConfigurationUpdate'] = {
    max_concurrent_downloads: 5,
    download_subtitles: true,
    default_format: 'best'
  }
  
  const config = await apiClient.updateConfiguration(updates)
  console.log('Config updated:', config)
}
```

### 5. Using with TanStack Query

```typescript
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'

export function useDownloadQueue(status?: string) {
  return useQuery({
    queryKey: ['queue', status],
    queryFn: () => apiClient.getDownloadQueue(status),
    refetchInterval: 2000  // Poll every 2 seconds
  })
}

// In component
function QueueView() {
  const { data: queue } = useDownloadQueue('active')
  
  if (!queue) return <div>Loading...</div>
  
  return (
    <div>
      <h2>Active: {queue.active}</h2>
      <h2>Pending: {queue.pending}</h2>
      {queue.items.map(item => (
        <div key={item.download_id}>
          {item.current_filename} - {item.progress?.percentage}%
        </div>
      ))}
    </div>
  )
}
```

---

## 🔄 Keeping Types in Sync

### Current Method: Manual Sync

**When to Update Types:**
1. When adding new API endpoints
2. When modifying existing endpoint responses
3. After backend Pydantic model changes
4. When adding new fields to existing models

**Process:**
1. Check the OpenAPI schema: http://localhost:8000/openapi.json
2. Run the type generation: `pnpm generate:types`
3. Test the API client methods
4. Update API client if needed (new endpoints or changes)

### Option 1: Generate Types Automatically (Integrated)

**✅ Already configured!** Type generation is integrated into the main `package.json`:

```json
{
  "scripts": {
    "generate:types": "openapi-typescript http://localhost:8000/openapi.json -o ./src/types/api.generated.ts"
  }
}
```

Usage:

```bash
# Generate from running API (requires API to be running)
pnpm generate:types

# FastAPI automatically serves OpenAPI JSON at /openapi.json when running
```

### Option 2: CI/CD Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/type-check.yml
name: Type Check

on: [push, pull_request]

jobs:
  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start API
        run: docker compose up -d api
        
      - name: Wait for API
        run: sleep 10
        
      - name: Generate types
        run: |
          pnpm install
          pnpm --filter hermes-app generate:types
        
      - name: Check for type changes
        run: |
          git diff --exit-code packages/hermes-app/src/types/api.generated.ts || \
          echo "::error::Generated types don't match committed types. Run 'pnpm generate:types' and commit changes."
```

---

## 🎯 Benefits of This Approach

### ✅ Type Safety
- **Compile-time checks**: TypeScript catches type errors before runtime
- **Autocomplete**: Full IDE support for all API methods and response fields
- **Refactoring**: Change types once, TypeScript highlights all affected code

### ✅ Developer Experience
- **SDK-like**: Feels like using a native library, not raw fetch calls
- **Documentation**: Types serve as inline documentation
- **Discoverability**: IDE shows all available methods and properties

### ✅ Reliability
- **Fewer bugs**: Type mismatches caught early
- **Consistent**: App always expects correct backend response shape
- **Self-documenting**: Types show exact API contract

---

## 📝 Type Sync Checklist

Before deploying:

- [ ] Run API locally
- [ ] Check OpenAPI schema at `/openapi.json`
- [ ] Run `pnpm generate:types` to regenerate types
- [ ] Run `pnpm type-check` to verify
- [ ] Test API client methods
- [ ] Update app components if API changed

---

## 🚀 Next Steps (Optional Improvements)

1. **Add runtime validation** using `zod` for enhanced type safety
2. **Create React hooks** for each endpoint using TanStack Query
3. **Add request/response logging** in development mode
4. **Implement request caching** where appropriate (downloads, static data)
5. **Add retry logic** for transient failures with exponential backoff
6. **Create mock API client** for testing and development
7. **Add API rate limiting** visualization in the UI
8. **Implement offline support** with service worker caching

---

## 📚 Related Files

- **Current Types**: `src/types/api.generated.ts` (auto-generated from OpenAPI, 3,244+ lines)
- **API Client**: `packages/hermes-app/src/services/api/client.ts`
- **Auth Service**: `packages/hermes-app/src/services/auth.ts`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json` (auto-generated by FastAPI)
- **Backend Models**: `packages/hermes-api/app/models/pydantic/`

---

## 💡 Best Practices

1. **Always use the API client** - Don't use `fetch` directly for consistency
2. **Type your hooks** - Use TanStack Query with auto-generated typed responses
3. **Handle errors** - Wrap API calls in try/catch for robust error handling
4. **Check nullability** - Many fields are `| null` to match backend Optional types
5. **Use generated schemas** - Import types from `components['schemas']` for full type safety
6. **Regenerate types** - Run `pnpm generate:types` after backend API changes
7. **Validate at boundaries** - Check user input before API calls

---

**The Hermes app SDK provides a production-grade, type-safe way to interact with the API!** 🎉

