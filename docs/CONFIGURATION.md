# Configuration Guide

Start with `.env.example`. Docker Compose loads the root `.env` and passes its
settings to the API, worker, and scheduler. Native processes must receive these
settings through their environment or their launcher's env-file option. Relative
paths resolve from the process working directory, which is `/app` in Docker.

## Docker defaults and native development

The example is configured for the bundled Docker network and persistent mounts:

| Setting | Bundled Docker value | Native process example |
|---------|----------------------|------------------------|
| `HERMES_REDIS_URL` | `redis://redis:6379/0` | `redis://localhost:6379/0` |
| `HERMES_DATABASE_URL` | `sqlite+aiosqlite:///./data/hermes.db` | Same value when launched from `packages/hermes-api` |
| `HERMES_DOWNLOAD_DIR` | `/app/downloads` | `./downloads` from the API directory |
| `HERMES_TEMP_DIR` | `/app/temp` | `./temp` from the API directory |

API, worker, and scheduler must use the same database, Redis URL, and storage
roots. Native processes cannot resolve the Docker service hostname `redis`.
Docker processes must use the service hostname rather than `localhost`.

## API settings

These variables are read by `packages/hermes-api/app/core/config.py`.
Defaults below are application defaults; `.env.example` supplies Docker paths.

### Core and API metadata

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_SECRET_KEY` | Required | JWT signing secret. Generate a long random value before startup. |
| `HERMES_DEBUG` | `false` | Development logging and environment metadata. HTTP tracebacks remain disabled. |
| `HERMES_API_TITLE` | `Hermes API` | Title in interactive documentation. |
| `HERMES_API_DESCRIPTION` | `Video downloader API` | API description. |
| `HERMES_BUILD_VERSION` | Package version | Build metadata supplied by release builds; otherwise version comes from installed metadata or `pyproject.toml`. |

Interactive documentation is served at `/api/v1/docs` and `/api/v1/redoc`.
The schema is `/api/v1/openapi.json`. All three work through the bundled nginx
proxy. The former direct-server `/docs`, `/redoc`, and `/openapi.json` paths have
moved; update bookmarks and clients that read the schema.

### Database and Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_DATABASE_URL` | `sqlite+aiosqlite:///./data/hermes.db` | Async SQLite database URL. SQLite is the supported bundled database. |
| `HERMES_DATABASE_ECHO` | `false` | SQL query logging. |
| `HERMES_REDIS_URL` | `redis://localhost:6379` | Complete Redis URL, shared by Celery and application services. Compose defaults to the `redis` service. |

Select a Redis database in the URL, for example `redis://redis:6379/2`.
`HERMES_REDIS_DB` was unused and has been removed. There is no separate database
selector to override the URL.

### Authentication and API keys

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime, minimum one minute. |
| `HERMES_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime, minimum one day. |
| `HERMES_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `HERMES_API_KEYS` | Empty list | Configured API keys. Flexible list syntax is described below. |

Refresh tokens are single-use. Clients must serialize refresh requests and store
both replacement tokens. Logout revokes the session's access and refresh tokens.
Revocation is mandatory; `HERMES_ENABLE_TOKEN_BLACKLIST` is no longer supported.

### Signup and initial administrator

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ALLOW_PUBLIC_SIGNUP` | `false` | Initial signup policy; the saved administrator setting takes precedence afterward. |
| `HERMES_INITIAL_ADMIN_USERNAME` | Unset | Seed an administrator when the database has no users. |
| `HERMES_INITIAL_ADMIN_EMAIL` | Unset | Valid email for the seeded administrator. |
| `HERMES_INITIAL_ADMIN_PASSWORD` | Unset | Seed password: at least eight characters and at most 72 UTF-8 bytes. |

Set all three initial-admin variables to use seeding, then remove the password
from `.env` after bootstrap. Without seeding, the first signup creates an
administrator; subsequent signup follows the saved policy. Password changes use
the same length limits.

### Storage and maintenance

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_DOWNLOAD_DIR` | `./downloads` | Shared root for managed downloads. |
| `HERMES_TEMP_DIR` | `./temp` | Shared temporary processing directory. |
| `HERMES_DOWNLOAD_RETENTION_DAYS` | Unset | Opt-in hourly removal of terminal downloads older than this many days; minimum one. |

The bundled stacks run one `celery_beat` scheduler. It enqueues temporary-file
cleanup every 30 minutes (files older than 24 hours) and expired token-blacklist
cleanup hourly. It schedules media retention only when
`HERMES_DOWNLOAD_RETENTION_DAYS` is set. Preview retention with the administrative
cleanup API's `dry_run` option before enabling it. Failed file deletions keep
their download records. Never run multiple schedulers for the same deployment.

Scheduler state persists in `/app/data/celerybeat-schedule*`. API startup repairs
missing file records for existing completed media inside the managed root; the
repair skips missing files and paths or symlinks outside that root.

`HERMES_DOWNLOADS_DIR` has been removed. Use `HERMES_DOWNLOAD_DIR` and restart the
API, worker, and scheduler together. File/status responses expose paths relative
to the managed root, including subdirectories.

