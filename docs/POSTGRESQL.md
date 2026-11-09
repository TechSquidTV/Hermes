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

Back up the database before upgrading. API startup runs locked migrations and
exits if they fail; worker/scheduler entrypoints verify the schema without
changing it. For native installs, run from
`packages/hermes-api` with `HERMES_SECRET_KEY` and `HERMES_DATABASE_URL` set:

```sh
uv sync --locked
uv run --locked alembic upgrade head
uv run --locked uvicorn app.main:app
```

Use the [managed upgrade flow](UPGRADING.md) for the bundled prebuilt stack.
API startup and online Alembic commands share a database migration lock. Native
startup applies migrations too; recognized unversioned native schemas are
validated before baselining. Workers/scheduler must use the
same migrated database. For PostgreSQL, each process uses at most 10 pooled connections plus 20
overflow connections; budget the server connection limit for all processes.
Celery task wrappers dispose database connections before their temporary event
loop closes, so successive tasks cannot reuse connections from a closed loop.
The API retains pooling on its application event loop. Use Celery's default
`prefork` pool (or `solo` for single-process debugging). Thread, gevent and
eventlet pools and concurrent eager task execution are unsupported: each worker
process must execute only one task/event loop at a time.

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

The migration chain includes the already-published managed-path revision
`e7f31a92c604`, then the PostgreSQL counter revision `f2a84c6d901b` and the
worker heartbeat revision `a7c4e19d82b6`.
Run the complete upgrade online with the download filesystem mounted; the
managed-path step intentionally rejects SQL-only generation. Counter SQL can be
inspected separately with `alembic upgrade e7f31a92c604:f2a84c6d901b --sql`.

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


## SQLite contention and connection lifetime

File-backed SQLite connections are not pooled: closing a request or task session
releases its connection before the owning event loop ends. In-memory databases
retain their single shared connection. PostgreSQL pooling remains unchanged.
Migration/startup initializes persistent WAL journaling under the existing
migration lock, before workers start, and refuses startup if WAL cannot be set.
Connection lock waits are bounded to five seconds. Use a supported SQLite build
with the applicable WAL fixes; keep SQLite data on a local filesystem supporting
shared memory and file locks, not a network share.

WAL permits a reader and writer to progress concurrently; it still permits only
one writer. Keep transactions short and do not hold them over downloads, network
calls or progress waits. Task sessions must close even on errors or cancellation;
engine disposal alone does not close checked-out sessions.

Detailed health reads the users table rather than only evaluating `SELECT 1`.
SQLite busy/locked errors reaching the API return HTTP 503 with `Retry-After: 5`
and a generic `database_busy` error. Credentials are not rejected as invalid and
the server does not automatically retry login, refresh or other mutations.

**Operational change:** SQLite now uses persistent WAL journaling. Use the online
backup command or a consistent stopped-process snapshot; copying a live `.db`
file alone can omit committed WAL data. Never delete journal, WAL or shared-memory
files to clear a lock. Restore only with all backend processes stopped, using the
matched backup/configuration/images described in [upgrade recovery](UPGRADING.md).
