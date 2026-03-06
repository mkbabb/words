#!/bin/bash
# Deploy PWA features to production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Deploying PWA features to production...${NC}"

# Check if required environment variables are set
if [ -z "$VAPID_PUBLIC_KEY" ] || [ -z "$VAPID_PRIVATE_KEY" ]; then
    echo -e "${RED}Error: VAPID keys not set. Run 'npm run generate-vapid-keys' in notification-server directory${NC}"
    exit 1
fi

# Configuration
DEPLOY_HOST="${DEPLOY_HOST:-mbabb.friday.institute}"
DEPLOY_PORT="${DEPLOY_PORT:-1022}"
DEPLOY_USER="${DEPLOY_USER:-mbabb}"

SSH_CMD="ssh -p $DEPLOY_PORT"
SCP_CMD="scp -P $DEPLOY_PORT"
RSYNC_SSH="ssh -p $DEPLOY_PORT"

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Build notification server
echo -e "${YELLOW}Building notification server...${NC}"
cd notification-server
docker build -t floridify-notification-server:latest .
cd ..

# Update frontend with PWA support
echo -e "${YELLOW}Building frontend with PWA support...${NC}"
cd frontend

# Ensure VAPID public key is in frontend environment
echo "VITE_VAPID_PUBLIC_KEY=$VAPID_PUBLIC_KEY" >> .env.production.local

# Build frontend
npm run build
cd ..

# Create deployment package
echo -e "${YELLOW}Creating deployment package...${NC}"
mkdir -p deploy-temp/frontend
mkdir -p deploy-temp/notification-server

# Copy frontend build
cp -r frontend/dist/* deploy-temp/frontend/

# Copy notification server
cp notification-server/Dockerfile deploy-temp/notification-server/
cp notification-server/package*.json deploy-temp/notification-server/
cp -r notification-server/dist deploy-temp/notification-server/

# Copy docker-compose files
cp docker-compose.notification.yml deploy-temp/
cp docker-compose.prod.notification.yml deploy-temp/

# Deploy to server
if [ -n "$DEPLOY_HOST" ]; then
    echo -e "${YELLOW}Deploying to server...${NC}"

    # Ensure remote directories exist
    $SSH_CMD "$DEPLOY_USER@$DEPLOY_HOST" "mkdir -p /opt/floridify/notification-server"

    # Copy files
    rsync -avz --delete \
        -e "$RSYNC_SSH" \
        ./deploy-temp/frontend/ \
        "$DEPLOY_USER@$DEPLOY_HOST:/var/www/floridify/"

    rsync -avz \
        -e "$RSYNC_SSH" \
        ./deploy-temp/notification-server/ \
        "$DEPLOY_USER@$DEPLOY_HOST:/opt/floridify/notification-server/"

    rsync -avz \
        -e "$RSYNC_SSH" \
        ./deploy-temp/*.yml \
        "$DEPLOY_USER@$DEPLOY_HOST:/opt/floridify/"

    # Update Docker services on remote
    echo -e "${YELLOW}Updating Docker services...${NC}"
    $SSH_CMD "$DEPLOY_USER@$DEPLOY_HOST" << 'ENDSSH'
        cd /opt/floridify

        # Pull latest images
        docker-compose -f docker-compose.yml -f docker-compose.notification.yml pull

        # Update services
        docker-compose \
            -f docker-compose.yml \
            -f docker-compose.notification.yml \
            -f docker-compose.prod.yml \
            -f docker-compose.prod.notification.yml \
            up -d --no-deps notification-server

        # Update nginx configuration for PWA
        sudo tee /etc/nginx/sites-available/floridify-pwa > /dev/null << 'EOF'
location /service-worker.js {
    add_header Service-Worker-Allowed /;
    add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
    try_files $uri =404;
}

location /manifest.json {
    add_header Content-Type application/manifest+json;
    try_files $uri =404;
}

location ~ ^/(icons|screenshots)/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    try_files $uri =404;
}
EOF

        # Reload nginx
        sudo nginx -s reload

        # Check service health
        sleep 10
        curl -f http://localhost:3001/health || exit 1

        echo "PWA deployment complete!"
ENDSSH

    echo -e "${GREEN}PWA deployment complete!${NC}"
else
    echo -e "${YELLOW}DEPLOY_HOST not set. Skipping remote deployment.${NC}"
    echo "To deploy, set: DEPLOY_HOST, DEPLOY_PORT, and DEPLOY_USER environment variables"
fi

# Cleanup
rm -rf deploy-temp

echo -e "${GREEN}PWA features deployed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Test PWA installation on iOS and Android devices"
echo "2. Verify push notifications are working"
echo "3. Check service worker caching"
echo "4. Monitor notification server logs: docker logs -f floridify-notifications"
