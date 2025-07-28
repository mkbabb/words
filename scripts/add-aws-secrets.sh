#!/bin/bash

# Script to add only the missing AWS secrets

echo "Adding AWS credentials to GitHub secrets..."
echo ""
echo "You'll need your AWS Access Key ID and Secret Access Key"
echo "These should have EC2 permissions to manage security groups"
echo ""

# AWS Access Key ID
echo -n "Enter AWS_ACCESS_KEY_ID: "
read -r AWS_ACCESS_KEY_ID
echo "$AWS_ACCESS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID --repo mkbabb/words

# AWS Secret Access Key
echo -n "Enter AWS_SECRET_ACCESS_KEY: "
read -rs AWS_SECRET_ACCESS_KEY
echo
echo "$AWS_SECRET_ACCESS_KEY" | gh secret set AWS_SECRET_ACCESS_KEY --repo mkbabb/words

echo ""
echo "✅ AWS secrets added successfully!"
echo ""
echo "Current secrets:"
gh secret list --repo mkbabb/words