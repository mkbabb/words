# GitHub Actions Setup Guide

## Required Secrets

The following secrets must be configured in your GitHub repository settings:

1. **AWS_ACCESS_KEY_ID**: AWS access key with EC2 permissions
2. **AWS_SECRET_ACCESS_KEY**: AWS secret access key
3. **EC2_HOST**: The public IP address of your EC2 instance
4. **EC2_SSH_KEY**: Your private SSH key for accessing the EC2 instance (full content, including header/footer)
5. **DOMAIN**: Your domain name (e.g., words.babb.dev)

## How It Works

The GitHub Actions workflow automatically handles security group updates:

1. Gets the runner's public IP address
2. Temporarily adds this IP to the EC2 security group
3. SSHs into the server and runs the deploy script
4. Removes the IP from the security group when done

This approach ensures secure access without permanently opening your security group.

## AWS IAM Permissions

The AWS user associated with the access keys needs the following EC2 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress"
      ],
      "Resource": "*"
    }
  ]
}
```

## Prerequisites

1. **Auth Config on Server**: The `auth/config.toml` file must already exist on the server at `~/floridify/auth/config.toml`
2. **Git Repository**: The server must have the git repository cloned at `~/floridify/`
3. **Deploy Script**: The deploy script must be executable on the server

## Troubleshooting

### Missing AWS Credentials

If you see AWS credential errors, ensure you've added:
- AWS_ACCESS_KEY_ID secret
- AWS_SECRET_ACCESS_KEY secret

### SSH Connection Failed

If SSH fails after adding the IP to security group:
1. Verify EC2_HOST secret contains the correct public IP
2. Check EC2 instance is running
3. Ensure the SSH key is properly formatted in secrets

### SSH Key Format

The EC2_SSH_KEY secret should contain the complete private key:
```
-----BEGIN RSA PRIVATE KEY-----
[key content]
-----END RSA PRIVATE KEY-----
```

## Manual Deployment

If GitHub Actions deployment fails, deploy manually from your local machine:

```bash
./scripts/deploy
```