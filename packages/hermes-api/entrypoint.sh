#!/bin/bash
set -e

if [ "${1:-}" = "celery" ]; then
    echo "Checking worker database schema..."
    python -m app.manage check-schema
fi

# API startup owns migrations; workers never change the schema during rollout.
echo "Starting Hermes backend..."
exec "$@"
