#!/bin/bash
# Start Floridify dev environment.
# Configuration lives in .env (ports, MongoDB URL, etc.)
# Usage: ./scripts/dev.sh [--build] [--down] [--logs] [--native]

set -e

case "${1:-}" in
    --down)   docker compose down; exit 0 ;;
    --logs)   docker compose logs -f; exit 0 ;;
    --build)  docker compose build && docker compose up -d ;;
    --native)
        cd backend  && unset VIRTUAL_ENV && uv run ./scripts/run_api.py &
        cd frontend && npm run dev &
        trap 'kill $(jobs -p) 2>/dev/null' INT
        wait
        ;;
    *)        docker compose up -d ;;
esac

# Show status
if [ "${1:-}" != "--native" ] && [ "${1:-}" != "--down" ] && [ "${1:-}" != "--logs" ]; then
    echo ""
    echo "  Backend:  http://localhost:${BACKEND_PORT:-8003}"
    echo "  Frontend: http://localhost:${FRONTEND_PORT:-3004}"
    echo ""
fi
