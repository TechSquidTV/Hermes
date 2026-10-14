#!/bin/sh
set -e

echo "==================================="
echo "Hermes App - Runtime Configuration"
echo "==================================="

# Generate runtime config with environment variable substitution
# Priority: VITE_API_BASE_URL env var > default /api/v1
API_BASE_URL="${VITE_API_BASE_URL:-/api/v1}"

{
    printf 'window.__RUNTIME_CONFIG__ = '
    jq -n --arg apiBaseUrl "$API_BASE_URL" '{API_BASE_URL: $apiBaseUrl}'
    printf ';\n'
} > /usr/share/nginx/html/config.js

echo "Runtime config generated:"
echo "  API_BASE_URL: ${API_BASE_URL}"
echo "==================================="

# Execute the main command (nginx)
exec "$@"
