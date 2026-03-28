#!/usr/bin/env bash
# Deploy floridify to production.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEPLOY_HOST="${DEPLOY_HOST:-mbabb.fridayinstitute.net}"
DEPLOY_PORT="${DEPLOY_PORT:-1022}"
DEPLOY_USER="${DEPLOY_USER:-mbabb}"
REMOTE_DIR="~/floridify"
GATEWAY_PORT=8110
DOMAIN="${DOMAIN:-mbabb.friday.institute}"

log()  { printf '\033[0;32m[%s]\033[0m %s\n' "$(date '+%H:%M:%S')" "$1"; }
err()  { printf '\033[0;31m[ERROR]\033[0m %s\n' "$1" >&2; }

# Verify local prerequisites
for required in "auth/config.toml" ".env.production"; do
    [[ -f "$ROOT/$required" ]] || { err "Missing: $required"; exit 1; }
done

# Push code
git push origin "$(git branch --show-current)"

# Sync secrets
log "Syncing secrets..."
scp -P "$DEPLOY_PORT" -r "$ROOT/auth" "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_DIR/"
scp -P "$DEPLOY_PORT" "$ROOT/.env.production" "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_DIR/.env"

# Deploy
log "Deploying..."
ssh -p "$DEPLOY_PORT" "$DEPLOY_USER@$DEPLOY_HOST" bash -s <<'REMOTE'
  set -euo pipefail
  cd ~/floridify
  PREV=$(git rev-parse HEAD)
  git fetch origin && git reset --hard origin/master

  docker compose -f docker-compose.yml -f docker-compose.prod.yml build
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

  for i in $(seq 1 12); do
    curl -sf "http://localhost:8110/health" >/dev/null 2>&1 && \
      { docker image prune -f >/dev/null 2>&1; echo "Deploy OK"; exit 0; }
    sleep 5
  done
  echo "FAILED — rolling back to $PREV"
  git reset --hard "$PREV"
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
  exit 1
REMOTE

log "Done: https://$DOMAIN/words/"
