#!/bin/bash

# Development server management for Floridify

set -e

RESTART_MODE=false
DOCKER_MODE=true
LOGS_MODE=false
BUILD_MODE=false
DOWN_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --restart)  RESTART_MODE=true; shift ;;
        --native)   DOCKER_MODE=false; shift ;;
        --logs)     LOGS_MODE=true; shift ;;
        --build)    BUILD_MODE=true; shift ;;
        --down)     DOWN_MODE=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--restart] [--native] [--logs] [--build] [--down]"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

ROOT_DIR=$(pwd)

# Find a free port starting from $1, incrementing up to $1+$2
find_free_port() {
    local port="$1"
    local max_tries="${2:-10}"
    local end=$((port + max_tries))
    while [ "$port" -lt "$end" ]; do
        if ! lsof -ti "tcp:$port" -sTCP:LISTEN >/dev/null 2>&1; then
            echo "$port"
            return 0
        fi
        port=$((port + 1))
    done
    echo "Error: no free port in range $1-$((end - 1))" >&2
    return 1
}

start_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker is not running"
        exit 1
    fi

    if [ "$DOWN_MODE" = true ]; then
        docker compose down
        exit 0
    fi

    echo "Using hosted remote MongoDB at mbabb.friday.institute"

    # Resolve free ports
    local backend_port
    local frontend_port
    backend_port=$(find_free_port "${BACKEND_PORT:-8000}") || exit 1
    frontend_port=$(find_free_port "${FRONTEND_PORT:-3000}") || exit 1

    export BACKEND_PORT="$backend_port"
    export FRONTEND_PORT="$frontend_port"

    if [ "$BUILD_MODE" = true ]; then
        docker compose build
    fi

    if [ "$RESTART_MODE" = true ]; then
        docker compose restart
    else
        docker compose up -d
    fi

    echo ""
    echo "  Backend:  http://localhost:$backend_port"
    echo "  Frontend: http://localhost:$frontend_port"
    echo "  MongoDB:  mbabb.friday.institute:27017 (remote)"
    echo ""

    if [ "$LOGS_MODE" = true ]; then
        docker compose logs -f
    fi
}

start_native() {
    if [ ! -f "$ROOT_DIR/.env" ] && [ -f "$ROOT_DIR/.env.example" ]; then
        cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
        echo "Created .env from .env.example"
    fi

    local backend_port
    local frontend_port
    backend_port=$(find_free_port 8000) || exit 1
    frontend_port=$(find_free_port 3000) || exit 1

    # Start backend
    if ! command -v uv &>/dev/null; then
        echo "Error: uv not found"
        exit 1
    fi
    (cd ./backend && unset VIRTUAL_ENV && BACKEND_PORT="$backend_port" uv run ./scripts/run_api.py) &
    BACKEND_PID=$!

    # Start frontend
    (cd ./frontend && VITE_PORT="$frontend_port" npm run dev -- --port "$frontend_port") &
    FRONTEND_PID=$!

    cleanup() {
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
        exit
    }
    trap cleanup INT

    echo ""
    echo "  Backend:  http://localhost:$backend_port (pid $BACKEND_PID)"
    echo "  Frontend: http://localhost:$frontend_port (pid $FRONTEND_PID)"
    echo "  Ctrl+C to stop"
    echo ""

    wait $BACKEND_PID $FRONTEND_PID
}

if [ "$DOCKER_MODE" = true ]; then
    start_docker
else
    start_native
fi
