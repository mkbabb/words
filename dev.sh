#!/bin/bash

# Start backend and frontend in parallel
echo "Starting floridify development servers..."

# Get current directory
ROOT_DIR=$(pwd)

# Function to find and kill processes by pattern
kill_processes_by_pattern() {
    local pattern="$1"
    local description="$2"

    local pids=$(pgrep -f "$pattern" | grep -v $$ | grep -v $PPID)
    if [ ! -z "$pids" ]; then
        echo "Killing existing $description processes: $pids"
        kill -9 $pids 2>/dev/null
        sleep 0.5
    fi
}

# Function to find processes using network ports
kill_processes_on_ports() {
    local port_pattern="$1"
    local description="$2"

    # Find all processes listening on ports matching the pattern
    local pids=$(lsof -i -P -n | grep LISTEN | grep -E "$port_pattern" | awk '{print $2}' | sort -u)
    if [ ! -z "$pids" ]; then
        echo "Killing $description processes on ports matching '$port_pattern': $pids"
        kill -9 $pids 2>/dev/null
        sleep 0.5
    fi
}

# Kill existing backend processes
echo "Checking for existing backend processes..."
# Look for Python processes running our backend script
kill_processes_by_pattern "python.*run_api\.py" "backend (run_api.py)"
kill_processes_by_pattern "uvicorn.*floridify" "backend (uvicorn)"
# Also check for any FastAPI/Uvicorn processes on typical backend ports
kill_processes_on_ports ":800[0-9]" "backend"
kill_processes_on_ports ":3[0-9]{3}" "backend API"

# Kill existing frontend processes
echo "Checking for existing frontend processes..."
# Look for Node/npm dev server processes
kill_processes_by_pattern "node.*vite" "frontend (vite)"
kill_processes_by_pattern "npm.*dev" "frontend (npm dev)"
kill_processes_by_pattern "node.*frontend" "frontend"
# Check for processes on typical frontend dev ports
kill_processes_on_ports ":517[0-9]" "frontend (vite)"
kill_processes_on_ports ":300[0-9]" "frontend (react)"
kill_processes_on_ports ":808[0-9]" "frontend dev server"

# Brief pause to ensure processes are fully terminated
sleep 1

# Start backend with UV
echo "Starting backend with UV..."
if command -v uv &>/dev/null; then
    cd ./backend
    # Clear any conflicting virtual environment
    unset VIRTUAL_ENV
    uv run ./scripts/run_api.py &
    BACKEND_PID=$!
    echo "Backend started with PID $BACKEND_PID"
    cd "$ROOT_DIR"
else
    echo "Error: UV not found. Please install UV or add it to your PATH."
    exit 1
fi

# Start frontend
cd ./frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend started with PID $FRONTEND_PID"

cd ..

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
