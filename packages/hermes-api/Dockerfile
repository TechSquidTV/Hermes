# Multi-stage Dockerfile for Hermes API
FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv-runtime

FROM python:3.15-slim@sha256:e97b88e416c3c01eb427b21fd8cd3ebf006e6ee38afcfcc3cae1c54ee2ab0a75 AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=uv-runtime /uv /uvx /usr/local/bin/

# Set work directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Validate the lockfile and install only production dependencies
RUN uv sync --locked --no-install-project --no-dev

FROM node:26-slim@sha256:5adad64f9a1fca2d51972caa65983634c8a774eb300d72b20f7f2a0f60368072 AS node-runtime

# Production stage - use Python slim base image
FROM python:3.15-slim@sha256:e97b88e416c3c01eb427b21fd8cd3ebf006e6ee38afcfcc3cae1c54ee2ab0a75

# Build args for configurable UID/GID (defaults to 1000)
# Override at build time: docker build --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)
ARG USER_UID=1000
ARG USER_GID=1000
ARG HERMES_BUILD_VERSION

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy uv and virtual environment from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
# Fail the build if Node's loader or shared libraries are incompatible with Python's base.
RUN ldd /usr/local/bin/node && node --version \
    && node -e "require('node:crypto').randomBytes(16)"

# Set work directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./

# Copy alembic migration files
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Copy entrypoint script
COPY entrypoint.sh ./

# Copy application code
COPY app/ ./app/

# Create non-root user with configurable UID/GID
RUN groupadd --gid ${USER_GID} hermes && \
    useradd --create-home --shell /bin/bash --uid ${USER_UID} --gid ${USER_GID} hermes && \
    chown -R hermes:hermes /app && \
    chmod -R 755 /app && \
    chmod +x /app/entrypoint.sh

# Switch to non-root user
USER hermes

# Set environment variables for security and performance
ENV PATH="/app/.venv/bin:$PATH" \
    HERMES_BUILD_VERSION="${HERMES_BUILD_VERSION}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check with better error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ready || exit 1

# Workers verify the schema; API startup applies locked migrations.
ENTRYPOINT ["/app/entrypoint.sh"]

# Run the application with optimized settings
# Use uvicorn directly from venv to avoid uv run re-installing dev dependencies
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "asyncio"]
