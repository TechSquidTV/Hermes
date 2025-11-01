# Deployment Guide

This document provides detailed information about deploying Hermes in various environments.

## Docker Volume Mounts

The Docker setup uses volume mounts to persist data and provide access to downloaded files:

### API Service Volume Mounts

| Host Path | Container Path | Purpose | Contents |
|-----------|----------------|---------|----------|
| `./packages/hermes-api/data/` | `/app/data/` | **Database Storage** | SQLite database file (`hermes.db`) containing user accounts, download history, queue state, and application settings |
| `./packages/hermes-api/downloads/` | `/app/downloads/` | **Completed Downloads** | Successfully downloaded video files, organized by format and quality |
| `./packages/hermes-api/temp/` | `/app/temp/` | **Temporary Files** | Intermediate files during download process, partial downloads, and temporary processing files |

### Database Persistence (`data/`)

The SQLite database is persisted to the host machine at `packages/hermes-api/data/hermes.db`. This ensures:

- **User accounts** and authentication data persist across container restarts
- **Download history** and queue state are preserved
- **Application settings** remain available
- **Database file** is easily accessible for backup, inspection, or migration

The database file is automatically created if it doesn't exist when the application starts.

### Download Storage (`downloads/`)

Downloaded files are stored in the host `downloads/` directory and mounted into the container. This allows:

- **Persistent storage** of completed downloads across container restarts
- **Easy access** to downloaded files from the host machine
- **Backup and archival** of downloaded content
- **Integration** with external media servers or storage systems

### Temporary Files (`temp/`)

Temporary files are stored separately to avoid cluttering the download directory:

- **Partial downloads** that may be resumed
- **Extracted metadata** and thumbnails during processing
- **Conversion artifacts** during format transcoding
- **Cleanup target** - these files can be safely deleted to free space

## Production Deployment

### Environment Setup

1. **Set `HERMES_DEBUG=false`** in your `.env` file
2. **Use a secure `HERMES_SECRET_KEY`** (generate with the methods in CONFIGURATION.md)
3. **Configure production database URL** (PostgreSQL recommended for production)
4. **Set up proper Redis configuration**
5. **Configure CORS origins** for your domain(s)
6. **Set frontend API URL** if using separate domains

### Domain Configuration Options

#### Option 1: Single Domain (Recommended for most users)

**Setup:**
- Frontend and API on same domain: `hermes.example.com`
- API accessible at: `hermes.example.com/api/`

**Environment Variables:**
```bash
HERMES_ALLOWED_ORIGINS=https://hermes.example.com
VITE_API_BASE_URL=/api/v1
```

**Caddyfile:**
```caddyfile
hermes.example.com {
    handle /api/* {
        reverse_proxy api:8000
    }

    handle {
        root * /app
        try_files {path} /index.html
        file_server
    }
}
```

#### Option 2: Separate Domains (Advanced)

**Setup:**
- Frontend at: `hermes.example.com`
- API at: `hermes-api.example.com`

**Environment Variables:**
```bash
HERMES_ALLOWED_ORIGINS=https://hermes.example.com,https://hermes-api.example.com
VITE_API_BASE_URL=https://hermes-api.example.com/api/v1
```

**Caddyfile:**
```caddyfile
# API Domain
hermes-api.example.com {
    handle /api/v1/* {
        reverse_proxy api:8000
    }

    handle {
        respond "Not Found" 404
    }
}

# Frontend Domain
hermes.example.com {
    handle /api/* {
        redir https://hermes-api.example.com{uri} permanent
    }

    handle {
        root * /app
        try_files {path} /index.html
        file_server
    }
}
```

### Docker Deployment

The application includes optimized Dockerfiles for both services:

- **Frontend**: Multi-stage build producing static files in a lightweight busybox container
- **API**: Python application with uv package management
- **Worker**: Celery worker for background tasks

> **Note**: The frontend container doesn't run a web server - it just holds static files that are served by the reverse proxy (Caddy) via a shared Docker volume.

#### Production Docker Compose

```yaml
# Production configuration is in the main docker-compose.yml
# Key features:
# - Caddy reverse proxy with automatic HTTPS
# - Static file serving via shared volumes
# - Internal network for service communication
# - Health checks for all services

services:
  proxy:
    image: caddy:2-alpine
    container_name: hermes-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - app_dist:/app:ro

  app:
    build: .
    volumes:
      - app_dist:/app

  api:
    build: ./packages/hermes-api
    volumes:
      - ./data:/app/data
      - ./downloads:/app/downloads
    # No ports exposed - accessed via proxy

volumes:
  app_dist:
  caddy_data:
```

