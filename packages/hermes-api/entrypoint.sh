#!/bin/bash
set -e

echo "Running database migrations..."
# Use alembic directly from venv since deps are already installed
# This avoids uv run re-installing dev dependencies
alembic upgrade head

echo "Starting Hermes API..."
exec "$@"
