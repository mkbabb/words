#!/bin/bash

# Start backend and frontend in parallel
echo "Starting floridify development servers..."

# Get current directory
ROOT_DIR=$(pwd)

# Start backend with UV
echo "Starting backend with UV..."
if command -v uv &> /dev/null; then
    cd "$ROOT_DIR/backend" && uv run scripts/run_api.py &
    BACKEND_PID=$!
else
    echo "Error: UV not found. Please install UV or add it to your PATH."
    exit 1
fi

# Start frontend  
cd "$ROOT_DIR/frontend" && npm run dev &
FRONTEND_PID=$!

# Function to kill both processes
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}

# Set up trap to catch Ctrl+C
trap cleanup INT

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID