#!/bin/bash
# Start SSH tunnel for MongoDB/DocumentDB access

# Configuration
BASTION_HOST="44.216.140.209"
DOCDB_HOST="docdb-2025-07-21-21-16-19.cluster-cuvowu48w9vs.us-east-1.docdb.amazonaws.com"
LOCAL_PORT=27018
REMOTE_PORT=27017

echo "Starting SSH tunnel to DocumentDB..."
echo "Local port: $LOCAL_PORT -> Remote: $DOCDB_HOST:$REMOTE_PORT"

# Check if tunnel is already running
if lsof -i :$LOCAL_PORT > /dev/null 2>&1; then
    echo "SSH tunnel already running on port $LOCAL_PORT"
    exit 0
fi

# Start SSH tunnel in background
ssh -N -L $LOCAL_PORT:$DOCDB_HOST:$REMOTE_PORT ubuntu@$BASTION_HOST &
SSH_PID=$!

# Wait a moment for tunnel to establish
sleep 2

# Check if tunnel started successfully
if lsof -i :$LOCAL_PORT > /dev/null 2>&1; then
    echo "SSH tunnel started successfully (PID: $SSH_PID)"
    echo "MongoDB accessible at localhost:$LOCAL_PORT"
else
    echo "Failed to start SSH tunnel"
    exit 1
fi