#!/usr/bin/env bash
# Start floridify dev environment. Cleans up on exit/kill.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ── Load .env if present ──────────────────────────────────
[[ -f "$ROOT/.env" ]] && set -o allexport && source "$ROOT/.env" && set +o allexport

# ── Config ────────────────────────────────────────────────
PROJECT_NAME="floridify"
BACKEND_PORT_DEFAULT=9110
FRONTEND_PORT_DEFAULT=9111

# ── Find a free port starting from $1 ────────────────────
find_free_port() {
    local p=${1:-8000}
    for _ in $(seq 1 20); do
        lsof -iTCP:"$p" -sTCP:LISTEN -P -n >/dev/null 2>&1 || { echo "$p"; return 0; }
        ((p++))
    done
    echo "ERROR: no free port from $1" >&2; return 1
}

# ── Pick ports ────────────────────────────────────────────
BACKEND_PORT=$(find_free_port "${BACKEND_PORT:-$BACKEND_PORT_DEFAULT}")
FRONTEND_PORT=$(find_free_port "${FRONTEND_PORT:-$FRONTEND_PORT_DEFAULT}")

export BACKEND_PORT FRONTEND_PORT
export BUILD_TARGET="${BUILD_TARGET:-development}"
export BACKEND_CORS_ORIGINS="${BACKEND_CORS_ORIGINS:-[\"http://localhost:${FRONTEND_PORT}\",\"http://localhost:5173\"]}"

# MONGO_URI / MONGODB_URL come from .env — direct TLS to production
[[ -z "${MONGODB_URL:-}" ]] && { echo "ERROR: MONGODB_URL not set (check .env)"; exit 1; }

# ── Sync glass-ui if present ─────────────────────────────
GLASS_UI_SRC="$ROOT/../glass-ui"
GLASS_UI_DST="$ROOT/frontend/glass-ui"
if [ -d "$GLASS_UI_SRC" ]; then
    rsync -a --delete \
        --exclude node_modules --exclude dist --exclude .git \
        "$GLASS_UI_SRC/" "$GLASS_UI_DST/"
fi

# ── Commands ──────────────────────────────────────────────
case "${1:-}" in
    --down)   docker compose down; exit 0 ;;
    --logs)   docker compose logs -f; exit 0 ;;
    --build)  docker compose build && docker compose up -d ;;
    *)        docker compose up -d ;;
esac

cat <<EOF

──────────────────────────────────────
  Floridify Dev Environment
──────────────────────────────────────
  Backend  → http://localhost:$BACKEND_PORT
  Frontend → http://localhost:$FRONTEND_PORT
  MongoDB  → (remote via TLS, from .env)
──────────────────────────────────────

EOF
