#!/bin/bash
# Frontend linting and type checking hook

source "$(dirname "$0")/../shared/utils.sh"

PROJECT_ROOT=$(get_project_root)
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Function to run frontend checks
run_frontend_checks() {
    local file_path="$1"
    local errors_found=0
    
    # Skip if not a frontend file
    if [[ ! "$file_path" =~ \.(ts|tsx|vue|js|jsx)$ ]]; then
        return 0
    fi
    
    # Skip if not in frontend directory
    if [[ ! "$file_path" =~ $FRONTEND_DIR ]]; then
        return 0
    fi
    
    cd "$FRONTEND_DIR" || return 1
    
    # Run Prettier check
    log_info "Checking Prettier formatting"
    if ! npx prettier --check "$file_path" 2>&1; then
        log_warning "File needs formatting: $file_path"
        # Auto-format the file
        log_info "Auto-formatting with Prettier"
        npx prettier --write "$file_path" >&2
    fi
    
    # Run TypeScript check on Vue/TS files
    if [[ "$file_path" =~ \.(ts|tsx|vue)$ ]]; then
        log_info "Running TypeScript check"
        # Use vue-tsc for type checking
        if ! npm run --silent type-check 2>&1 | grep -E "(error|Error)" | grep -q "$file_path"; then
            log_success "No TypeScript errors in $file_path"
        else
            log_warning "TypeScript errors found in $file_path"
            errors_found=1
        fi
    fi
    
    return $errors_found
}

# Function to run full frontend validation
run_full_frontend_validation() {
    cd "$FRONTEND_DIR" || return 1
    local errors_found=0
    
    # Run type check
    log_info "Running full TypeScript check"
    if ! npm run --silent type-check 2>&1; then
        log_error "TypeScript errors found"
        errors_found=1
    fi
    
    # Check if build would succeed
    log_info "Checking if frontend builds"
    if ! npm run --silent build -- --mode development 2>&1; then
        log_error "Frontend build failed"
        errors_found=1
    fi
    
    return $errors_found
}

# Main execution
main() {
    local file_path="${FILE_PATH:-}"
    local tool_name="${TOOL_NAME:-}"
    
    case "$tool_name" in
        "Write"|"Edit"|"MultiEdit")
            if [[ -n "$file_path" ]]; then
                run_frontend_checks "$file_path"
                # Don't block on warnings, only on critical errors
                json_success
            else
                json_success
            fi
            ;;
        *)
            json_success
            ;;
    esac
}

main