### Manual Deployment

#### Building Production Images

```bash
# Build API
cd packages/hermes-api
docker build -f Dockerfile -t hermes-api:latest .

# Build Frontend
cd packages/hermes-app
docker build -f Dockerfile -t hermes-app:latest .
```

#### Running Production Containers

```bash
# API
docker run -d \
  --name hermes-api \
  -p 8000:8000 \
  -e HERMES_SECRET_KEY=your-secret \
  -e HERMES_DEBUG=false \
  -e HERMES_DATABASE_URL=postgresql+asyncpg://user:pass@db/hermes \
  -v /data/hermes/downloads:/app/downloads \
  -v /data/hermes/data:/app/data \
  hermes-api:latest

# Frontend
docker run -d \
  --name hermes-app \
  -p 3000:80 \
  hermes-app:latest
```

## Reverse Proxy Setup

### Using Caddy (Default)

The default `docker-compose.yml` includes Caddy as a reverse proxy. To customize:

1. Edit the `Caddyfile` in the project root
2. For production with a domain:
```caddy
hermes.yourdomain.com {
    tls admin@yourdomain.com
    
    handle /health {
        respond "healthy" 200
    }
    
    handle /api/* {
        reverse_proxy api:8000
    }
    
    handle {
        root * /app
        try_files {path} /index.html
        file_server
    }
}
```
3. Restart the proxy: `docker compose restart proxy`

### Using Your Own Reverse Proxy

If you have an existing reverse proxy (Traefik, nginx Proxy Manager, etc.):

1. Remove the `proxy` service from `docker-compose.yml`
2. Don't expose port 3000 on the `app` service
3. Connect your reverse proxy to the `hermes-network`
4. Point your proxy to:
   - Static files: Mount the `app_dist` volume and serve from there
   - API: `http://api:8000/api/`

See the [Reverse Proxy Guide](REVERSE_PROXY_GUIDE.md) for detailed examples.

### Legacy nginx Configuration

For reference, if you need to use nginx as an external reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend - serve from shared volume
    location / {
        root /path/to/app_dist/volume;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Note: Hermes uses Server-Sent Events (SSE), not WebSockets
        # No special WebSocket configuration needed
    }
}
```

## Monitoring & Health Checks

### Health Check Endpoints

- **API Health**: `http://your-domain.com/api/v1/health/`
- **Frontend Health**: `http://your-domain.com/health`

### Version Status

The application includes a built-in version status indicator in the sidebar that:

- **Shows current versions** of both frontend (hermes-app) and backend (hermes-api)
- **Checks for updates** by querying GitHub releases automatically
- **Displays status badges**:
  - 🟢 **Up to date**: Green checkmark when running latest version
  - 🟠 **Update available**: Orange warning with clickable link to new release
  - 🔘 **Unknown**: Gray indicator when unable to check for updates

#### Version Information

- **Frontend Version**: Dynamically loaded from `package.json` at build time
- **API Version**: Fetched from the API's health endpoint (`/api/v1/health/`), sourced from `pyproject.toml`
- **Latest Versions**: Retrieved from GitHub releases in the monorepo (`techsquidtv/hermes`)
- **Release Tags**: Supports semantic versioning with tags like `hermes-app-v1.0.0`

#### Accessing Version Status

The version status appears in the bottom-left of the sidebar and provides:

1. **Current versions** display (e.g., "App: v1.0.0 | API: v1.0.0")
2. **Update notifications** when new releases are available
3. **Direct links** to GitHub releases for easy access to changelogs
4. **Pre-release messaging** when no releases have been published yet

#### Integration with Release Process

The version status feature automatically integrates with the release workflows:

- Updates are detected when new tags are pushed (`hermes-app-v*`, `hermes-api-v*`)
- Version comparison uses semantic versioning (MAJOR.MINOR.PATCH)
- Links point to the correct release pages in the monorepo

#### Deployment Considerations

- **Docker Images**: Version status works with any deployment method (Docker, manual, etc.)
- **Offline Mode**: Shows "Unknown" status when unable to reach GitHub API
- **Network Security**: May be blocked by corporate firewalls or restrictive networks
- **Performance**: Caches GitHub API responses and only checks periodically

