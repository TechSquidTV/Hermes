#!/bin/sh
set -e

echo "==================================="
echo "Hermes App - Runtime Configuration"
echo "==================================="

# Generate runtime config with environment variable substitution
# Priority: VITE_API_BASE_URL env var > default /api/v1
API_BASE_URL="${VITE_API_BASE_URL:-/api/v1}"

cat > /usr/share/nginx/html/config.js <<EOF
window.__RUNTIME_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL}"
};
EOF

echo "Runtime config generated:"
echo "  API_BASE_URL: ${API_BASE_URL}"
echo "==================================="

# Execute the main command (nginx)
exec "$@"
