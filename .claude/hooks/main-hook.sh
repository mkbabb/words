#!/bin/bash
# Main hook orchestrator

source "$(dirname "$0")/shared/utils.sh"

PROJECT_ROOT=$(get_project_root)
HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"

# Function to determine which hooks to run
determine_hooks() {
    local tool_name="$1"
    local file_path="$2"
    local event_type="$3"
    
    local hooks=()
    
    # Pre-tool hooks
    if [[ "$event_type" == "pre" ]]; then
        case "$tool_name" in
            "Write"|"Edit"|"MultiEdit")
                # Server health check before making changes
                hooks+=("shared/server-health.sh")
                ;;
        esac
    fi
    
    # Post-tool hooks
    if [[ "$event_type" == "post" ]]; then
        case "$tool_name" in
            "Write"|"Edit"|"MultiEdit")
                # Determine if backend or frontend file
                if [[ "$file_path" =~ /backend/ ]] && [[ "$file_path" =~ \.py$ ]]; then
                    hooks+=("backend/lint-and-check.sh")
                elif [[ "$file_path" =~ /frontend/ ]] && [[ "$file_path" =~ \.(ts|tsx|vue|js|jsx)$ ]]; then
                    hooks+=("frontend/lint-and-check.sh")
                fi
                # Always run error analyzer after changes
                hooks+=("shared/error-analyzer.sh")
                ;;
            "Bash")
                # Check server health after bash commands
                hooks+=("shared/server-health.sh")
                ;;
        esac
    fi
    
    echo "${hooks[@]}"
}

# Function to run a single hook
run_hook() {
    local hook_script="$1"
    local hook_path="$HOOKS_DIR/$hook_script"
    
    if [[ -f "$hook_path" ]]; then
        log_info "Running hook: $hook_script"
        bash "$hook_path"
        return $?
    else
        log_error "Hook not found: $hook_path"
        return 1
    fi
}

# Main execution
main() {
    local tool_name="${TOOL_NAME:-}"
    local file_path="${FILE_PATH:-}"
    local event_type="${HOOK_EVENT:-post}" # Default to post if not specified
    
    log_info "Hook triggered: event=$event_type, tool=$tool_name, file=$file_path"
    
    # Determine which hooks to run
    local hooks_to_run=($(determine_hooks "$tool_name" "$file_path" "$event_type"))
    
    if [[ ${#hooks_to_run[@]} -eq 0 ]]; then
        log_info "No hooks to run for this event"
        json_success
        return
    fi
    
    # Run each hook
    local final_result=0
    local last_output=""
    
    for hook in "${hooks_to_run[@]}"; do
        output=$(run_hook "$hook")
        local exit_code=$?
        
        if [[ $exit_code -ne 0 ]]; then
            final_result=$exit_code
        fi
        
        # Keep the last meaningful output
        if [[ -n "$output" ]] && [[ "$output" != '{"continue": true}' ]]; then
            last_output="$output"
        fi
    done
    
    # Return the last meaningful output or success
    if [[ -n "$last_output" ]]; then
        echo "$last_output"
    else
        json_success
    fi
}

main