### Monitoring Recommendations

1. **Application Metrics**
   - Monitor download queue length
   - Track API response times
   - Monitor error rates

2. **System Resources**
   - Disk space (downloads and temp directories)
   - Memory usage (Redis, API, workers)
   - CPU usage during downloads

3. **Logs**
   - API logs for errors and authentication issues
   - Worker logs for download failures
   - Nginx access logs for security monitoring

## Backup Strategy

### Database Backups

```bash
# SQLite backup (development)
cp packages/hermes-api/data/hermes.db packages/hermes-api/data/hermes.db.backup

# PostgreSQL backup (production)
pg_dump hermes > hermes_backup.sql
```

### File Backups

```bash
# Backup downloads directory
tar -czf downloads_backup_$(date +%Y%m%d).tar.gz packages/hermes-api/downloads/

# Backup configuration
cp .env .env.backup
cp docker-compose.yml docker-compose.yml.backup
```

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
cp packages/hermes-api/data/hermes.db $BACKUP_DIR/db_backup_$DATE.sqlite

# Downloads backup (incremental)
rsync -a --delete packages/hermes-api/downloads/ $BACKUP_DIR/downloads_backup_$DATE/

# Configuration backup
cp .env $BACKUP_DIR/
cp docker-compose.yml $BACKUP_DIR/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*" -type f -mtime +7 -delete
```

## Security Considerations

### Production Security Checklist

- [ ] Use HTTPS with proper SSL certificates
- [ ] Enable rate limiting (`HERMES_ENABLE_RATE_LIMITING=true`)
- [ ] Set strong secret key
- [ ] Configure CORS properly for your domain
- [ ] Enable token blacklisting
- [ ] Set up proper firewall rules
- [ ] Monitor authentication attempts
- [ ] Keep all dependencies updated
- [ ] Use non-root containers
- [ ] Implement proper backup strategy

### Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow SSH (if needed)
sudo ufw allow 22

# Deny all other incoming traffic
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

## Troubleshooting

### Common Issues

**Dev dependencies being installed in production:**
- **Symptom**: Logs show "Downloading black, ruff, mypy" on container startup
- **Cause**: Using `uv run <command>` installs all dependencies including dev dependencies
- **Solution**: Run commands directly from the venv instead:
  ```yaml
  # Bad - reinstalls dev dependencies
  command: uv run uvicorn app.main:app

  # Good - uses pre-installed dependencies only
  command: uvicorn app.main:app
  ```
- **Note**: The Dockerfile already installs dependencies with `--no-dev`, but `uv run` bypasses this

**Container won't start:**
- Check if all required environment variables are set
- Verify volume mount paths exist and are writable
- Check Docker daemon status

**Database connection errors:**
- Ensure database URL format is correct
- Verify database server is running and accessible
- Check network connectivity between containers

**Download failures:**
- Check available disk space
- Verify yt-dlp can access the target URLs
- Check worker container logs

**Authentication issues:**
- Verify `HERMES_SECRET_KEY` is set correctly
- Check token expiration settings
- Review CORS configuration

### Log Locations

- **API logs**: Container logs (`docker compose logs api`)
- **Worker logs**: Container logs (`docker compose logs celery_worker`)
- **Frontend logs**: Container logs (`docker compose logs hermes-app`)
- **Redis logs**: Container logs (`docker compose logs redis`)

### Getting Support

1. Check the [Docker setup guide](DOCKER_OPTIMIZATION_README.md)
2. Review [configuration documentation](CONFIGURATION.md)
3. Check API documentation in the individual package READMEs
4. Search existing issues in the repository

## Performance Tuning

### API Performance

- Adjust `HERMES_RATE_LIMIT_PER_MINUTE` based on your needs
- Monitor database query performance
- Consider using PostgreSQL for better performance under load

### Worker Performance

- Scale Celery workers based on download volume:
  ```yaml
  celery_worker:
    # ... existing config ...
    deploy:
      replicas: 3  # Scale workers horizontally
  ```

### Storage Optimization

- Implement regular cleanup of temporary files
- Use appropriate file formats for your use case
- Consider external storage solutions for large download volumes

See the [Docker optimization guide](DOCKER_OPTIMIZATION_README.md) for detailed performance recommendations.
