# Multi-stage Dockerfile for Hermes API
FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv-runtime

# Build the same verified WAL-fixed library for both supported architectures.
# Upstream archive SHA3-256: b6ced585c750916b1052667239a12c25a7ff34e7f06e1e6e01ecb0427657d9c4
# https://sqlite.org/download.html (3.54.1); https://sqlite.org/wal.html#walreset
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS sqlite-runtime
RUN apt-get update && apt-get install -y --no-install-recommends gcc make libc6-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
ADD --checksum=sha256:926ef8d3eab93fbf6e06011901273eec076b25594a4e1cdadd50c987f4f6d64e \
    https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz sqlite.tar.gz
RUN tar -xzf sqlite.tar.gz --strip-components=1 \
    && ./configure --prefix=/opt/sqlite --disable-static --disable-readline CFLAGS='-O2' \
    && make -j2 libsqlite3.so \
    && make install-dll

FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS builder

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

FROM node:26-slim@sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc AS node-runtime

# Production stage - use Python slim base image
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

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

# Verify Python's loaded library, rather than trusting a package version or CLI.
COPY --from=sqlite-runtime /opt/sqlite/lib/ /usr/local/lib/
RUN echo '/usr/local/lib' > /etc/ld.so.conf.d/00-hermes-sqlite.conf \
    && ldconfig \
    && python -c "import sqlite3; assert sqlite3.sqlite_version == '3.54.1', sqlite3.sqlite_version; print(sqlite3.connect(':memory:').execute('SELECT sqlite_source_id()').fetchone()[0])"

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
