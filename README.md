# Hermes

[![codecov](https://codecov.io/gh/TechSquidTV/Hermes/branch/main/graph/badge.svg)](https://codecov.io/gh/TechSquidTV/Hermes)

A self-hosted video downloader with a web interface and API, powered by
[yt-dlp](https://github.com/yt-dlp/yt-dlp).

- Download videos and playlists from YouTube and other yt-dlp-supported sites.
- Queue downloads in the background and follow progress in real time.
- Browse download history and retrieve media, subtitles, and thumbnails.
- Manage users and API keys with administrator controls and configurable signup.
- Run the app, API, workers, scheduler, and Redis with Docker Compose.

Use Hermes only for media you have permission to download and reuse. Hermes is
intended for lawful use by content creators and does not endorse piracy,
freebooting, or bypassing advertising.

https://github.com/user-attachments/assets/7d9c6b96-d966-4989-a8b3-d5d49af463ae

## Quick start

Install Docker with Compose 2.24.4+ and Git. The commands below build the current
checkout so all components use the same source.

```bash
git clone https://github.com/TechSquidTV/Hermes.git hermes
cd hermes
cp .env.example .env

# Generate a secret, then set HERMES_SECRET_KEY in .env to the result.
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
nano .env

# Prepare persistent directories for the default container user (UID/GID 1000).
mkdir -p data/downloads data/temp data/data
sudo chown -R 1000:1000 data

docker compose up -d --build --wait
```

Open the [web app](http://localhost:3000) and create your first account; it becomes
the administrator. Public signup is disabled afterward unless an administrator
enables it. You can also [seed an administrator](docs/CONFIGURATION.md#signup-and-initial-administrator)
before starting the stack.

| Service | Default URL |
| --- | --- |
| Web app | [localhost:3000](http://localhost:3000) |
| Interactive API docs | [Swagger UI](http://localhost:3000/api/v1/docs) |
| Alternative API docs | [ReDoc](http://localhost:3000/api/v1/redoc) |
| API readiness | [Readiness check](http://localhost:3000/api/v1/health/ready) |

The API and Redis stay on the internal Docker network. The app container serves
the UI and proxies `/api/*` to the API. For HTTPS, put your reverse proxy in front
of the app; see the [proxy guide](docs/PROXY_DEPLOYMENT.md).

### Prebuilt releases and upgrades

Use `docker-compose.example.yml` and `.env.example` from the release you deploy.
Prepare the secret and data directories as above, then set `HERMES_IMAGE_TAG` in
`.env` to that exact published version without a `v` prefix. One tag selects the
app, API, worker, and scheduler together.

**Release compatibility warning:** the 0.6.0 images predate the security and
opt-in retention fixes required by these Compose files. Use a release containing
those fixes; build the current checkout from source for unreleased changes.

For a new installation with a compatible release:

```bash
docker compose -f docker-compose.example.yml pull
docker compose -f docker-compose.example.yml up -d --wait
```

For an existing installation, use `scripts/upgrade.py` from the target release:

```bash
python3 scripts/upgrade.py 1.2.3  # Replace with the selected published version.
```

The upgrade drains work, backs up the database, migrates it, and checks replacement
services before updating `.env`. Read the [upgrade and recovery guide](docs/UPGRADING.md)
first, including its breaking changes and recovery requirements.

### Storage and maintenance

The bundled stacks persist the database and scheduler state in `data/data`,
downloads in `data/downloads`, and temporary files in `data/temp`. These directories
must be writable by the backend container user. See the
[deployment guide](docs/DEPLOYMENT.md#persistent-storage) for ownership and backups.

Run one `celery_beat` scheduler per deployment. It schedules temporary-file and
expired-token cleanup. Download retention is off unless
`HERMES_DOWNLOAD_RETENTION_DAYS` is set.

## Development

After preparing `.env` and the data directories, start the hot-reload stack:

```bash
docker compose -f docker-compose.dev.yml up --build --wait
```

The development app is at [localhost:5173](http://localhost:5173), with API docs
at [localhost:5173/api/v1/docs](http://localhost:5173/api/v1/docs). The API is also
exposed on port 8000 and Redis on port 6379 for debugging.

See [Contributing](docs/CONTRIBUTING.md) for native setup, tool versions, checks,
and the pull request workflow. Start branches from `main` and open PRs to `main`.

## Documentation

| Guide | Contents |
| --- | --- |
| [Configuration](docs/CONFIGURATION.md) | Environment variables, signup, authentication, and storage settings |
| [Deployment](docs/DEPLOYMENT.md) | Persistent storage, backups, monitoring, and troubleshooting |
| [Reverse proxies](docs/PROXY_DEPLOYMENT.md) | HTTPS, single-domain and separate-domain deployments, and SSE |
| [Upgrading](docs/UPGRADING.md) | Coordinated upgrades, migrations, and recovery |
| [PostgreSQL](docs/POSTGRESQL.md) | Optional PostgreSQL deployment and validation; SQLite is the default |
| [Managed files](docs/MANAGED_FILES.md) | Media deliverables, sidecars, and path migration requirements |
| [Contributing](docs/CONTRIBUTING.md) | Development setup, checks, and contribution workflow |
| [Release process](docs/RELEASE_PROCESS.md) | Shared versioning, image publication, and release recovery |
| [Dependency maintenance](docs/DEPENDENCY_MAINTENANCE.md) | Renovate policy, lockfiles, and dependency validation |
| [API](packages/hermes-api/README.md) | Authenticated usage, endpoint overview, and backend development |
| [Frontend](packages/hermes-app/README.md) | App development, configuration, and generated API types |

For bugs or feature requests, use the
[issue templates](https://github.com/TechSquidTV/Hermes/issues/new/choose).
Include reproduction steps and relevant logs with secrets removed.

Hermes is licensed under [AGPL-3.0](LICENSE).
