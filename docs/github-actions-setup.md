# GitHub Actions Setup Guide

## Required Secrets

The following secrets must be configured in your GitHub repository settings:

1. **EC2_HOST**: The public IP address of your EC2 instance
2. **EC2_SSH_KEY**: Your private SSH key for accessing the EC2 instance (full content, including header/footer)
3. **DOMAIN**: Your domain name (e.g., words.babb.dev)
4. **OPENAI_API_KEY**: Your OpenAI API key
5. **MONGODB_CONNECTION_STRING**: Your MongoDB connection string
6. **CERTBOT_EMAIL**: Email for SSL certificate generation
7. **OXFORD_APP_ID**: (Optional) Oxford Dictionary API app ID
8. **OXFORD_API_KEY**: (Optional) Oxford Dictionary API key
9. **DICTIONARY_COM_AUTH**: (Optional) Dictionary.com auth token

## EC2 Security Group Configuration

GitHub Actions uses dynamic IP ranges that change frequently. To allow deployments from GitHub Actions, you need to configure your EC2 security group:

### Option 1: Allow GitHub Actions IP Ranges (Recommended)

1. Get the current GitHub Actions IP ranges:
   ```bash
   curl -s https://api.github.com/meta | jq -r '.actions[]' | sort -u
   ```

2. Add these IP ranges to your EC2 security group for SSH (port 22)

3. Note: These IPs change periodically, so you may need to update them

### Option 2: Use AWS Systems Manager Session Manager

Instead of direct SSH, use AWS Systems Manager for secure access without opening port 22.

### Option 3: Temporary Security Group Update

Create a GitHub Action that:
1. Temporarily adds the runner's IP to the security group
2. Performs the deployment
3. Removes the IP from the security group

### Option 4: Self-Hosted Runner

Deploy a self-hosted GitHub Actions runner within your AWS VPC for direct access.

## Troubleshooting

### SSH Connection Timeout

If you see "Connection timed out" errors:

1. Verify EC2_HOST secret contains the correct public IP
2. Check EC2 instance is running and accessible
3. Verify security group allows SSH from GitHub Actions IPs
4. Ensure the SSH key is properly formatted in secrets

### SSH Key Format

The EC2_SSH_KEY secret should contain the complete private key:
```
-----BEGIN RSA PRIVATE KEY-----
[key content]
-----END RSA PRIVATE KEY-----
```

## Manual Deployment Alternative

If GitHub Actions deployment fails, you can deploy manually from your local machine:

```bash
./scripts/deploy
```

This uses your local SSH configuration and doesn't require special security group rules.