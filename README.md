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
- 🔒 **Secure Authentication** - JWT tokens with API key management

## Quick Start

### Pre-built Images (Recommended)

```bash
# Clone the repository
git clone https://github.com/techsquidtv/hermes.git
cd hermes

# Copy environment template (all environment variables are configured in the root .env file)
cp .env.example .env

# Edit .env and set a secure HERMES_SECRET_KEY
nano .env

# Start all services using pre-built images (includes Caddy reverse proxy)
docker compose -f docker-compose.example.yml up -d
```

**That's it!** 🎉 Your Hermes instance will be available at:
- **Web App**: http://localhost:3000
- **API Docs**: http://localhost:3000/api/v1/docs (via proxy)

**For development with hot reload:**
```bash
docker compose -f docker-compose.dev.yml up
```
- **Dev Server**: http://localhost:5173 (Vite with hot reload)
- **API**: http://localhost:8000 (direct access)

### Building from Source

If you prefer to build the images from source or want to modify the code:

```bash
# Use the standard docker-compose.yml (builds from source)
docker compose up -d
```

### Deployment Options

Hermes offers two deployment approaches:

#### **Pre-built Images (Recommended)**
- **Faster startup** - No build time required
- **Stable releases** - Uses tested, published versions
- **Smaller downloads** - Only pulls necessary images
- **File**: `docker-compose.example.yml`
- **Public packages** - No authentication required

```bash
# Uses ghcr.io/techsquidtv/hermes-app:latest and ghcr.io/techsquidtv/hermes-api:latest
docker compose -f docker-compose.example.yml up -d
```

#### **Build from Source**
- **Full customization** - Modify code and rebuild
- **Latest changes** - Access to unreleased features
- **Development** - Perfect for contributors
- **File**: `docker-compose.yml`

```bash
# Builds images from local Dockerfiles
docker compose up -d
```

### Preparing Directories for Docker Volumes

Before starting Docker containers, create the required directories with proper permissions. The API container runs as a non-root user (UID 1000), so mounted volumes must be writable:

```bash
# Create directories (paths should match your docker-compose volumes)
mkdir -p ./data ./downloads ./temp

# Set ownership for container user (default UID 1000)
sudo chown -R 1000:1000 ./data ./downloads ./temp

# Or match your current host user (useful for development)
sudo chown -R $(id -u):$(id -g) ./data ./downloads ./temp

# Or use permissive permissions (less secure)
chmod -R 777 ./data ./downloads ./temp
```

**Required directories:**
- `data/` - SQLite database and persistent data
- `downloads/` - Downloaded video files
- `temp/` - Temporary files during download

> **Note:** Directory paths depend on your docker-compose configuration. Check the `volumes` section in your compose file to see where these are mounted from. For example, `docker-compose.example.yml` might use `./services/hermes/data` instead of `./data`.

### Customizing the Reverse Proxy

The default setup uses Caddy as a reverse proxy. You can customize it by editing the `Caddyfile`:

```bash
nano Caddyfile
# Add your domain for automatic HTTPS, custom routing, etc.
docker compose restart proxy
```

#### Domain Configuration Options

**Single Domain** (Recommended for most users):
- Frontend and API on same domain: `hermes.example.com`
- API accessible at: `hermes.example.com/api/`

**Separate Domains** (Advanced):
- Frontend at: `hermes.example.com`
- API at: `hermes-api.example.com`

See the [Caddyfile examples](Caddyfile) for both configurations.

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

### 🐛 Having Issues?

If you run into problems, please use our [issue templates](https://github.com/techsquidtv/hermes/issues/new/choose) instead of generic issues:
- **[🐛 Bug Report](https://github.com/techsquidtv/hermes/issues/new?template=bug_report.yml)** - For unexpected behavior
- **[🔧 API Issues](https://github.com/techsquidtv/hermes/issues/new?template=hermes-api-issue.yml)** - Backend problems
- **[🎨 Frontend Issues](https://github.com/techsquidtv/hermes/issues/new?template=hermes-app-issue.yml)** - UI/UX problems
- **[🐳 DevOps Issues](https://github.com/techsquidtv/hermes/issues/new?template=devops-issue.yml)** - Docker/deployment issues

These templates help us help you faster!

### Manual Installation (Development)

For development and contribution purposes:

```bash
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
- **[Contributing Guide](docs/CONTRIBUTING.md)** - How to contribute code, tests, and documentation
- **[API Documentation](packages/hermes-api/README.md)** - Complete API reference and examples
- **[Frontend Guide](packages/hermes-app/README.md)** - React app development guide
- **[Interactive API Docs](http://localhost:8000/docs)** - Live Swagger documentation
- **[docker-compose.example.yml](docker-compose.example.yml)** - Pre-built images deployment configuration
---

## Hosting Partner

This could be you! Bring Hermes to the world by hosting a public instance and getting featured here!
