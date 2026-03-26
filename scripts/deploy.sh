#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# Floridify production deployment.
#
# Steps:
#   1. Verify SSH connectivity to the deploy host
#   2. Sync secrets (auth/ directory + .env.production) to the server
#   3. Pull latest code on the server
#   4. Build and start Docker containers in production mode
#   5. Health-check the live endpoint
#
# Prerequisites:
#   - SSH key access to DEPLOY_HOST
#   - Local auth/ directory with config.toml
#   - Local .env.production file
#   - Docker + Docker Compose on the server
#
# Usage:
#   ./scripts/deploy.sh             # Full deploy
#   ./scripts/deploy.sh --help      # Show help
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ─── Configuration ───────────────────────────────────────────────────
# All overridable via environment variables.

DEPLOY_HOST="${DEPLOY_HOST:-mbabb.fridayinstitute.net}"
DEPLOY_PORT="${DEPLOY_PORT:-1022}"
DEPLOY_USER="${DEPLOY_USER:-mbabb}"
DOMAIN="${DOMAIN:-mbabb.friday.institute}"
REMOTE_DIR="${REMOTE_DIR:-~/floridify}"
REPO_URL="${REPO_URL:-https://github.com/mkbabb/words.git}"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"
SSH_CMD="ssh $SSH_OPTS -p $DEPLOY_PORT"
SCP_CMD="scp $SSH_OPTS -P $DEPLOY_PORT"

# ─── Logging ─────────────────────────────────────────────────────────

log()  { printf '\033[0;32m[%s]\033[0m %s\n' "$(date '+%H:%M:%S')" "$1"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$1"; }
err()  { printf '\033[0;31m[ERROR]\033[0m %s\n' "$1" >&2; }

# ─── Help ────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
Floridify production deployment.

Syncs secrets, pulls code, builds Docker images, and starts services
on the remote server.

Environment variables (defaults shown):
  DEPLOY_HOST   $DEPLOY_HOST
  DEPLOY_PORT   $DEPLOY_PORT
  DEPLOY_USER   $DEPLOY_USER
  DOMAIN        $DOMAIN

Required local files:
  auth/config.toml     API keys + database config
  .env.production      Production environment variables

Usage:
  ./scripts/deploy.sh
EOF
    exit 0
fi

# ─── Preflight checks ───────────────────────────────────────────────

log "Deploying to ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PORT}"

# Verify local prerequisites exist
for required in "auth/config.toml" ".env.production"; do
    if [ ! -f "$ROOT_DIR/$required" ]; then
        err "Missing required file: $required"
        exit 1
    fi
done

# Verify SSH connectivity
log "Testing SSH connection..."
if ! $SSH_CMD "$DEPLOY_USER@$DEPLOY_HOST" 'true' 2>/dev/null; then
    err "Cannot connect via SSH to $DEPLOY_HOST:$DEPLOY_PORT"
    exit 1
fi
log "SSH connection verified"

# ─── Sync secrets ───────────────────────────────────────────────────

log "Syncing secrets to server..."
$SCP_CMD -r "$ROOT_DIR/auth" "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_DIR/"
$SCP_CMD "$ROOT_DIR/.env.production" "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_DIR/.env"
log "Secrets synced"

# ─── Deploy on server ───────────────────────────────────────────────

log "Building and deploying on server..."

$SSH_CMD "$DEPLOY_USER@$DEPLOY_HOST" << ENDSSH
    set -euo pipefail

    # Clone if first deploy, otherwise pull
    if [ ! -d "$REMOTE_DIR" ]; then
        git clone "$REPO_URL" "$REMOTE_DIR"
    fi
    cd "$REMOTE_DIR"
    git pull origin master

    # Verify secrets arrived
    [ -f auth/config.toml ] || { echo "auth/config.toml missing"; exit 1; }
    [ -f .env ]             || { echo ".env missing"; exit 1; }

    # Build and start
    docker compose -f docker-compose.yml -f docker-compose.prod.yml build
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    echo ""
    docker compose ps
ENDSSH

log "Containers deployed"

# ─── Health check ────────────────────────────────────────────────────

log "Waiting 20s for services to start..."
sleep 20

status=$(curl -s -o /dev/null -w "%{http_code}" -L "https://$DOMAIN/words/health" 2>/dev/null || echo "000")
if [ "$status" = "200" ]; then
    log "Health check passed (HTTP 200)"
elif [ "$status" = "000" ]; then
    warn "No response from https://$DOMAIN/words/health — check manually"
else
    warn "Health check returned HTTP $status"
fi

# ─── Done ────────────────────────────────────────────────────────────

log "Deployment complete"
echo ""
echo "  App:  https://$DOMAIN/words/"
echo "  API:  https://$DOMAIN/words/api"
echo "  Docs: https://$DOMAIN/words/api/docs"
echo ""
