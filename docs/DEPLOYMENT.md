# Deployment Guide

This document covers operational aspects of deploying Hermes including volume management, monitoring, backups, and security. For reverse proxy configuration and domain setup, see the [Proxy & Deployment Guide](PROXY_DEPLOYMENT.md).

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
with its `dry_run` option before enabling scheduled deletion. See the
[configuration guide](CONFIGURATION.md) for the updated settings.

## Compose scheduler and release upgrade

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

## Docker Volume Mounts

The Docker setup uses volume mounts to persist data and provide access to downloaded files:

### API Service Volume Mounts

| Host Path | Container Path | Purpose | Contents |
|-----------|----------------|---------|----------|
| `./data/data/` | `/app/data/` | **Database Storage** | SQLite database file (`hermes.db`) containing user accounts, download history, queue state, and application settings |
| `./data/downloads/` | `/app/downloads/` | **Completed Downloads** | Successfully downloaded video files, organized by format and quality |
| `./data/temp/` | `/app/temp/` | **Temporary Files** | Intermediate files during download process, partial downloads, and temporary processing files |

### Database Persistence (`data/`)

The SQLite database is persisted to the host machine at `data/data/hermes.db`. This ensures:

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

---

## Production Deployment

### Environment Setup

1. **Set `HERMES_DEBUG=false`** in your `.env` file
2. **Use a secure `HERMES_SECRET_KEY`** (generate with the methods in CONFIGURATION.md)
3. **Ensure SQLite database is properly backed up**
4. **Set up proper Redis configuration**
5. **Configure CORS origins** for your domain(s)
6. **Set frontend API URL** if using separate domains

### Domain Configuration

For domain configuration, reverse proxy setup, and deployment scenarios, see the [Proxy & Deployment Guide](PROXY_DEPLOYMENT.md) which covers:

- Single domain deployment (default)
- Separate subdomains setup
- Integration with existing reverse proxies (Caddy, nginx, Traefik, Apache, etc.)
- Complete configuration examples
- Runtime API URL configuration

### Docker Deployment

The application includes optimized Dockerfiles for both services:

- **Frontend**: Multi-stage build producing static files served by nginx
- **API**: Python application with uv package management
- **Worker**: Celery worker for background tasks

> **Note**: The frontend container runs nginx to serve static files and generate runtime configuration.

#### Building Production Images

```bash
# Build API
docker build -f packages/hermes-api/Dockerfile -t hermes-api:latest packages/hermes-api

# Build Frontend
docker build -f packages/hermes-app/Dockerfile -t hermes-app:latest .
```

#### Running Production Containers

```bash
# API
docker run -d \
  --name hermes-api \
  -p 8000:8000 \
  -e HERMES_SECRET_KEY=your-secret \
  -e HERMES_DEBUG=false \
  -e HERMES_DATABASE_URL=sqlite+aiosqlite:///./data/hermes.db \
  -v /data/hermes/downloads:/app/downloads \
  -v /data/hermes/data:/app/data \
  hermes-api:latest

# Frontend
docker run -d \
  --name hermes-app \
  -p 3000:80 \
  -e VITE_API_BASE_URL=http://localhost:8000/api/v1 \
  hermes-app:latest
```

When using Docker Compose, leave `VITE_API_BASE_URL=/api/v1`; the frontend nginx container proxies `/api/*` to the internal API service. When running containers manually as separate host ports, use the full browser-reachable API URL as shown above.

---

## Monitoring & Health Checks

### Health Check Endpoints

- **API Health**: `http://your-domain.com/api/v1/health/`
  - Returns: `{"status":"healthy","timestamp":"...","version":"...","environment":"..."}`
- **Frontend Health**: Nginx serves on port 80 - check with any HTTP request

### Version Status

The application includes a built-in version status indicator in the sidebar that:

- **Shows current versions** of both frontend (hermes-app) and backend (hermes-api)
- **Checks for updates** by querying published-image Git tags automatically
- **Displays status badges**:
  - 🟢 **Up to date**: Green checkmark when running latest version
  - 🟠 **Update available**: Orange warning with clickable link to new release
  - 🔘 **Unknown**: Gray indicator when unable to check for updates

#### Version Information

- **Frontend Version**: Dynamically loaded from `package.json` at build time
- **API Version**: Fetched from the API's health endpoint (`/api/v1/health/`), sourced from `pyproject.toml`
- **Latest Versions**: Retrieved from Git tags in the monorepo (`techsquidtv/hermes`)
- **Published Image Tags**: Supports semantic versioning with tags like `hermes-app-v1.0.0`

#### Accessing Version Status

The version status appears in the bottom-left of the sidebar and provides:

1. **Current versions** display (e.g., "App: v1.0.0 | API: v1.0.0")
2. **Update notifications** when new releases are available
3. **Direct links** to GitHub releases for easy access to changelogs
4. **Pre-release messaging** when no releases have been published yet

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
   - Container logs for system issues

---

## Backup Strategy

### Database Backups

```bash
# SQLite backup
cp data/data/hermes.db data/data/hermes.db.backup

# Create timestamped backup
cp data/data/hermes.db \
   data/data/hermes.db.backup.$(date +%Y%m%d_%H%M%S)
```

### File Backups

```bash
# Backup downloads directory
tar -czf downloads_backup_$(date +%Y%m%d).tar.gz data/downloads/

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
cp data/data/hermes.db $BACKUP_DIR/db_backup_$DATE.sqlite

# Downloads backup (incremental)
rsync -a --delete data/downloads/ $BACKUP_DIR/downloads_backup_$DATE/

# Configuration backup
cp .env $BACKUP_DIR/
cp docker-compose.yml $BACKUP_DIR/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*" -type f -mtime +7 -delete
```

---

## Security Considerations

