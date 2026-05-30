# Hermes API

A production-ready video downloading API built with FastAPI, yt-dlp, and modern Python async patterns.

## ✨ Features

- 🎥 **Video Downloads**: Download videos from YouTube and 1000+ other sites using yt-dlp, with bundled EJS support and Node-powered JavaScript challenge solving in Docker
- 📦 **Batch Processing**: Queue multiple downloads for background processing
- ⚡ **Async Architecture**: Built on FastAPI with async/await throughout
- 🔄 **Background Tasks**: Celery-powered background job processing
- 📊 **Queue Management**: Monitor and manage download queues
- 🗄️ **Database Tracking**: SQLAlchemy for download history and metadata
- 🔒 **Authentication**: API key and JWT token support
- 📝 **Auto Documentation**: Interactive Swagger UI and ReDoc
- 🧪 **Well Tested**: Comprehensive test suite with pytest
- 🐳 **Docker Ready**: Full Docker and Docker Compose support
- 📊 **Structured Logging**: Production-ready logging with structlog

## 🚀 Quick Start

### Using uv (Recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Optional: install Node.js 20+ for yt-dlp EJS challenge solving.
# The Docker image already includes Node 24.
node --version

# Start Redis
redis-server &

# Run the API
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start Celery worker
uv run celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1 --hostname=hermes-worker@%h --queues=hermes.downloads,hermes.cleanup,hermes.default
```

### Using Docker

```bash
docker compose up -d
```

The API will be available at http://localhost:8000

## 📖 Documentation

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **OpenAPI JSON**: http://localhost:8000/openapi.json (auto-generated)
- **Quick Start Guide**: [QUICKSTART.md](./QUICKSTART.md)
- **Implementation Status**: [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)
- **Implementation Plan**: [VideoDownloader_Implementation_Plan.md](../../docs/VideoDownloader_Implementation_Plan.md)

## 🎯 API Endpoints

### Health & Info
- `GET /health` - Basic health check
- `GET /api/v1/health/` - Detailed health check
- `GET /api/v1/info/` - Extract video information

### Downloads
- `POST /api/v1/download/` - Start a download
- `POST /api/v1/download/batch` - Batch downloads
- `GET /api/v1/download/{id}` - Check status
- `POST /api/v1/download/{id}/cancel` - Cancel download

### Management
- `GET /api/v1/queue/` - View download queue
- `GET /api/v1/files/` - List files
- `DELETE /api/v1/files/` - Delete files

## 📝 Usage Example

```python
import httpx

# Get video information
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/api/v1/info/",
        params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    info = response.json()
    print(f"Title: {info['title']}")
    print(f"Duration: {info['duration']}s")

# Start a download
    response = await client.post(
        "http://localhost:8000/api/v1/download/",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "format": "best",
            "download_subtitles": True
        },
        headers={"Authorization": "Bearer your-api-key"}
    )
    download = response.json()
    print(f"Download ID: {download['download_id']}")
    print(f"Status: {download['status']}")
```

## 🛠️ Development

### Project Structure

```
hermes-api/
├── app/
│   ├── api/v1/           # API endpoints
│   ├── core/             # Configuration, logging, security
│   ├── db/               # Database models and repositories
│   ├── models/pydantic/  # Request/response models
│   ├── services/         # Business logic
│   ├── tasks/            # Celery background tasks
│   └── main.py           # FastAPI application
├── data/                 # SQLite database (mounted from host)
├── downloads/            # Downloaded files (mounted from host)
├── temp/                 # Temporary files (mounted from host)
├── tests/                # Test suite
├── docker/               # Docker configuration
└── pyproject.toml        # Project dependencies (uv)
```

**Note:** The `data/`, `downloads/`, and `temp/` directories are mounted from the host machine for persistence and easy access to files.

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=app --cov-report=html

# Specific test file
uv run pytest tests/test_api/test_health.py -v
```

### Code Quality

