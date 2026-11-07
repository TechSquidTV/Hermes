# API conventions

## JSON fields and Python names

Use the shared [CamelCaseModel](../app/models/base.py) for API request and response
models. Python attributes use snake_case; serialized JSON and OpenAPI properties
use camelCase.

```python
from app.models.base import CamelCaseModel


class ExampleResponse(CamelCaseModel):
    download_id: str
    is_complete: bool
```

Serialized JSON:

```json
{
  "downloadId": "example-id",
  "isComplete": false
}
```

The base model configures Pydantic's `to_camel` alias generator,
`populate_by_name=True`, and `from_attributes=True`. Use those shared settings
instead of copying the base model or adding manual aliases for regular field
names. Explicit aliases should be reserved for contracts the generator cannot
express. Reuse existing shared models before introducing another request or
response shape.

Inputs support Python field names through the base configuration, but client
examples and frontend code should use the canonical camelCase schema. This
naming rule applies to JSON models; query parameter names are declared by each
endpoint and may use snake_case, such as `include_formats` or `start_date`.

## Frontend contracts

Generate TypeScript types from the Python app with `pnpm generate:types` at the
repository root. No running API server is needed. Import generated schemas
instead of manually mirroring backend interfaces:

```typescript
import type { components } from '@/types/api.generated'

const request = {
  url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
  format: 'bestvideo*+bestaudio/best',
  downloadSubtitles: true,
  downloadThumbnail: false,
} satisfies components['schemas']['DownloadRequest']
```

See the [SDK guide](../../hermes-app/SDK_GUIDE.md) for client examples and the
regeneration workflow. Live schema and documentation paths are
`/api/v1/openapi.json`, `/api/v1/docs`, and `/api/v1/redoc`.

## Validation and tests

Use Pydantic field types and validators for input contracts, keep optional values
explicit, and follow the application's strict mypy settings. Tests of JSON
responses should assert serialized names such as `downloadId`, even when model
constructors use `download_id`.

When changing a contract, update endpoint tests, regenerate frontend types, and
check callers. Document breaking changes and migration requirements; do not add
compatibility aliases or fallbacks for removed fields or behavior.

- [API development](../README.md)
- [API tests](../tests/README.md)
- [Pydantic aliases](https://docs.pydantic.dev/latest/concepts/alias/)