### Production Security Checklist

- [ ] Use HTTPS with proper SSL certificates
- [ ] Enable rate limiting (`HERMES_ENABLE_RATE_LIMITING=true`)
- [ ] Set strong secret key (32+ characters, random)
- [ ] Configure CORS properly for your domain(s)
- [ ] Use session revocation (always enabled) and store each replacement refresh token
- [ ] Set up proper firewall rules
- [ ] Monitor authentication attempts
- [ ] Keep all dependencies updated
- [ ] Use non-root containers (default in Dockerfiles)
- [ ] Implement proper backup strategy
- [ ] Restrict access to sensitive endpoints
- [ ] Use environment variables for secrets (never hardcode)

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

### Environment Variable Security

```bash
# Generate secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Set in .env with proper permissions
chmod 600 .env
chown your-user:your-user .env
```

---

## Troubleshooting

### Common Issues

#### Dev dependencies being installed in production

**Symptom**: Logs show "Downloading black, ruff, mypy" on container startup

**Cause**: Using `uv run <command>` installs all dependencies including dev dependencies

**Solution**: Run commands directly from the venv instead:
```yaml
# Bad - reinstalls dev dependencies
command: uv run uvicorn app.main:app

# Good - uses pre-installed dependencies only
command: uvicorn app.main:app
```

**Note**: The Dockerfile already installs dependencies with `--no-dev`, but `uv run` bypasses this

#### Container won't start

- Check if all required environment variables are set
- Verify volume mount paths exist and are writable
- Check Docker daemon status: `docker ps`
- Review container logs: `docker compose logs <service>`

#### Database connection errors

- Ensure database URL format is correct
- Verify database server is running and accessible
- Check network connectivity between containers
- Verify credentials and permissions

#### Download failures

- Check available disk space: `df -h`
- Verify yt-dlp can access the target URLs
- Check worker container logs: `docker compose logs celery_worker`
- Verify network connectivity from worker container

#### Authentication issues

- Verify `HERMES_SECRET_KEY` is set correctly and consistently across all services
- Check token expiration settings
- Review CORS configuration in `HERMES_ALLOWED_ORIGINS`
- Clear browser cache and cookies
- Check for expired or blacklisted tokens

#### Real-time updates not working

- Verify SSE endpoint is accessible: `/api/v1/events/*`
- Check reverse proxy configuration (see [Proxy & Deployment Guide](PROXY_DEPLOYMENT.md))
- Ensure proxy allows long-lived connections
- Check for buffering issues in proxy configuration

### Log Locations

Access container logs using Docker Compose:

```bash
# All services
docker compose logs

# Specific service
docker compose logs api
docker compose logs celery_worker
docker compose logs app
docker compose logs redis

# Follow logs in real-time
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api
```

### Debug Mode

Enable debug mode for more verbose logging:

```env
# .env
HERMES_DEBUG=true
HERMES_DATABASE_ECHO=true
```

**Warning**: Never enable debug mode in production as it may expose sensitive information.

### Getting Support

1. Check the [Proxy & Deployment Guide](PROXY_DEPLOYMENT.md) for proxy and domain issues
2. Review [Configuration Guide](CONFIGURATION.md) for environment variables
3. Review [persistent volume setup](#docker-volume-mounts) and container ownership
4. Search existing issues in the [GitHub repository](https://github.com/TechSquidTV/Hermes/issues)
5. Create a new issue with:
   - Your deployment configuration (redact secrets)
   - Container logs
   - Error messages
   - Steps to reproduce

---

## Performance Tuning

### API Performance

- **Adjust rate limiting** based on your needs:
  ```env
  HERMES_RATE_LIMIT_PER_MINUTE=120  # Increase for more traffic
  ```

- **Monitor database query performance**:
  ```env
  HERMES_DATABASE_ECHO=true  # Enable query logging (dev only)
  ```
  **Note:** Hermes uses SQLite for simplicity. For high-traffic production deployments, consider implementing database connection pooling or migrating to PostgreSQL (requires code changes).

- **Configure Redis maxmemory** policy:
  ```yaml
  redis:
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
  ```

### Worker Performance

Scale Celery workers based on download volume:

```yaml
# docker-compose.yml
celery_worker:
  # ... existing config ...
  deploy:
    replicas: 3  # Scale workers horizontally
```

Or run multiple named workers:

```bash
docker compose up -d --scale celery_worker=3
```

Adjust worker concurrency:

```yaml
celery_worker:
  command: celery -A app.worker worker --loglevel=info --concurrency=4 --queues=hermes.downloads,hermes.cleanup,hermes.default
```

### Storage Optimization

- **Implement regular cleanup** of temporary files:
  ```bash
  # Cron job to clean temp directory
  0 2 * * * find /path/to/temp -type f -mtime +7 -delete
  ```

- **Use appropriate file formats** for your use case:
  - MP4 for broad compatibility
  - WebM for smaller file sizes
  - MKV for highest quality

- **Monitor disk usage**:
  ```bash
  # Check disk space
  df -h

  # Check directory sizes
  du -sh data/downloads/
  du -sh data/temp/
  ```

- **Consider external storage** for large download volumes:
  - NFS mounts
  - S3-compatible object storage
  - Network-attached storage (NAS)

### Network Performance

- **Enable gzip compression** in your reverse proxy
- **Use HTTP/2** for better performance
- **Enable caching** for static assets
- **Use CDN** for frontend assets if serving globally

See the [configuration guide](CONFIGURATION.md) for worker, storage, and scheduler settings.

---

## Related Documentation

- [Proxy & Deployment Guide](PROXY_DEPLOYMENT.md) - Reverse proxy and domain configuration
- [Configuration Guide](CONFIGURATION.md) - Environment variables reference
- [Main README](../README.md) - Getting started and overview
