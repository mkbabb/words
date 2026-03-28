#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# Floridify development environment (Docker only).
#
# What it does:
#   1. Loads .env defaults
#   2. Finds available ports for backend, frontend, and SSH tunnel
#   3. Opens an SSH tunnel to the remote MongoDB instance
#   4. Starts all Docker services with hot-reload
#
# Port defaults (overridable via .env):
#   Backend:    8003
#   Frontend:   3004
#   SSH tunnel: 37117
#
# If a default port is occupied, the next free port is used automatically.
# The SSH tunnel connects to the remote MongoDB via the deploy host.
#
# Usage:
#   ./scripts/dev.sh              # Start everything
#   ./scripts/dev.sh --build      # Force rebuild + start
#   ./scripts/dev.sh --down       # Stop all containers
#   ./scripts/dev.sh --logs       # Tail container logs
#   ./scripts/dev.sh --restart    # Down + up (no rebuild)
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ─── Load .env ───────────────────────────────────────────────────────

if [ -f "$ROOT_DIR/.env" ]; then
    # shellcheck disable=SC1090
    eval "$(python3 - "$ROOT_DIR/.env" <<'PY'
from pathlib import Path; import shlex, sys
for line in Path(sys.argv[1]).read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    print(f"export {key}={shlex.quote(value)}")
PY
    )"
fi

# ─── Port utilities ──────────────────────────────────────────────────

find_free_port() {
    # Usage: find_free_port <preferred> [max_offset]
    # Returns the first available port starting from <preferred>,
    # scanning up to <max_offset> ports ahead (default 100).
    local port="$1"
    local max_offset="${2:-100}"
    local end=$((port + max_offset))

    while [ "$port" -le "$end" ]; do
        if ! lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
            echo "$port"
            return 0
        fi
        port=$((port + 1))
    done

    echo "No free port found in range $1-$end" >&2
    return 1
}

# ─── Resolve ports ───────────────────────────────────────────────────
# Each port falls back to .env default, then finds a free one.

BACKEND_PORT="$(find_free_port "${BACKEND_PORT:-8003}")"
FRONTEND_PORT="$(find_free_port "${FRONTEND_PORT:-3004}")"

export BACKEND_PORT FRONTEND_PORT
export BUILD_TARGET="${BUILD_TARGET:-development}"
export BACKEND_CORS_ORIGINS="${BACKEND_CORS_ORIGINS:-[\"http://localhost:${FRONTEND_PORT}\",\"http://localhost:5173\",\"http://frontend:${FRONTEND_PORT}\"]}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:${FRONTEND_PORT},http://frontend:${FRONTEND_PORT}}"

# ─── MongoDB URL from config.toml ───────────────────────────────────
# Single source of truth: auth/config.toml [database].tunnel_url
# The tunnel URL's port is rewritten to the dynamically-selected tunnel port,
# and the host is rewritten to host.docker.internal so Docker containers can
# reach the SSH tunnel running on the host.

resolve_mongodb_url() {
    local port="$1" host="$2"
    ROOT_DIR="$ROOT_DIR" python3 - "$port" "$host" <<'PY'
import os, sys, tomllib
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

def replace_host_port(uri: str, host: str, port: str) -> str:
    parts = urlsplit(uri)
    if not parts.scheme or not parts.netloc:
        raise SystemExit(f"Invalid MongoDB URL: {uri!r}")
    creds, _hosts = parts.netloc.rsplit("@", 1) if "@" in parts.netloc else ("", "")
    netloc = f"{creds}@{host}:{port}" if creds else f"{host}:{port}"
    return urlunsplit(SplitResult(parts.scheme, netloc, parts.path, parts.query, parts.fragment))

config_path = Path(os.environ["ROOT_DIR"]) / "auth" / "config.toml"
if not config_path.exists():
    raise SystemExit(f"Config not found: {config_path}")
db = tomllib.loads(config_path.read_text()).get("database", {})
url = db.get("tunnel_url") or db.get("runtime_url")
if not url:
    raise SystemExit("No [database].tunnel_url or runtime_url in config.toml")
print(replace_host_port(url, sys.argv[2], sys.argv[1]))
PY
}

# ─── SSH tunnel ──────────────────────────────────────────────────────

start_tunnel() {
    # Delegates to start-ssh-tunnel.sh which handles:
    #   - Reusing an existing tunnel if one is already running
    #   - Auto-selecting a free port starting from MONGO_TUNNEL_PORT
    #   - SSH keepalive and connection health
    local tunnel_port
    tunnel_port="$("$ROOT_DIR/scripts/start-ssh-tunnel.sh" --print-port)"
    echo "$tunnel_port"
}

# ─── Prepare runtime environment ─────────────────────────────────────

prepare_env() {
    local tunnel_port
    tunnel_port="$(start_tunnel)"

    export MONGO_TUNNEL_PORT="$tunnel_port"
    export MONGODB_URL="$(resolve_mongodb_url "$tunnel_port" "host.docker.internal")"
    export VITE_API_URL="${VITE_API_URL:-http://backend:8000}"
    export API_URL="${API_URL:-http://backend:8000}"
}

# ─── Sync glass-ui into frontend build context ───────────────────
# Temporary: until @mkbabb/glass-ui is published to npm, copy it
# into frontend/ so Docker can access it during build.
GLASS_UI_SRC="$ROOT_DIR/../glass-ui"
GLASS_UI_DST="$ROOT_DIR/frontend/glass-ui"
if [ -d "$GLASS_UI_SRC" ]; then
    rsync -a --delete \
        --exclude node_modules --exclude dist --exclude .git \
        "$GLASS_UI_SRC/" "$GLASS_UI_DST/"
fi

# ─── Commands ────────────────────────────────────────────────────────

case "${1:-}" in
    --down)
        docker compose down
        exit 0
        ;;
    --logs)
        docker compose logs -f
        exit 0
        ;;
    --restart)
        docker compose down
        prepare_env
        docker compose up -d
        ;;
    --build)
        prepare_env
        docker compose build
        docker compose up -d
        ;;
    *)
        prepare_env
        docker compose up -d
        ;;
esac

# ─── Summary ─────────────────────────────────────────────────────────

echo ""
echo "  Backend:          http://localhost:${BACKEND_PORT}"
echo "  Frontend:         http://localhost:${FRONTEND_PORT}"
echo "  MongoDB tunnel:   localhost:${MONGO_TUNNEL_PORT}"
echo ""
