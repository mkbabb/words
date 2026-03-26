#!/bin/bash
# Start or reuse an SSH tunnel for MongoDB access.
# Selects a free local port automatically to avoid collisions with other apps.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
    eval "$(
        python3 - "$ROOT_DIR/.env" <<'PY'
from pathlib import Path
import shlex
import sys

for raw_line in Path(sys.argv[1]).read_text().splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    print(f"export {key}={shlex.quote(value)}")
PY
    )"
fi

DEPLOY_HOST="${DEPLOY_HOST:-mbabb.fridayinstitute.net}"
DEPLOY_PORT="${DEPLOY_PORT:-1022}"
DEPLOY_USER="${DEPLOY_USER:-mbabb}"
REMOTE_PORT="${REMOTE_MONGO_PORT:-27017}"
PREFERRED_PORT="${MONGO_TUNNEL_PORT:-37117}"
MAX_PORT="${MONGO_TUNNEL_MAX_PORT:-37217}"

PRINT_PORT_ONLY=false
QUIET=false

while [ $# -gt 0 ]; do
    case "$1" in
        --print-port)
            PRINT_PORT_ONLY=true
            QUIET=true
            ;;
        --quiet)
            QUIET=true
            ;;
        --port)
            shift
            PREFERRED_PORT="${1:?missing value for --port}"
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
    shift
done

log() {
    if [ "$QUIET" != true ]; then
        echo "$@" >&2
    fi
}

listener_pid() {
    local port="$1"
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

is_port_free() {
    local port="$1"
    [ -z "$(listener_pid "$port")" ]
}

is_ssh_listener() {
    local port="$1"
    local pid
    pid="$(listener_pid "$port")"
    [ -n "$pid" ] && ps -p "$pid" -o command= | grep -qE '(^|/)ssh( |$)'
}

extract_forward_port() {
    local pid="$1"
    ps -p "$pid" -o command= | sed -n "s/.*-L \([0-9][0-9]*\):localhost:${REMOTE_PORT}.*/\1/p"
}

find_existing_tunnel_port() {
    local pid port
    while read -r pid _command; do
        [ -n "$pid" ] || continue
        port="$(extract_forward_port "$pid")"
        [ -n "$port" ] || continue
        if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
            echo "$port"
            return 0
        fi
    done < <(ps ax -o pid= -o command= | grep -E '(^|[[:space:]])ssh([[:space:]]|$)' | grep "localhost:${REMOTE_PORT}" || true)
    return 1
}

select_tunnel_port() {
    local existing candidate
    existing="$(find_existing_tunnel_port || true)"
    if [ -n "$existing" ]; then
        echo "$existing"
        return 0
    fi

    candidate="$PREFERRED_PORT"
    while [ "$candidate" -le "$MAX_PORT" ]; do
        if is_port_free "$candidate"; then
            echo "$candidate"
            return 0
        fi
        if is_ssh_listener "$candidate"; then
            echo "$candidate"
            return 0
        fi
        candidate=$((candidate + 1))
    done

    echo "Could not find a free SSH tunnel port in range ${PREFERRED_PORT}-${MAX_PORT}" >&2
    exit 1
}

LOCAL_PORT="$(select_tunnel_port)"

if ! is_port_free "$LOCAL_PORT" && ! is_ssh_listener "$LOCAL_PORT"; then
    echo "Selected tunnel port ${LOCAL_PORT} is occupied by a non-SSH process" >&2
    exit 1
fi

if is_ssh_listener "$LOCAL_PORT"; then
    log "Reusing SSH tunnel on localhost:${LOCAL_PORT}"
else
    log "Starting SSH tunnel to MongoDB on ${DEPLOY_HOST}"
    log "Local port: ${LOCAL_PORT} -> Remote: localhost:${REMOTE_PORT}"

    ssh -N -f \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -o TCPKeepAlive=yes \
        -o ConnectTimeout=10 \
        -L "${LOCAL_PORT}:localhost:${REMOTE_PORT}" \
        -p "${DEPLOY_PORT}" \
        "${DEPLOY_USER}@${DEPLOY_HOST}"

    sleep 1

    if ! is_ssh_listener "$LOCAL_PORT"; then
        echo "Failed to start SSH tunnel on localhost:${LOCAL_PORT}" >&2
        exit 1
    fi
fi

if [ "$PRINT_PORT_ONLY" = true ]; then
    echo "$LOCAL_PORT"
else
    log "MongoDB accessible at localhost:${LOCAL_PORT}"
fi