```bash
# Format code
uv run black app/ tests/
uv run isort app/ tests/

# Type checking
uv run mypy app/

# Linting
uv run ruff check app/ tests/
```

## 🏗️ Architecture

- **FastAPI**: Async web framework with automatic OpenAPI docs
- **yt-dlp**: Video extraction and downloading
- **SQLAlchemy**: Async ORM for database operations
- **Celery**: Distributed task queue for background processing
- **Redis**: Message broker and caching
- **Pydantic**: Data validation and settings management
- **structlog**: Structured logging
- **pytest**: Testing framework

## 🔧 Configuration

Configuration via environment variables (prefix: `HERMES_`):

```bash
HERMES_DEBUG=false
HERMES_DATABASE_URL=sqlite+aiosqlite:///./hermes.db
HERMES_REDIS_URL=redis://localhost:6379/0
HERMES_SECRET_KEY=your-secret-key-here
HERMES_DOWNLOAD_DIR=./downloads
HERMES_TEMP_DIR=./temp
HERMES_RATE_LIMIT_PER_MINUTE=60
```

See [QUICKSTART.md](./QUICKSTART.md) for all configuration options.

## 🐳 Docker Deployment

The project includes Docker and Docker Compose configurations.

### Preparing Volume Directories

Before running the Docker container, prepare the required directories with proper permissions. The container runs as a non-root user (default UID 1000), so mounted volumes need to be writable:

```bash
# Create required directories
mkdir -p ./data ./downloads ./temp

# Set ownership for container user (default UID 1000)
sudo chown -R 1000:1000 ./data ./downloads ./temp

# Or match your current host user (useful for development)
sudo chown -R $(id -u):$(id -g) ./data ./downloads ./temp

# Or use permissive permissions (less secure)
chmod -R 777 ./data ./downloads ./temp
```

**Note:** To use your host user's UID/GID with the second option, you can customize the Docker image at build time using `--build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)` if needed.

**Volume Mounts:**
- `/app/data` - SQLite database and persistent data
- `/app/downloads` - Downloaded video files
- `/app/temp` - Temporary files during download

### Running with Docker

```bash
# Development
docker compose up -d

# Production build
docker build -f docker/Dockerfile -t hermes-api:latest .

# Run production container
docker run -d \
  -p 8000:8000 \
  -e HERMES_SECRET_KEY=your-secret-key \
  -e HERMES_DATABASE_URL=sqlite+aiosqlite:///./data/hermes.db \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/temp:/app/temp \
  -v $(pwd)/data:/app/data \
  hermes-api:latest
```

### Docker Compose Example

```yaml
services:
  hermes-api:
    image: ghcr.io/techsquidtv/hermes-api:latest
    environment:
      - HERMES_SECRET_KEY=${HERMES_SECRET_KEY}
      - HERMES_DATABASE_URL=sqlite+aiosqlite:///./data/hermes.db
      - HERMES_REDIS_URL=redis://redis:6379
      - HERMES_ALLOWED_ORIGINS=https://your-domain.com
    volumes:
      - ./services/hermes/downloads:/app/downloads
      - ./services/hermes/temp:/app/temp
      - ./services/hermes/data:/app/data
    depends_on:
      - redis
```

## 📊 Current Status

✅ **Phase 1-6 Complete** - Foundation fully implemented

- Core API functionality
- Database layer
- Background task processing
- Security & authentication
- Testing infrastructure
- Documentation

See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for detailed status.

## 🗺️ Roadmap

### Next Up
- [ ] Expand test coverage
- [ ] Webhook system implementation
- [ ] Storage management features
- [ ] Analytics & metrics
- [ ] Cloud storage integration

### Future
- [ ] WebSocket support for real-time updates
- [ ] Advanced playlist handling
- [ ] Scheduled downloads
- [ ] User management system
- [ ] Rate limiting per user
- [ ] Multi-tenancy support

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The amazing video downloader
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Celery](https://docs.celeryq.dev/) - Distributed task queue

---

Built with ❤️ using FastAPI and yt-dlp
