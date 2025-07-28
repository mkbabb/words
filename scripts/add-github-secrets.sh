#!/bin/bash

# Script to add GitHub secrets for deployment
# Usage: ./add-github-secrets.sh

set -e

echo "Adding GitHub secrets for words repository..."

# Function to add a secret
add_secret() {
    local name=$1
    local value=$2
    echo "Adding secret: $name"
    echo "$value" | gh secret set "$name" --repo mkbabb/words
}

# AWS Credentials
echo "Enter AWS_ACCESS_KEY_ID:"
read -r AWS_ACCESS_KEY_ID
add_secret "AWS_ACCESS_KEY_ID" "$AWS_ACCESS_KEY_ID"

echo "Enter AWS_SECRET_ACCESS_KEY:"
read -rs AWS_SECRET_ACCESS_KEY
echo
add_secret "AWS_SECRET_ACCESS_KEY" "$AWS_SECRET_ACCESS_KEY"

# EC2 Configuration
echo "Enter EC2_HOST (e.g., 44.216.140.209):"
read -r EC2_HOST
add_secret "EC2_HOST" "$EC2_HOST"

echo "Enter your domain (e.g., words.babb.dev):"
read -r DOMAIN
add_secret "DOMAIN" "$DOMAIN"

# SSH Key
echo "Enter path to your EC2 SSH private key file (e.g., ~/.ssh/id_rsa):"
read -r SSH_KEY_PATH
SSH_KEY_PATH="${SSH_KEY_PATH/#\~/$HOME}"  # Expand tilde
if [ -f "$SSH_KEY_PATH" ]; then
    add_secret "EC2_SSH_KEY" "$(cat "$SSH_KEY_PATH")"
else
    echo "Error: SSH key file not found at $SSH_KEY_PATH"
    exit 1
fi

echo "✅ All secrets have been added successfully!"
echo ""
echo "To verify, run: gh secret list --repo mkbabb/words"