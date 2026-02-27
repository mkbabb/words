#!/bin/bash
# Start SSH tunnel for MongoDB access on EC2

# Configuration
EC2_HOST="3.225.200.137"
LOCAL_PORT=27018
REMOTE_PORT=27017

echo "Starting SSH tunnel to MongoDB on EC2..."
echo "Local port: $LOCAL_PORT -> Remote: localhost:$REMOTE_PORT"

# Check if tunnel is already running
if lsof -i :$LOCAL_PORT > /dev/null 2>&1; then
    echo "SSH tunnel already running on port $LOCAL_PORT"
    exit 0
fi

# Start SSH tunnel in background
# MongoDB is bound to 127.0.0.1 on EC2, so we tunnel to localhost
ssh -N -L $LOCAL_PORT:localhost:$REMOTE_PORT ubuntu@$EC2_HOST &
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
