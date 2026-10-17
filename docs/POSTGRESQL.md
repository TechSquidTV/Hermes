# PostgreSQL and SQLite deployments

Hermes supports SQLite with `aiosqlite` and PostgreSQL with `asyncpg` as explicit
backends. Both drivers ship in the API image. SQLite remains the default for a
single-host installation. PostgreSQL is suitable for shared database access by
the API and Celery processes; media directories must still be shared separately.

Set the same connection URL for the API, worker and scheduler:

```dotenv
HERMES_DATABASE_URL=postgresql+asyncpg://hermes:password@db.example.com:5432/hermes
```

Use `sqlite+aiosqlite:///./data/hermes.db` for SQLite. The driver prefix is required;
Hermes rejects synchronous driver URLs and unsupported backends. It does not
rewrite URLs or switch databases after connection failures. URL-encode special
characters in usernames/passwords (for example `%40` for `@` and `%25` for `%`).
With asyncpg, use `?ssl=verify-full` for a remote server with a trusted certificate;
use its hostname matching the certificate and configure the system CA trust.
Do not use libpq's `sslmode` parameter with asyncpg.

The production Compose files already pass `.env` to all three backend processes.
For an external database, its hostname must be reachable from the containers;
`localhost` means the current container. Provision the database and a dedicated
role with schema/table/index/type creation and alteration privileges before
starting Hermes. PostgreSQL is not silently provisioned by the default stack.
For a Compose-managed database, add a PostgreSQL service on `hermes-network`,
a persistent data volume, and a `pg_isready` health check; make the API depend on
that service being healthy. Keep the database port private to that network.

## Schema and startup

Back up the database before upgrading. The image entrypoint runs `alembic upgrade
head` and exits if migrations fail. For native installs, run from
`packages/hermes-api` with `HERMES_SECRET_KEY` and `HERMES_DATABASE_URL` set:

```sh
uv sync --locked
uv run --locked alembic upgrade head
uv run --locked uvicorn app.main:app
```

Run migrations once before rolling out multiple API replicas; do not run
concurrent Alembic upgrades. Startup's `create_all` supports fresh development
databases but cannot upgrade an existing schema. Workers/scheduler must use the
same migrated database. Each process uses at most 10 pooled connections plus 20
overflow connections; budget the server connection limit for all processes.

Timestamps retain the existing schema: timezone-naive UTC in the database.
Aware input values are normalized to UTC; naive input values mean UTC.
PostgreSQL media byte fields and view counts use 64-bit integers, matching
SQLite's supported integer range.

**Breaking configuration warning:** only `sqlite+aiosqlite` and
`postgresql+asyncpg` URLs are accepted. There are no driver aliases or fallback
backends. Existing SQLite installations using the documented URL keep working.
Downgrading the 64-bit PostgreSQL counters fails if records exceed the old
32-bit range; archive those records before downgrading. Changing the URL from
SQLite to PostgreSQL creates/selects a different database; it does not transfer
existing users, settings or download records. Plan a separate data migration and
backup/restore exercise if transferring an existing installation.

## Real PostgreSQL validation

The `PostgreSQL integration` GitHub Actions workflow provisions PostgreSQL 17,
checks a clean migration upgrade/downgrade/re-upgrade with runtime writes, then
runs the API, integration, services and task tests against it. Offline SQL
compilation alone does not prove PostgreSQL runtime support.

To reproduce locally, provision an **empty, disposable** PostgreSQL database and
run these commands separately from `packages/hermes-api`:

```sh
# Destroys/recreates the schema; never use a production database.
HERMES_TEST_POSTGRES_URL='postgresql+asyncpg://hermes:test@localhost/hermes_test' \
  uv run --locked pytest tests/test_db --no-cov

# Each test creates/drops application tables. Use the same now-empty test DB.
HERMES_TEST_DATABASE_URL='postgresql+asyncpg://hermes:test@localhost/hermes_test' \
  uv run --locked pytest tests/test_api tests/test_integration tests/test_services tests/test_tasks --no-cov

# Default SQLite regression suite (does not inherit HERMES_DATABASE_URL).
uv run --locked pytest --no-cov
```

Do not set both test variables simultaneously: the migration target must start
empty. Without `HERMES_TEST_POSTGRES_URL`, the PostgreSQL migration test reports
an explicit skip. The normal test suite always isolates SQLite data in a temporary
directory unless `HERMES_TEST_DATABASE_URL` is explicitly supplied.
