#!/bin/sh
set -e

# Create runtime environment configuration
# This allows environment variables to be injected at container startup
# rather than at build time, making the image more portable

echo "Injecting runtime environment variables..."

# BASE_PATH should match the VITE_BASE_PATH used at build time.
# It determines the URL prefix for the env.js script tag.
BASE_PATH="${BASE_PATH:-/}"

# Create env.js file with runtime environment variables
cat > /usr/share/nginx/html/env.js <<EOF
window.__env__ = {
  VITE_API_URL: "${VITE_API_URL:-http://localhost:8000}",
  VITE_APP_TITLE: "${VITE_APP_TITLE:-Floridify}",
  VITE_ENVIRONMENT: "${VITE_ENVIRONMENT:-production}"
};
EOF

# Inject the env.js script into index.html if not already present
if ! grep -q "env.js" /usr/share/nginx/html/index.html; then
    sed -i "s|</head>|<script src=\"${BASE_PATH}env.js\"></script></head>|" /usr/share/nginx/html/index.html
fi

echo "Environment variables injected successfully"

# Continue with the default entrypoint
exec "$@"
