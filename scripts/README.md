# Deployment Scripts

## Setup

Configure production deployment:

```bash
./scripts/setup
```

This script:
- Sets GitHub repository secrets (SSH key, domain, email)
- Copies `auth/config.toml` to EC2 instance
- Prepares for automated deployment

## Deploy

Manual production deployment:

```bash
./scripts/deploy
```

Or trigger via GitHub Actions by pushing to `main` branch.

## Prerequisites

- GitHub CLI authenticated (`gh auth login`)
- SSH access to EC2 instance
- Local config files: `auth/config.toml`, `.env.production`