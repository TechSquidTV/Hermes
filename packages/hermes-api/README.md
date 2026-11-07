# Hermes API

FastAPI service for metadata extraction, background video downloads, queue
management, and managed media delivery. Celery runs downloads and maintenance
jobs; Redis supplies the broker, progress events, and authentication budgets.
SQLite is the default database, with PostgreSQL available as an explicit opt-in.

## Run with Docker

Use the repository's [quick start](../../README.md#quick-start) for the complete
stack or [contributing guide](../../docs/CONTRIBUTING.md) for hot reload. Run
Compose from the repository root. The production stack exposes the app on port
3000 and keeps the API internal; the development stack also exposes the API on
port 8000.

| Documentation | Production stack | Development API |
| --- | --- | --- |
| Swagger UI | [API docs](http://localhost:3000/api/v1/docs) | [API docs](http://localhost:8000/api/v1/docs) |
| ReDoc | [ReDoc](http://localhost:3000/api/v1/redoc) | [ReDoc](http://localhost:8000/api/v1/redoc) |
| OpenAPI | [Schema](http://localhost:3000/api/v1/openapi.json) | [Schema](http://localhost:8000/api/v1/openapi.json) |

These live documents describe the full request and response contracts. See
[API conventions](docs/API_CONVENTIONS.md) for JSON field naming.

## Native development

Install Python 3.11+, uv, Redis, and FFmpeg. For yt-dlp JavaScript challenge
solving, install a supported JavaScript runtime; Docker includes Node 26.

From `packages/hermes-api`:

```bash
uv sync --locked --all-groups
mkdir -p data downloads temp

# Export the same settings in each API, worker, and scheduler terminal.
# Set HERMES_SECRET_KEY to a generated value and reuse it across processes.
export HERMES_SECRET_KEY=replace-with-your-generated-secret
export HERMES_DATABASE_URL=sqlite+aiosqlite:///./data/hermes.db
export HERMES_REDIS_URL=redis://localhost:6379/0
export HERMES_DOWNLOAD_DIR="$PWD/downloads"
export HERMES_TEMP_DIR="$PWD/temp"
```

Generate the secret with
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. The Python app
does not load the root `.env` automatically. See the
[configuration guide](../../docs/CONFIGURATION.md#docker-defaults-and-native-development)
for Docker versus native settings.

Start Redis separately, then launch the API:

```bash
redis-server
```

```bash
uv run --locked uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API startup applies database migrations. Once it is ready, start the worker and
one scheduler in separate terminals with the same settings and working directory:

```bash
uv run --locked celery -A app.worker worker --loglevel=info --concurrency=1 --queues=hermes.downloads,hermes.cleanup,hermes.default
```

```bash
uv run --locked celery -A app.worker beat --loglevel=info --schedule=./data/celerybeat-schedule
```

Worker and scheduler processes require the migrated schema. Do not run native
processes alongside Compose services against the same deployment. PostgreSQL
worker-pool requirements are covered in the [database guide](../../docs/POSTGRESQL.md).

## Authenticated usage

Sign up through the web app, then create an API key in settings. Send that key
as `Authorization: Bearer <key>`; user access JWTs use the same header. Metadata
lookup requires `read` permission and download creation requires `download`.
User administration, cleanup, and file deletion require administrator access.
API-key management itself requires a user session.

This standalone Python example uses HTTPX from the API environment. Set
`HERMES_API_KEY` in the launching environment first:

```python
import asyncio
import os

import httpx


async def main() -> None:
    async with httpx.AsyncClient(
        base_url="http://localhost:3000/api/v1/",
        headers={"Authorization": f"Bearer {os.environ['HERMES_API_KEY']}"},
        timeout=30,
    ) as client:
        response = await client.get(
            "info/", params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        )
        response.raise_for_status()
        print(response.json()["title"])

        response = await client.post(
            "download/",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "downloadSubtitles": True,
            },
        )
        response.raise_for_status()
        download = response.json()
        print(download["downloadId"], download["status"], download["message"])


asyncio.run(main())
```

Use port 8000 for native or direct development API access. A successful HTTP
response does not guarantee broker publication: inspect the returned `status`
and `message`. Poll `GET /api/v1/download/{id}` or use scoped SSE credentials to
follow progress. Batch responses identify individual publication failures in
`failedDownloads`; retry those items rather than resubmitting successful ones.

## Endpoint overview

| Area | Selected routes |
| --- | --- |
| Health | `GET /api/v1/health/`, `GET /api/v1/health/ready` |
| Metadata | `GET /api/v1/info/` |
| Downloads | `POST /api/v1/download/`, `POST /api/v1/download/batch`, `GET /api/v1/download/{id}`, `POST /api/v1/download/{id}/cancel` |
| Queue | `GET /api/v1/queue/` |
| Files | `GET /api/v1/files/`, `GET /api/v1/files/download`, `DELETE /api/v1/files/` |
| Authentication | `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` |
| API keys | `POST /api/v1/auth/api-keys`, `GET /api/v1/auth/api-keys`, `DELETE /api/v1/auth/api-keys/{id}` |
| Live events | `POST /api/v1/events/token`, `GET /api/v1/events/stream` |

Use Swagger UI for route parameters, permissions, and additional endpoints.
Refresh tokens are single-use: serialize refresh requests and store both
replacement tokens. Browser event streams use short-lived scoped SSE tokens.

## Download defaults and storage

The default format and the UI's **Best Quality** option use
`bestvideo*+bestaudio/best`. FFmpeg merges separate streams and is bundled in
Docker.

**Breaking behavior change:** omitting a format can select higher resolutions
and larger files than the old `best` default. Explicit selectors keep their
yt-dlp meaning; `best` requests a pre-merged stream and may fail when none exists.
Existing queued jobs retain their selector and must be recreated to use the new
default.

Output directories must stay inside `HERMES_DOWNLOAD_DIR`, shared by API and
workers. Status and file responses use paths relative to that root. The worker
registers media, subtitles, and thumbnails as managed deliverables; see
[managed files](../../docs/MANAGED_FILES.md). Media retention is opt-in.

## Development checks

Run from `packages/hermes-api`:

```bash
uv run --locked pytest
uv run --locked black --check app/ tests/
uv run --locked isort --check-only app/ tests/
uv run --locked ruff check app/ tests/
uv run --locked python -m mypy --explicit-package-bases app/ tests/
```

Mypy runs in strict mode across the application and tests. Use SQLAlchemy
`Mapped` attributes, typed fixtures, and explicit optional values. Celery and
Kombu imports are confined to library boundaries. Local yt-dlp contracts live
in [typings](typings/README.md); update them when changing that integration.

See [testing](tests/README.md), [configuration](../../docs/CONFIGURATION.md),
[deployment](../../docs/DEPLOYMENT.md), and [upgrades](../../docs/UPGRADING.md).
Hermes is licensed under [AGPL-3.0](../../LICENSE).
