# API tests

Run commands from `packages/hermes-api` after installing dependencies with
`uv sync --locked --all-groups`. FFmpeg is required for local media-conversion
regressions; those fixtures do not need external video sites.

## Run tests

```bash
uv run --locked pytest
uv run --locked pytest tests/test_api/test_health.py -v
uv run --locked pytest tests/test_api/test_auth.py -k api_key -v
uv run --locked pytest tests/test_integration -v
uv run --locked pytest --cov=app --cov-report=html --cov-report=term
```

The project pytest configuration enables coverage by default. Add `--no-cov` for
focused runs without coverage reporting.

## Test layout

| Directory | Coverage |
| --- | --- |
| `test_api/` | HTTP contracts, authentication, permissions, queue, files, and administration |
| `test_integration/` | Download flows, sessions, deliverables, bootstrap, and dispatch recovery |
| `test_db/` | Database backends, migrations, operator commands, and deployment upgrade/recovery |
| `test_services/` | Downloader, public-network policy, events, file registration, and cleanup |
| `test_tasks/` | Celery downloads, scheduling, worker database lifecycle, and retention |
| `test_models/` | Pydantic request/response validation |

Frontend tests live in `packages/hermes-app`, not this directory. From the
repository root, run `pnpm test` for the frontend or `pnpm test:all` for both
packages.

## Fixtures and isolation

[conftest.py](conftest.py) selects a temporary SQLite database by default,
creates and drops tables per test, and supplies typed async database/client
fixtures. No manual schema creation is needed. It does not inherit an operator's
`HERMES_DATABASE_URL` for tests.

The shared `client` fixture overrides the authentication principal with an admin
API key. Tests of authentication itself must use the appropriate unmocked client
or explicit dependency setup; an overridden principal does not prove that a
credential or permission is valid. Reuse existing fixtures and isolate session,
Redis, and network state as needed.

For real PostgreSQL testing, follow the [database validation guide](../../../docs/POSTGRESQL.md#real-postgresql-validation).
The explicit test variables target **empty, disposable databases** and create or
drop schema objects. Never use them with application data, and never set both
PostgreSQL test variables at once.

## Related checks

Run `pnpm pre-check:api` from the repository root for formatting, lint, strict
mypy, and pytest. CI also verifies generated OpenAPI types, backend Docker builds,
and infrastructure tests. See [contributing](../../../docs/CONTRIBUTING.md) for
shared commands and [typing boundaries](../typings/README.md) for third-party stubs.
