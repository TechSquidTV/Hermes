# Multi-stage Dockerfile for Hermes API
FROM python:3.12-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set work directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies (fixed: added missing --no-dev flag)
RUN uv sync --frozen --no-install-project --no-dev

# Production stage - use distroless for smaller size
FROM python:3.12-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy uv and virtual environment from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv

# Set work directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./

# Copy application code
COPY app/ ./app/

# Create non-root user and set permissions
RUN useradd --create-home --shell /bin/bash --uid 1000 hermes && \
    chown -R hermes:hermes /app && \
    chmod -R 755 /app

# Switch to non-root user
USER hermes

# Set environment variables for security and performance
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check with better error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with optimized settings
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "asyncio"]
