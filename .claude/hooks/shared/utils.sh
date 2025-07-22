#!/bin/bash
# Shared utilities for hooks

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if a process is running on a port
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Get project root directory
get_project_root() {
    echo "${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)}"
}

# Parse tool information from environment
get_tool_info() {
    echo "Tool: ${TOOL_NAME:-unknown}"
    echo "File: ${FILE_PATH:-none}"
    echo "Action: ${TOOL_ACTION:-none}"
}

# JSON response helpers
json_success() {
    echo '{"continue": true}'
}

json_block() {
    local reason="${1:-Operation blocked}"
    echo "{\"continue\": false, \"block\": true, \"decision_reason\": \"$reason\"}"
}

json_approve() {
    echo '{"approve": true}'
}

json_deny() {
    local reason="${1:-Operation denied}"
    echo "{\"approve\": false, \"decision_reason\": \"$reason\"}"
}