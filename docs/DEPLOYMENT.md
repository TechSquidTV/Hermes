# Deployment Guide

This document covers operational aspects of deploying Hermes including volume management, monitoring, backups, and security. For reverse proxy configuration and domain setup, see the [Proxy & Deployment Guide](PROXY_DEPLOYMENT.md).

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
  -e HERMES_DATABASE_URL=sqlite+aiosqlite:///./data/hermes.db \
  -v /data/hermes/downloads:/app/downloads \
  -v /data/hermes/data:/app/data \
  hermes-api:latest

# Frontend
docker run -d \
  --name hermes-app \
  -p 3000:80 \
  -e VITE_API_BASE_URL=/api/v1 \
  hermes-app:latest
```

---

## Monitoring & Health Checks

### Health Check Endpoints

- **API Health**: `http://your-domain.com/api/v1/health/`
  - Returns: `{"status":"healthy","timestamp":"...","version":"...","environment":"..."}`
- **Frontend Health**: Nginx serves on port 80 - check with any HTTP request

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
cp packages/hermes-api/data/hermes.db packages/hermes-api/data/hermes.db.backup

# Create timestamped backup
cp packages/hermes-api/data/hermes.db \
   packages/hermes-api/data/hermes.db.backup.$(date +%Y%m%d_%H%M%S)
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

---

## Security Considerations

### Production Security Checklist

- [ ] Use HTTPS with proper SSL certificates
- [ ] Enable rate limiting (`HERMES_ENABLE_RATE_LIMITING=true`)
- [ ] Set strong secret key (32+ characters, random)
- [ ] Configure CORS properly for your domain(s)
- [ ] Enable token blacklisting (`HERMES_ENABLE_TOKEN_BLACKLIST=true`)
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
3. Check the [Docker setup guide](DOCKER_OPTIMIZATION_README.md) for optimization tips
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
  command: celery -A app.worker worker --loglevel=info --concurrency=4
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
  du -sh packages/hermes-api/downloads/
  du -sh packages/hermes-api/temp/
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

See the [Docker optimization guide](DOCKER_OPTIMIZATION_README.md) for detailed performance recommendations.

---

## Related Documentation

- [Proxy & Deployment Guide](PROXY_DEPLOYMENT.md) - Reverse proxy and domain configuration
- [Configuration Guide](CONFIGURATION.md) - Environment variables reference
- [Docker Optimization](DOCKER_OPTIMIZATION_README.md) - Docker performance tuning
- [Main README](../README.md) - Getting started and overview
