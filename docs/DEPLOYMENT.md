# Deployment guide

Start with the [quick start](../README.md#quick-start) for installation, the
[configuration reference](CONFIGURATION.md) for settings, and the
[proxy guide](PROXY_DEPLOYMENT.md) for HTTPS and domain routing. This guide covers
persistent storage, operations, and troubleshooting for the bundled stack.

## Choose a stack

| Compose file | Purpose | Public ports by default |
| --- | --- | --- |
| `docker-compose.yml` | Build the current checkout for production | App: 3000 |
| `docker-compose.example.yml` | Deploy one exact prebuilt release | App: 3000 |
| `docker-compose.dev.yml` | Develop with source mounts and hot reload | App: 5173, API: 8000, Redis: 6379 |

Each stack includes `app`, `api`, `celery_worker`, `celery_beat`, and `redis`.
Use matching code or image versions for all Hermes services. Run one scheduler
per deployment. SQLite is the default; see [PostgreSQL](POSTGRESQL.md) to opt in.

## Backend security upgrade

This upgrade includes breaking authentication and download behavior. Before
rolling it out, drain older queued tasks, then restart the API, workers, and beat
together. The old sequential batch task is removed, and single-download task IDs
now match their download UUIDs.

Users must sign in again because earlier JWTs do not contain the required session
claim. Renew SSE tokens after restarting: progress, token, and event-channel
Redis names now use the `hermes:` namespace. Refresh tokens can be exchanged only
once; the bundled frontend coordinates concurrent exchanges, and other clients
must serialize refresh requests and store both replacement tokens.

The following API changes apply:

- `/api/v1/info/` requires authenticated READ access.
- URLs must use HTTP or HTTPS and resolve to public addresses. Private, local,
  reserved, credential-bearing, and non-HTTP URLs are rejected, including
  redirects and secondary media requests. Media requiring an external network
  downloader is refused. Local ffmpeg merging and conversion remain supported.
- `cookieFile` and `browserCookies` are removed from download requests.
  Caller-supplied cookie values remain supported.
- Output directories must resolve inside `HERMES_DOWNLOAD_DIR`. The API and
  worker must share that root. UUIDs prefix default and custom output filenames;
  download status reports return a path relative to the download root, including subdirectories.
- Cleanup and file deletion require administrator users or administrator API
  keys.

New installations disable public signup after bootstrap. Review the saved signup
setting on existing installations if public registration should be disabled.
Default access and refresh lifetimes are 15 minutes and seven days, respectively;
explicit settings still take precedence. Token revocation is mandatory, and
`HERMES_ENABLE_TOKEN_BLACKLIST` has been removed.

Authentication budgets are shared through Redis. With limiting enabled, Redis
outages temporarily disable login, signup, and refresh. Configure
`HERMES_TRUSTED_PROXY_HOSTS` with exact trusted proxy IPs or DNS names before using
forwarded client addresses; Compose defaults to its frontend service, `app`.
Wildcard CORS origins cannot be combined with credentials.

Automatic retention is off by default. Set `HERMES_DOWNLOAD_RETENTION_DAYS` only
when hourly deletion of old managed downloads is desired. Preview the cleanup
with its `dryRun` JSON field before enabling scheduled deletion. See the
[configuration guide](CONFIGURATION.md) for the updated settings.

## Compose scheduler and release upgrade

Use the [one-command upgrade and recovery flow](UPGRADING.md) for prebuilt
deployments. It coordinates worker draining, consistent backups, migrations and
matching component versions. Direct `pull`/`up` remains appropriate for initial
installation; it does not provide an upgrade backup or drain work.

The bundled source, prebuilt, and development stacks now include `celery_beat`.
It schedules temporary-file cleanup every 30 minutes and expired-token blacklist
cleanup hourly. Media deletion stays opt-in through
`HERMES_DOWNLOAD_RETENTION_DAYS`. Run one scheduler per deployment; its schedule
state persists in `/app/data/celerybeat-schedule*` on the database mount.

**Breaking deployment change:** prebuilt deployments require one explicit
`HERMES_IMAGE_TAG` for app, API, worker, and scheduler. Use images and Compose
files from the same hardened release. The old 0.6.0 images scheduled media
retention unconditionally when beat ran and must not be used with these new
files. Build unreleased `main` from source until a matching release is published.

API documentation and schema moved to `/api/v1/docs`, `/api/v1/redoc`, and
`/api/v1/openapi.json`, which work through nginx. Update direct API bookmarks
that used `/docs` or `/openapi.json`. The unused `HERMES_APP_PORT`,
`HERMES_HTTPS_PORT`, and `HERMES_REDIS_DB` settings have been removed; use
`HERMES_PORT` for the public host port and the Redis URL suffix for its database.

## Persistent storage

Paths below are relative to the repository or installation directory:

| Host path | Container path | Contents |
| --- | --- | --- |
| `data/data` | `/app/data` | SQLite database, migration lock, scheduler state, and database backups |
| `data/downloads` | `/app/downloads` | Managed media, subtitles, and thumbnails |
| `data/temp` | `/app/temp` | Temporary processing files |
| Compose Redis volume | `/data` in Redis | Broker and Redis persistence data |

All backend services share the same database URL, Redis URL, and storage roots.
An external PostgreSQL server needs its own persistence and backup arrangements.
Changing the database URL does not transfer an existing installation's data.

### Ownership

The backend image runs as UID/GID 1000 by default. Prepare mounts before startup:

```bash
mkdir -p data/data data/downloads data/temp
sudo chown -R 1000:1000 data
```

For source builds, set `USER_UID` and `USER_GID` in `.env` to match the intended
host owner, then rebuild the API, worker, and scheduler together. Prebuilt images
use the image's existing UID/GID. Avoid world-writable storage permissions.

### Cleanup and retention

The scheduler enqueues temporary-file cleanup every 30 minutes and expired-token
cleanup hourly. Temporary cleanup defaults to files older than 24 hours, protects
active outputs, and skips symlinks. Do not delete files belonging to active tasks
with a host cron job.

Media retention is disabled unless `HERMES_DOWNLOAD_RETENTION_DAYS` is set.
Preview administrative cleanup with `dryRun` before enabling scheduled deletion.
See [managed files](MANAGED_FILES.md) for deliverable tracking and migration limits.

## Production operations

Set a generated `HERMES_SECRET_KEY`, keep `HERMES_DEBUG=false`, restrict CORS to
actual frontend origins, and terminate HTTPS at your external reverse proxy.
Review the saved signup policy and remove seeded administrator passwords from
`.env` after bootstrap. Configured service API keys have administrator permissions;
store them as secrets. See [configuration](CONFIGURATION.md).

The production app container serves static files through nginx and proxies `/api`
to the internal API. Keep the default `VITE_API_BASE_URL=/api/v1` unless the API
has a separate browser-facing origin. Do not expose Redis publicly.

For a source build, from the repository root:

```bash
docker compose up -d --build --wait
```

For a **new prebuilt installation**, use the target release's Compose files and
one exact `HERMES_IMAGE_TAG`:

```bash
docker compose -f docker-compose.example.yml pull
docker compose -f docker-compose.example.yml up -d --wait
```

For an **existing prebuilt installation**, use the target release's upgrade tool:

```bash
python3 scripts/upgrade.py 1.2.3  # Replace with the selected published version.
```

Read [upgrades and recovery](UPGRADING.md) before deployment. Direct Compose
replacement does not drain work or create an upgrade backup. Image-only rollback
is unsafe after a schema migration; recovery must restore a matching database,
configuration, and images. Snapshot restoration discards later database writes.

## Monitoring and health

| Endpoint | Meaning |
| --- | --- |
| `/api/v1/health/` | API liveness and version metadata |
| `/api/v1/health/ready` | Database, Redis, and release-schema readiness; returns 503 when unavailable |
| `/` | Frontend availability |

For the default production stack:

```bash
curl --fail http://localhost:3000/api/v1/health/ready
docker compose ps
docker compose logs --tail=100 api celery_worker celery_beat
```

Monitor storage capacity, queue length, worker health, Redis memory, and failed
downloads. Keep Redis's `noeviction` policy: evicting broker keys can silently lose
queued work. A full broker rejects publication instead, allowing Hermes to report
it as a download failure.

The sidebar reports current app/API versions and checks published component Git
tags for updates. Separately, open browser tabs check the deployed frontend build
and offer a Reload button when it changes. GitHub update availability does not
control that deployed-build check.

## Backups

Use the built-in backup command for a consistent SQLite snapshot or PostgreSQL
dump. From the installation directory, choose a new backup path each time:

```bash
docker compose -f docker-compose.example.yml run --rm --no-deps \
  --entrypoint python api -m app.manage backup \
  /app/data/backups/manual-$(date +%Y%m%d_%H%M%S)
```

For a source-build stack, use `-f docker-compose.yml` instead. Database snapshots
are stored under the host `data/data/backups` mount. Copy them to separate storage
along with `.env`, the selected Compose files and overrides, media, and scheduler
state. Configuration and recovery records contain secrets; restrict access.
Do not copy a live SQLite database file as a substitute for a consistent snapshot.

Managed upgrades retain their own backup and `.hermes-upgrades/<upgrade-id>`
recovery record. Keep these together, plus the previous images, until the release
is accepted. Rehearse restoration against a disposable database. See
[backup and native procedures](UPGRADING.md#backups-and-native-deployments) and
[failed-upgrade recovery](UPGRADING.md#failed-upgrades-and-recovery).

## Troubleshooting

Use the same Compose file, environment, and project identity as the running stack.
Examples below use the source-build file; add
`-f docker-compose.example.yml` or `-f docker-compose.dev.yml` as appropriate.

```bash
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 celery_worker
docker compose logs --tail=100 celery_beat
docker compose logs --tail=100 app
docker compose logs --tail=100 redis
```

| Symptom | Check |
| --- | --- |
| Container will not start | Required secret, writable mount paths, image version alignment, and port conflicts |
| Database connection fails | URL driver, database reachability and credentials; `localhost` inside a container refers to that container |
| Download fails | Returned status/message, worker logs, disk capacity, and outbound access to the media site |
| Login or refresh returns 503 | Redis health; authentication budgets depend on Redis when enabled |
| Authentication fails | Shared secret across processes, token expiry/revocation, saved signup policy, and CORS |
| Progress stops updating | Scoped SSE token renewal, proxy buffering, and long-lived connection timeouts; see the proxy guide |
| Worker rejects schema | Start the matching API or run the migration procedure before workers and scheduler |
| API returns maintenance 503 | Inspect the upgrade recovery record; follow recovery before reopening traffic |

For native diagnostics, `HERMES_DATABASE_ECHO=true` enables SQL logging. Disable
it again after investigation and avoid debug logging in production.

Do not use `pnpm clean:all` to troubleshoot a deployment: it deletes persistent
application data and volumes. Before reporting an issue, collect relevant logs
and reproduction steps and remove secrets and private media URLs.

## Worker capacity

The bundled worker uses concurrency 1. Source and prebuilt Compose files assign
fixed worker names, so remove `container_name` and give workers unique node names
before creating replicas. Keep their database, broker, and storage settings aligned.
The managed upgrade tool supports the bundled single-worker topology and rejects
extra workers; custom replicas need their own coordinated drain procedure.

For PostgreSQL use Celery's default `prefork` pool, or `solo` for single-process
debugging. Thread, gevent, and eventlet pools are unsupported. See
[PostgreSQL connection and worker guidance](POSTGRESQL.md#schema-and-startup)
when budgeting database connections.
