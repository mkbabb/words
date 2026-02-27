#!/bin/bash
# Daily MongoDB backup script
# Run via cron: 0 3 * * * /home/ubuntu/floridify/scripts/backup-mongodb.sh
#
# Setup on EC2:
#   chmod +x /home/ubuntu/floridify/scripts/backup-mongodb.sh
#   mkdir -p /home/ubuntu/backups
#   crontab -e  # Add the cron line above

set -e

BACKUP_DIR="/home/ubuntu/backups"
RETENTION_DAYS=14
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE_NAME="floridify-${TIMESTAMP}.archive"

# Read password from .env file if available
if [ -f /home/ubuntu/floridify/.env ]; then
    MONGO_PASSWORD=$(grep '^MONGO_PASSWORD=' /home/ubuntu/floridify/.env | cut -d'=' -f2-)
fi

if [ -z "$MONGO_PASSWORD" ]; then
    echo "Error: MONGO_PASSWORD not set. Set it in /home/ubuntu/floridify/.env"
    exit 1
fi

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting MongoDB backup..."

# Dump directly from the container
docker exec floridify-mongodb mongodump \
    -u admin \
    -p "$MONGO_PASSWORD" \
    --authenticationDatabase admin \
    --db floridify \
    --archive="/tmp/${ARCHIVE_NAME}" \
    --gzip

# Copy archive out of the container
docker cp "floridify-mongodb:/tmp/${ARCHIVE_NAME}" "${BACKUP_DIR}/${ARCHIVE_NAME}"

# Clean up inside container
docker exec floridify-mongodb rm -f "/tmp/${ARCHIVE_NAME}"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "floridify-*.archive" -mtime +${RETENTION_DAYS} -delete

# Report
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${ARCHIVE_NAME}" | cut -f1)
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "floridify-*.archive" | wc -l | tr -d ' ')
echo "[$(date)] Backup complete: ${ARCHIVE_NAME} (${BACKUP_SIZE})"
echo "[$(date)] Total backups: ${BACKUP_COUNT} (retention: ${RETENTION_DAYS} days)"
