#!/bin/bash

# Deployment script for Floridify
# Deploys by SSHing to server, syncing secrets, and running Docker commands

set -e

# Configuration
DEPLOY_HOST="${DEPLOY_HOST:-mbabb.fridayinstitute.net}"
DEPLOY_PORT="${DEPLOY_PORT:-1022}"
DEPLOY_USER="${DEPLOY_USER:-mbabb}"
DOMAIN="${DOMAIN:-mbabb.friday.institute}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-mike@babb.dev}"

SSH_CMD="ssh -o StrictHostKeyChecking=no -p $DEPLOY_PORT"
SCP_CMD="scp -o StrictHostKeyChecking=no -P $DEPLOY_PORT"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Test SSH connection
test_ssh() {
    print_status "Testing SSH connection to $DEPLOY_HOST:$DEPLOY_PORT..."

    if $SSH_CMD -o ConnectTimeout=10 $DEPLOY_USER@$DEPLOY_HOST 'echo "SSH connection successful"' &>/dev/null; then
        print_status "SSH connection verified"
    else
        print_error "Cannot connect to server via SSH"
        print_info "Please check:"
        print_info "  - Your SSH key is configured"
        print_info "  - DEPLOY_HOST is correct: $DEPLOY_HOST"
        print_info "  - DEPLOY_PORT is correct: $DEPLOY_PORT"
        print_info "  - DEPLOY_USER is correct: $DEPLOY_USER"
        exit 1
    fi
}

# Sync secrets and configuration files
sync_secrets() {
    print_status "Syncing secrets and configuration files..."

    # Check if local auth directory exists
    if [ ! -d "./auth" ]; then
        print_error "Local auth directory not found. Please ensure ./auth exists with config.toml"
        exit 1
    fi

    # Check if local .env.production exists
    if [ ! -f "./.env.production" ]; then
        print_error "Local .env.production file not found. Please ensure .env.production exists"
        exit 1
    fi

    print_info "Syncing auth directory..."
    $SCP_CMD -r ./auth $DEPLOY_USER@$DEPLOY_HOST:~/floridify/

    print_info "Syncing .env.production file..."
    $SCP_CMD ./.env.production $DEPLOY_USER@$DEPLOY_HOST:~/floridify/.env

    print_status "Secrets and configuration synced successfully"
}

# Deploy on server
deploy_on_server() {
    print_status "Deploying on server..."

    $SSH_CMD $DEPLOY_USER@$DEPLOY_HOST << 'ENDSSH'
        set -e  # Exit on error

        # Check if floridify directory exists, if not clone it
        if [ ! -d ~/floridify ]; then
            echo "Cloning repository..."
            git clone https://github.com/mkbabb/words.git ~/floridify
        fi

        cd ~/floridify

        # Pull latest code
        echo "Pulling latest code..."
        git pull origin master

        # Verify that secrets were synced properly
        if [ ! -f ~/floridify/auth/config.toml ]; then
            echo "Error: auth/config.toml not found on server after sync"
            echo "Please check the sync_secrets step"
            exit 1
        fi

        if [ ! -f ~/floridify/.env ]; then
            echo "Error: .env file not found on server after sync"
            echo "Please check the sync_secrets step"
            exit 1
        fi

        echo "Configuration files verified"

        # Build and deploy with Docker Compose
        # Note: SSL is handled by the host's Apache reverse proxy, not Docker nginx.
        # Use --profile ssl only if no external reverse proxy is available.
        echo "Building and deploying with Docker Compose..."
        docker compose -f docker-compose.yml -f docker-compose.prod.yml build
        docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

        # Show container status
        echo ""
        echo "Container status:"
        docker compose ps

        echo ""
        echo "Deployment completed on server!"
ENDSSH

    print_status "Deployment completed"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."

    print_info "Waiting for services to be ready..."
    sleep 30

    # Check if the application responds
    print_info "Testing application endpoint..."
    response=$(curl -s -o /dev/null -w "%{http_code}" -L https://$DOMAIN/words/api/health || echo "000")

    if [ "$response" = "200" ]; then
        print_status "Application is healthy at https://$DOMAIN/words/"
    elif [ "$response" = "000" ]; then
        print_warning "Application is not responding yet."
        print_info "Check manually: https://$DOMAIN/words/"
    else
        print_warning "Application responded with HTTP $response"
        print_info "Check deployment logs on server"
    fi
}

# Main function
main() {
    print_status "Starting Floridify deployment to $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PORT"

    # Test SSH connection
    test_ssh

    # Sync secrets and configuration
    sync_secrets

    # Deploy on server
    deploy_on_server

    # Verify deployment
    verify_deployment

    print_status "Deployment completed successfully!"
    print_info "Frontend: https://$DOMAIN/words/"
    print_info "API: https://$DOMAIN/words/api"
    print_info "API Docs: https://$DOMAIN/words/api/docs"
}

# Help message
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Floridify Deployment Script"
    echo ""
    echo "Deploys to server by:"
    echo "  1. Testing SSH connection to the server"
    echo "  2. Syncing local auth/ directory and .env.production to server"
    echo "  3. Pulling latest code from GitHub"
    echo "  4. Building and running Docker containers with SSL profile"
    echo ""
    echo "Prerequisites:"
    echo "  - SSH access to deployment server (mbabb.fridayinstitute.net:1022)"
    echo "  - Local auth/ directory with config.toml"
    echo "  - Local .env.production file"
    echo "  - Docker and Docker Compose installed on server"
    echo ""
    echo "Environment Variables:"
    echo "  DEPLOY_HOST   - Server hostname (default: mbabb.fridayinstitute.net)"
    echo "  DEPLOY_PORT   - SSH port (default: 1022)"
    echo "  DEPLOY_USER   - SSH username (default: mbabb)"
    echo "  DOMAIN        - Domain name (default: mbabb.friday.institute)"
    echo "  CERTBOT_EMAIL - Email for SSL certificates (default: mike@babb.dev)"
    echo ""
    echo "Files synced to server:"
    echo "  ./auth/        -> ~/floridify/auth/"
    echo "  ./.env.production -> ~/floridify/.env"
    echo ""
    echo "Usage:"
    echo "  ./scripts/deploy"
    exit 0
fi

main "$@"
