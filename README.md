# Hermes — Self-Hosted Video Downloader

[![codecov](https://codecov.io/gh/TechSquidTV/Hermes/branch/main/graph/badge.svg)](https://codecov.io/gh/TechSquidTV/Hermes)

**Download videos from YouTube and 1000+ sites with a robust API and beautiful, modern interface**

Hermes is a self-hosted video downloader built on [yt-dlp](https://github.com/yt-dlp/yt-dlp).

_This tool is designed for content creators who wish to **lawfully** use freely available media under [fair use](https://en.wikipedia.org/wiki/Fair_use) (best explained by [Tom Scott](https://www.youtube.com/watch?v=1Jwo5qc78QU)).
Hermes **does not endorse** piracy, freebooting, or using downloads to bypass advertising._

https://github.com/user-attachments/assets/7d9c6b96-d966-4989-a8b3-d5d49af463ae

## Key Features

- 🎥 **Universal Support** - Download from YouTube, Vimeo, TikTok, and 1000+ sites
- ⚡ **Background Processing** - Queue downloads and process them asynchronously
- ▶️ **Playlists** - Download entire playlists asynchronously
- 🔒 **Secure Authentication** - JWT tokens with API key management and admin user control
- 👥 **User Management** - Admin controls for self-hosted deployments with configurable signup

## Quick Start

### Build the current checkout

For unreleased `main`, build from source so the app, API, worker, and scheduler
include the same fixes.

```bash
git clone https://github.com/techsquidtv/hermes.git
cd hermes
cp .env.example .env

# Set a random HERMES_SECRET_KEY in .env before starting.
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
nano .env

# Prepare the bind mounts for the default container user (UID/GID 1000).
mkdir -p ./data/downloads ./data/temp ./data/data
sudo chown -R 1000:1000 ./data

docker compose up -d --build --wait
```

The web app is at http://localhost:3000 and the interactive API documentation is
at http://localhost:3000/api/v1/docs. Redis and the API stay on the internal
Docker network.

### Prebuilt release images

Use `docker-compose.example.yml` and `.env.example` from the release you deploy.
Set `HERMES_IMAGE_TAG` in `.env` to that exact published version, without a `v`
prefix. The same tag selects the frontend, API, worker, and scheduler images.
There is no independent `latest` selection.

**Release requirement:** the new scheduler requires a release containing the
security and opt-in retention fixes. Published 0.6.0 images predate them. Until a
hardened release is published, use the source-build instructions above for these
changes.

After selecting a compatible release and preparing the same data directories:

```bash
docker compose -f docker-compose.example.yml pull
docker compose -f docker-compose.example.yml up -d --wait
```

For upgrades, update the single `HERMES_IMAGE_TAG`, pull, and recreate the entire
stack together. See the [deployment guide](docs/DEPLOYMENT.md) before upgrading
an existing installation.

### Development with hot reload

Use the same `.env` and persistent directories:

```bash
docker compose -f docker-compose.dev.yml up --build --wait
```

The Vite app is at http://localhost:5173, with API requests and documentation
proxied under `/api/v1`. Direct debugging access is http://localhost:8000; Redis
is exposed only by the development stack. For native processes, change the Redis
hostname and storage paths as described in the
[configuration guide](docs/CONFIGURATION.md#docker-defaults-and-native-development).

### Persistent directories and maintenance

The bundled stacks mount `data/downloads` at `/app/downloads`, `data/temp` at
`/app/temp`, and `data/data` at `/app/data`. These directories must be writable
by the backend container user. Source builds accept `USER_UID` and `USER_GID` to
match a different host owner; set those build arguments and rebuild all backend
services together.

One `celery_beat` process schedules temporary-file and expired-token cleanup.
Media retention is off unless `HERMES_DOWNLOAD_RETENTION_DAYS` is set. Scheduler
state is kept beside the database in `data/data`; run only one scheduler per
deployment.

### Using a Reverse Proxy

The default setup exposes the `hermes-app` nginx container on port 3000. That container serves the UI and proxies `/api/*` to the internal API service, so no bundled reverse proxy is required.

For production HTTPS, put your existing reverse proxy in front of the app container and forward traffic to port 80. Preserve the `Host` header and pass `X-Forwarded-Proto`.

#### Domain Configuration Options

**Single Domain** (Recommended for most users):
- Frontend and API on same domain: `hermes.example.com`
- API accessible at: `hermes.example.com/api/`

**Separate Domains** (Advanced):
- Frontend at: `hermes.example.com`
- API at: `hermes-api.example.com`

#### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# For single domain
HERMES_ALLOWED_ORIGINS=https://hermes.example.com
VITE_API_BASE_URL=/api/v1

# For separate domains
HERMES_ALLOWED_ORIGINS=https://hermes.example.com,https://hermes-api.example.com
VITE_API_BASE_URL=https://hermes-api.example.com/api/v1
```

See our [Proxy & Deployment Guide](docs/PROXY_DEPLOYMENT.md) for integrating with existing setups (Traefik, nginx, etc.) and deploying with separate subdomains.

## 🔒 Self-Hosting Security

Hermes includes security features designed specifically for self-hosted deployments:

### Signup Control

Public signup is disabled by default after the first account is created. Administrators can create additional accounts or explicitly enable public signup. Existing installations retain their saved signup setting.

**Option 1: First User Becomes Admin** (Default)
- The first user to sign up automatically gets admin privileges
- Subsequent users can only sign up if public signup is enabled
- Simple for personal deployments

**Option 2: Disable Public Signup**
```bash
# In your .env file:
HERMES_ALLOW_PUBLIC_SIGNUP=false
```
- Only administrators can create new accounts via admin panel
- Prevents unauthorized account creation
- Recommended for shared/exposed deployments

**Option 3: Pre-seed Initial Admin** (Docker-friendly)
```bash
# In your .env file:
HERMES_INITIAL_ADMIN_USERNAME=admin
HERMES_INITIAL_ADMIN_EMAIL=admin@example.com
HERMES_INITIAL_ADMIN_PASSWORD=changeme123
```
- Admin account created automatically on first startup
- Perfect for Docker deployments and automation
- **Important**: Change the password after first login!

### Admin User Management

Administrators have access to user management features:
- **Create users** - Add accounts when public signup is disabled
- **Promote/demote admins** - Grant admin privileges to trusted users
- **Activate/deactivate accounts** - Disable access without deleting users
- **Delete users** - Permanently remove accounts
- **Safety checks** - Cannot delete yourself or the last admin

Access admin features via: **API endpoints at `/api/v1/users`** (see [API docs](http://localhost:3000/api/v1/docs))

### Security Best Practices

1. **Set a strong secret key**: Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
2. **Disable public signup** for non-personal deployments: `HERMES_ALLOW_PUBLIC_SIGNUP=false`
3. **Change default credentials** if using pre-seeded admin
4. **Use HTTPS** in production with your reverse proxy or load balancer
5. **Restrict CORS origins** to your actual domains in `.env`
6. **Keep Hermes updated** to get the latest security patches

### 🐛 Having Issues?

If you run into problems, please use our [issue templates](https://github.com/techsquidtv/hermes/issues/new/choose) instead of generic issues:
- **[🐛 Bug Report](https://github.com/techsquidtv/hermes/issues/new?template=bug_report.yml)** - For unexpected behavior
- **[🔧 API Issues](https://github.com/techsquidtv/hermes/issues/new?template=bug_report.yml)** - Backend problems
- **[🎨 Frontend Issues](https://github.com/techsquidtv/hermes/issues/new?template=bug_report.yml)** - UI/UX problems
- **[🐳 DevOps Issues](https://github.com/techsquidtv/hermes/issues/new?template=bug_report.yml)** - Docker/deployment issues

These templates help us help you faster!

### Manual Installation (Development)

For development and contribution purposes, use Node.js 22.22.2+ (22.x), 24.15+ (24.x), or 26+ (used in Docker and CI), pnpm 12.3.4, and Python 3.11+ (Python 3.14 in Docker and CI). Corepack uses the pnpm version pinned in `package.json`. Node 26 requires installing Corepack separately; the Docker builds use its pinned root development dependency.

**Breaking tooling update:** pnpm 10 and Node versions outside those ranges are no longer supported. Run `corepack enable` and `pnpm install` after pulling. TypeScript remains on 6.0.3 because the current ESLint and OpenAPI tooling does not support the TypeScript 7 compiler API.

```bash
# Install the repository's Corepack version, then enable pnpm
npm install --global "corepack@$(node -p 'require("./package.json").devDependencies.corepack')"
corepack enable pnpm

# Install dependencies
pnpm install

# Set up environment (all environment variables are configured in the root .env file)
cp .env.example .env
# Edit .env with your settings

# Start development servers
pnpm dev
```

## 📚 Documentation

- **[Configuration Guide](docs/CONFIGURATION.md)** - Complete environment variables and settings reference
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Docker volumes, production deployment, and troubleshooting
- **[Contributing Guide](docs/CONTRIBUTING.md)** - Development workflow, branch strategy, and how to contribute
- **[Release Process](docs/RELEASE_PROCESS.md)** - Version management and release workflow
- **[API Documentation](packages/hermes-api/README.md)** - Complete API reference and examples
- **[Frontend Guide](packages/hermes-app/README.md)** - React app development guide
- **[Interactive API Docs](http://localhost:3000/api/v1/docs)** - Live Swagger documentation
- **[docker-compose.example.yml](docker-compose.example.yml)** - Pre-built images deployment configuration

### 🔀 Branch Strategy

- **`main`** - Stable production releases (Docker: `latest`)
- **`develop`** - Integration branch for testing (Docker: `develop`)
- **Feature branches** - Your contributions (merge to `develop`)

Contributors: Open PRs to `develop`, not `main`. See the [Contributing Guide](docs/CONTRIBUTING.md) for details.
---

## Hosting Partner

This could be you! Bring Hermes to the world by hosting a public instance and getting featured here!
