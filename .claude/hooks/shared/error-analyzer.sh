#!/bin/bash
# Error analyzer hook - checks for server errors after file changes

source "$(dirname "$0")/../shared/utils.sh"

PROJECT_ROOT=$(get_project_root)
TEMP_DIR="${TMPDIR:-/tmp}"
ERROR_LOG="$TEMP_DIR/claude-code-errors.log"

# Function to capture recent server output
capture_server_errors() {
    local duration="${1:-3}" # seconds to wait
    local start_time=$(date +%s)
    
    > "$ERROR_LOG" # Clear previous errors
    
    # Monitor backend logs if available
    if pgrep -f "uvicorn|fastapi" >/dev/null 2>&1; then
        log_info "Monitoring backend server for errors..."
        # Capture any output from the backend process
        timeout "$duration" bash -c "
            while read -r line; do
                echo \"\$line\" | grep -iE '(error|exception|traceback|failed|warning)' >> '$ERROR_LOG'
            done < <(lsof -p \$(pgrep -f 'uvicorn|fastapi' | head -1) 2>&1 | grep -E '(PIPE|log)' | tail -1)
        " 2>/dev/null &
    fi
    
    # Monitor frontend console if browser is available
    if command_exists mcp__browsermcp__browser_get_console_logs; then
        log_info "Checking browser console for errors..."
        # This would need to be called through Claude Code's tool system
    fi
    
    # Wait for monitoring to complete
    sleep "$duration"
    
    # Analyze collected errors
    if [[ -s "$ERROR_LOG" ]]; then
        local error_count=$(wc -l < "$ERROR_LOG")
        log_warning "Found $error_count errors/warnings after changes"
        cat "$ERROR_LOG" | head -10 >&2
        return 1
    else
        log_success "No errors detected after changes"
        return 0
    fi
}

# Function to check for syntax errors in changed files
check_syntax_errors() {
    local file_path="$1"
    
    if [[ "$file_path" =~ \.py$ ]]; then
        # Python syntax check
        if ! python -m py_compile "$file_path" 2>&1; then
            log_error "Python syntax error in $file_path"
            return 1
        fi
    elif [[ "$file_path" =~ \.(js|jsx)$ ]]; then
        # JavaScript syntax check using Node
        if ! node -c "$file_path" 2>&1; then
            log_error "JavaScript syntax error in $file_path"
            return 1
        fi
    elif [[ "$file_path" =~ \.(ts|tsx|vue)$ ]]; then
        # TypeScript files need transpilation, skip syntax check
        # Type checking is handled by vue-tsc in the frontend hook
        log_info "Skipping syntax check for TypeScript file (handled by type checker)"
        return 0
    fi
    
    return 0
}

# Main execution
main() {
    local file_path="${FILE_PATH:-}"
    local tool_name="${TOOL_NAME:-}"
    
    case "$tool_name" in
        "Write"|"Edit"|"MultiEdit")
            if [[ -n "$file_path" ]]; then
                # Quick syntax check first
                if ! check_syntax_errors "$file_path"; then
                    json_block "Syntax error detected in $file_path"
                    return
                fi
                
                # Monitor for runtime errors (non-blocking)
                capture_server_errors 2 &
            fi
            ;;
    esac
    
    json_success
}

main