### Authentication budgets and proxy trust

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ENABLE_RATE_LIMITING` | `true` | Shared Redis budgets for login, signup, and refresh. A Redis outage returns 503 for these operations. |
| `HERMES_MAX_LOGIN_ATTEMPTS` | `5` | Requests per client, per authentication endpoint, per window. |
| `HERMES_LOGIN_ATTEMPT_WINDOW_MINUTES` | `15` | Budget window, minimum one minute. |
| `HERMES_TRUSTED_PROXY_HOSTS` | Empty list | Exact trusted proxy IPs or resolvable hostnames; Compose defaults to `app`. |
| `HERMES_RATE_LIMIT_PER_MINUTE` | `60` | Configuration API value; authentication uses the explicit budgets above. |

Forwarded client addresses are trusted only from configured proxies.

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173,https://hermes.example.com,https://hermes-api.example.com` | Allowed browser origins. Replace the example domains for deployment. |
| `HERMES_ALLOW_CREDENTIALS` | `true` | Allow credentials in cross-origin requests. |

Wildcard origins are rejected when credentials are enabled. For one public
origin, set `HERMES_ALLOWED_ORIGINS=https://hermes.example.com`. For a separate API
host, include the actual frontend origin; the API URL is configured separately.

`HERMES_ALLOWED_ORIGINS`, `HERMES_API_KEYS`, and `HERMES_TRUSTED_PROXY_HOSTS` accept
comma-separated strings, space-separated strings, or JSON arrays. An empty value
is an empty list.

### Server-sent events

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_SSE_HEARTBEAT_INTERVAL` | `30` | SSE heartbeat interval setting, seconds. |
| `HERMES_SSE_MAX_CONNECTIONS` | `1000` | Concurrent connection limit setting. |
| `HERMES_SSE_CONNECTION_TIMEOUT` | `300` | Reserved timeout value in seconds; stream lifetime is not currently enforced by it. |

SSE is a core feature and has no enable/disable switch. Browser connections use
short-lived scoped SSE tokens; JWTs are sent only in authenticated HTTP headers.

## Compose and frontend settings

These settings belong to Compose or the frontend rather than the API settings
model. `API_PORT` is a host-port mapping, not an API server environment setting.

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_PORT` | `3000` | Public nginx host port in production Compose. |
| `HERMES_DEV_PORT` | `5173` | Vite host port in development Compose. |
| `API_PORT` | `8000` | Direct API host port in development Compose; container port stays 8000. |
| `USER_UID`, `USER_GID` | `1000` | Source-built API/worker/scheduler user IDs; match mounted-directory ownership. |
| `HERMES_IMAGE_TAG` | Required for prebuilt stack | One exact release for app, API, worker, and scheduler. Source builds do not use it. |
| `VITE_API_BASE_URL` | `/api/v1` | Browser-facing API URL. Production Docker reads it at container startup. |
| `VITE_HERMES_BUILD_VERSION` | Package version | Frontend version metadata set during image builds. |
| `HERMES_DEV_API_TARGET` | `http://localhost:8000` | Vite's upstream proxy target; development Compose sets `http://api:8000`. |

For production Docker, changing `VITE_API_BASE_URL` requires recreating the app
container, not rebuilding the image. The entrypoint writes escaped JSON into
`config.js` on every start. Native Vite builds capture this variable at build
time and need a rebuild. Development Compose fixes the browser URL to `/api/v1`
and proxies it to the API container.

Use `/api/v1` for a single origin or
`https://hermes-api.example.com/api/v1` for a separate API origin. The nginx
container listens on HTTP port 80; terminate HTTPS in your external proxy.
`HERMES_APP_PORT` and `HERMES_HTTPS_PORT` were unused and have been removed.

## Release alignment

Use Compose files from the same release as the images and set
`HERMES_IMAGE_TAG` once for the entire prebuilt stack. Upgrade all four backend
and frontend processes together. These files require a release containing the
security and opt-in retention fixes; the old 0.6.0 images are unsuitable for the
new scheduler setup. For unreleased `main`, build from source until that release
is published.

## Secret generation and persistent volumes

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set that result as `HERMES_SECRET_KEY` in your untracked `.env`. Back up
`data/data`, `data/downloads`, and the deployment configuration. Keep `.env` out
of version control and restrict its permissions. See the
[deployment guide](DEPLOYMENT.md) for volume ownership, backup, and recovery.

### API-key owner authorization

**Breaking security change:** ordinary users cannot mint keys with `admin`
permissions. Database-backed keys require an existing, active owner on every
request. Disabling an account suspends its keys; re-enabling it restores only
keys that are still active and unexpired. Demoting an administrator removes
`admin` from its keys' effective grants, including keys issued before this fix;
explicit `read`, `write`, and `download` grants remain usable. The stored grants
are unchanged, so promotion restores the admin grant.

`HERMES_API_KEYS` are operator-managed service credentials with administrator
permissions and no user owner. User disable/demotion does not affect them;
remove them from configuration and restart the API to revoke them. They cannot
use endpoints that require a user session, including key creation.

### Admin configuration API

**Breaking API change:** `PUT /api/v1/admin/config` returns HTTP 501 for valid
requests, including empty requests. Runtime updates are unsupported; no fields
are applied. Invalid requests return validation errors. Change supported
`HERMES_*` deployment settings and restart every affected API process, Celery
worker and Celery beat process. There is no cross-process runtime propagation.
Worker concurrency is controlled by worker launch options, and download options
belong on individual download requests.

`GET /api/v1/admin/config` reports only non-secret startup settings of the
responding API process: directories, configured media retention age, authentication attempt limit and window, whether authentication rate limiting is
enabled, and debug mode. Authentication limits are enforced only when enabled. This response does not inspect worker or scheduler
state. The former hardcoded download, concurrency, retry, timeout, unused global rate limit and cleanup
fields were removed because they did not describe effective consumer behavior.
The database-backed signup setting retains its dedicated `/admin/settings/signup`
endpoint.
