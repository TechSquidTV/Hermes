# Frontend API client guide

The app's [API client](src/services/api/client.ts) provides typed methods for
Hermes endpoints. [Generated schemas](src/types/api.generated.ts) come from the
backend's OpenAPI contract; reuse them rather than declaring duplicate request
or response interfaces.

## Generate and update types

From the repository root, with workspace dependencies and uv installed:

```bash
pnpm generate:types
pnpm type-check
```

The [generator](scripts/generate-openapi-types.mjs) runs the Python app's
[OpenAPI exporter](../hermes-api/scripts/export_openapi.py) through `uv run --locked`,
then invokes `openapi-typescript`. No running API, Redis, or database server is
required. Do not edit the generated file manually.

When changing an API contract:

1. Update backend models and endpoint tests.
2. Regenerate the schemas.
3. Update the client methods, hooks, and components that use changed fields.
4. Run relevant frontend and backend checks and commit the generated file.

For interactive inspection, the development schema is at
[localhost:5173/api/v1/openapi.json](http://localhost:5173/api/v1/openapi.json).

## Requests and responses

JSON models use camelCase. Query parameters retain their schema-defined names,
including `start_date`, `end_date`, `limit`, and `offset`. The client converts
query objects into URL parameters but does not rename JSON fields.

### Start a download

```typescript
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

const request = {
  url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
  format: 'bestvideo*+bestaudio/best',
  downloadSubtitles: true,
  downloadThumbnail: true,
} satisfies components['schemas']['DownloadRequest']

const download = await apiClient.startDownload(request)
console.log(download.downloadId, download.status, download.message)
```

The backend defaults omitted formats to `bestvideo*+bestaudio/best`; the generated
TypeScript request type requires it explicitly. Inspect the returned status:
a broker publication failure can return a created record with `status: 'failed'`.
For batches, inspect `failedDownloads` and retry only unsuccessful members.
A transport failure is ambiguous; requests do not have idempotency keys.

### Read history

```typescript
import { apiClient } from '@/services/api/client'

const history = await apiClient.getDownloadHistory({
  status: 'completed',
  limit: 20,
  offset: 0,
})

console.log(history.totalDownloads)
history.items?.forEach((item) => {
  console.log(item.title, item.fileSize)
})
```

Check optional or nullable fields before using them. Treat the generated schema
as the contract rather than assuming every response contains media metadata.

### Use TanStack Query

```typescript
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'

export function useCompletedHistory() {
  return useQuery({
    queryKey: ['history', 'completed'],
    queryFn: () => apiClient.getDownloadHistory({ status: 'completed', limit: 20 }),
  })
}
```

Reuse existing hooks in [src/hooks](src/hooks/) when they cover the view's needs,
including query invalidation and SSE updates. Avoid adding independent polling
for views already maintained by the event hooks.

## Authentication and errors

The client obtains credentials through the shared session service, sends bearer
headers, coordinates refreshes, and retries an authenticated request after a
successful refresh. Do not refresh independently in components: refresh tokens
are single-use, and the shared service handles cross-tab coordination.

HTTP failures use the shared [HTTP error handling](src/services/http.ts).
Handle errors in the query or calling UI. Cancellation and timeout support live
in the client and HTTP helpers; reuse these rather than duplicating fetch logic.
File downloads use `apiClient.downloadFile(path)` to retrieve a `Blob` with the
same authentication handling.

EventSource connections require scoped short-lived SSE tokens obtained through
authenticated requests. Use the existing SSE hooks instead of putting access or
refresh JWTs in URLs. Logout, account changes, and credential revocation can
invalidate an event stream.

## Administrator settings

`apiClient.getAdminConfig()` reads startup settings for the responding API
process. **Breaking API behavior:** runtime configuration updates are unsupported;
`updateAdminConfig()` rejects with HTTP 501 for valid requests. Change deployment
environment settings and restart affected processes instead.

Signup policy has its own persisted endpoint and client method,
`updateSignupSetting(enabled)`. See the
[configuration guide](../../docs/CONFIGURATION.md#admin-configuration-api).

## Related code

- [API client](src/services/api/client.ts)
- [Session coordinator](src/services/session.ts)
- [Authentication service](src/services/auth.ts)
- [API client tests](src/services/__tests__/apiClient.test.ts)
- [Backend JSON conventions](../hermes-api/docs/API_CONVENTIONS.md)
