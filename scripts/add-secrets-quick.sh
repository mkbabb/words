#!/bin/bash

# Quick script to add GitHub secrets
# Edit the values below before running

# Configuration - EDIT THESE VALUES
AWS_ACCESS_KEY_ID="your-access-key-here"
AWS_SECRET_ACCESS_KEY="your-secret-key-here"
EC2_HOST="44.216.140.209"
DOMAIN="words.babb.dev"
SSH_KEY_PATH="~/.ssh/id_rsa"  # Path to your EC2 private key

# Don't edit below this line
set -e

echo "Adding GitHub secrets for words repository..."

# Expand tilde in path
SSH_KEY_PATH="${SSH_KEY_PATH/#\~/$HOME}"

# Check if SSH key exists
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "Error: SSH key not found at $SSH_KEY_PATH"
    exit 1
fi

# Add secrets
echo "$AWS_ACCESS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID --repo mkbabb/words
echo "$AWS_SECRET_ACCESS_KEY" | gh secret set AWS_SECRET_ACCESS_KEY --repo mkbabb/words
echo "$EC2_HOST" | gh secret set EC2_HOST --repo mkbabb/words
echo "$DOMAIN" | gh secret set DOMAIN --repo mkbabb/words
cat "$SSH_KEY_PATH" | gh secret set EC2_SSH_KEY --repo mkbabb/words

echo "✅ All secrets added successfully!"

# List secrets
gh secret list --repo mkbabb/words