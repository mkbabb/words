#!/usr/bin/env bash
# Start floridify dev environment. Tears down on Ctrl-C / exit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ── Load .env if present ──────────────────────────────────
[[ -f "$ROOT/.env" ]] && set -o allexport && source "$ROOT/.env" && set +o allexport

# ── Config ────────────────────────────────────────────────
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

# ── Parse arguments ──────────────────────────────────────
MODE="dev"
ACTION=""
for arg in "$@"; do
    case "$arg" in
        --prod)   MODE="prod" ;;
        --down)   ACTION="down" ;;
        --logs)   ACTION="logs" ;;
        --build)  ACTION="build" ;;
    esac
done

# ── Quick actions ─────────────────────────────────────────
case "$ACTION" in
    down)   docker compose down; exit 0 ;;
    logs)   docker compose logs -f; exit 0 ;;
esac

# ── Pick ports ────────────────────────────────────────────
BACKEND_PORT=$(find_free_port "${BACKEND_PORT:-$BACKEND_PORT_DEFAULT}")
FRONTEND_PORT=$(find_free_port "${FRONTEND_PORT:-$FRONTEND_PORT_DEFAULT}")

export BACKEND_PORT FRONTEND_PORT
export BACKEND_CORS_ORIGINS="${BACKEND_CORS_ORIGINS:-[\"http://localhost:${FRONTEND_PORT}\",\"http://localhost:5173\"]}"

# ── Mode-specific config ─────────────────────────────────
# --prod only affects the FRONTEND (nginx-served production build).
# Backend and search always use development target (hot-reload, NLTK data).
if [[ "$MODE" == "prod" ]]; then
    export BUILD_TARGET="development"
    export FRONTEND_BUILD_TARGET="production"
    # Production frontend: nginx on port 80 inside the container
    export FRONTEND_INTERNAL_PORT=80
else
    export BUILD_TARGET="${BUILD_TARGET:-development}"
    export FRONTEND_BUILD_TARGET="${BUILD_TARGET:-development}"
    # Development frontend: vite listens on FRONTEND_PORT
    export FRONTEND_INTERNAL_PORT="${FRONTEND_PORT}"
fi

# ── Teardown ──────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Shutting down..."
    docker compose down 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ── Sync local packages if present ────────────────────────
GLASS_UI_SRC="$ROOT/../glass-ui"
GLASS_UI_DST="$ROOT/frontend/glass-ui"
if [ -d "$GLASS_UI_SRC" ]; then
    rsync -a --delete \
        --exclude node_modules --exclude dist --exclude .git \
        "$GLASS_UI_SRC/" "$GLASS_UI_DST/"
fi

LATEX_PAPER_SRC="$ROOT/../latex-paper"
LATEX_PAPER_DST="$ROOT/frontend/latex-paper"
if [ -d "$LATEX_PAPER_SRC" ]; then
    rsync -a --delete \
        --exclude node_modules --exclude dist --exclude .git \
        "$LATEX_PAPER_SRC/" "$LATEX_PAPER_DST/"
fi

# ── Build if requested ────────────────────────────────────
if [[ "$ACTION" == "build" ]]; then
    docker compose build backend search frontend
fi

# ── Start services ────────────────────────────────────────
# backend + search + frontend. Search is always needed — backend
# delegates /api/v1/search to the search service container.
docker compose up -d backend search frontend

cat <<EOF

──────────────────────────────────────
  Floridify Dev Environment ($MODE)
──────────────────────────────────────
  Backend  → http://localhost:$BACKEND_PORT
  Search   → http://search:8000 (internal)
  Frontend → http://localhost:$FRONTEND_PORT
  MongoDB  → remote (MONGODB_URL)
──────────────────────────────────────
  Ctrl-C to tear down
──────────────────────────────────────

EOF

docker compose logs -f
