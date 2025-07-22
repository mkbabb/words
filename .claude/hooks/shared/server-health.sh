#!/bin/bash
# Server health check hook

source "$(dirname "$0")/../shared/utils.sh"

PROJECT_ROOT=$(get_project_root)

# Function to check backend server health
check_backend_health() {
    if port_in_use 8000; then
        # Try to hit the health endpoint
        if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
            log_success "Backend server is healthy"
            return 0
        else
            log_warning "Backend server is running but not responding to health check"
            return 1
        fi
    else
        log_error "Backend server is not running on port 8000"
        return 2
    fi
}

# Function to check frontend server health
check_frontend_health() {
    if port_in_use 3000; then
        # Try to hit the frontend
        if curl -s -f http://localhost:3000 >/dev/null 2>&1; then
            log_success "Frontend server is healthy"
            return 0
        else
            log_warning "Frontend server is running but not responding"
            return 1
        fi
    else
        log_error "Frontend server is not running on port 3000"
        return 2
    fi
}

# Function to check for server errors in logs
check_server_logs() {
    local log_file="$1"
    local server_name="$2"
    
    if [[ -f "$log_file" ]]; then
        # Check for recent errors (last 100 lines)
        local error_count=$(tail -n 100 "$log_file" 2>/dev/null | grep -iE "(error|exception|traceback|failed)" | wc -l)
        if [[ $error_count -gt 0 ]]; then
            log_warning "$server_name has $error_count recent errors in logs"
            return 1
        fi
    fi
    return 0
}

# Main execution
main() {
    local tool_name="${TOOL_NAME:-}"
    local backend_healthy=true
    local frontend_healthy=true
    
    # Check server health on certain operations
    case "$tool_name" in
        "Bash"|"Write"|"Edit"|"MultiEdit")
            log_info "Checking server health..."
            
            if ! check_backend_health; then
                backend_healthy=false
            fi
            
            if ! check_frontend_health; then
                frontend_healthy=false
            fi
            
            # If servers are expected to be running but aren't, warn
            if [[ "$backend_healthy" == "false" ]] || [[ "$frontend_healthy" == "false" ]]; then
                log_warning "Some servers are not healthy. Consider running ./dev.sh"
            fi
            ;;
    esac
    
    # Always continue, just log warnings
    json_success
}

main