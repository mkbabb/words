#!/bin/bash
# Backend linting and type checking hook

source "$(dirname "$0")/../shared/utils.sh"

PROJECT_ROOT=$(get_project_root)
BACKEND_DIR="$PROJECT_ROOT/backend"

# Function to run backend checks
run_backend_checks() {
    local file_path="$1"
    local errors_found=0
    
    # Skip if not a Python file
    if [[ ! "$file_path" =~ \.py$ ]]; then
        return 0
    fi
    
    # Skip if not in backend directory
    if [[ ! "$file_path" =~ $BACKEND_DIR ]]; then
        return 0
    fi
    
    cd "$BACKEND_DIR" || return 1
    
    # Run Ruff check
    log_info "Running Ruff check on $file_path"
    if ! uv run ruff check "$file_path" 2>&1; then
        log_warning "Ruff found issues in $file_path"
        errors_found=1
    fi
    
    # Run Ruff format check
    log_info "Checking Ruff formatting"
    if ! uv run ruff format --check "$file_path" 2>&1; then
        log_warning "File needs formatting: $file_path"
        # Auto-format the file
        log_info "Auto-formatting with Ruff"
        uv run ruff format "$file_path" >&2
    fi
    
    # Run MyPy type check
    log_info "Running MyPy type check"
    if ! uv run mypy "$file_path" 2>&1; then
        log_warning "MyPy found type errors in $file_path"
        errors_found=1
    fi
    
    return $errors_found
}

# Function to run full backend validation
run_full_backend_validation() {
    cd "$BACKEND_DIR" || return 1
    local errors_found=0
    
    # Run all tests
    log_info "Running backend tests"
    if ! uv run pytest --no-header -rN 2>&1; then
        log_error "Backend tests failed"
        errors_found=1
    fi
    
    # Check for syntax errors
    log_info "Checking Python syntax"
    if ! uv run python -m py_compile src/floridify/**/*.py 2>&1; then
        log_error "Python syntax errors found"
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
                run_backend_checks "$file_path"
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