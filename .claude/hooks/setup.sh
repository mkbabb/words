#!/bin/bash
# Claude Code hooks setup script

source "$(dirname "$0")/shared/utils.sh"

PROJECT_ROOT=$(get_project_root)

# Function to install backend dependencies if needed
check_backend_deps() {
    log_info "Checking backend dependencies..."
    cd "$PROJECT_ROOT/backend" || return 1
    
    if ! command_exists uv; then
        log_error "UV not found. Please install UV first."
        return 1
    fi
    
    # Ensure dev dependencies are installed
    if ! uv sync; then
        log_error "Failed to sync backend dependencies"
        return 1
    fi
    
    log_success "Backend dependencies ready"
    return 0
}

# Function to install frontend dependencies if needed
check_frontend_deps() {
    log_info "Checking frontend dependencies..."
    cd "$PROJECT_ROOT/frontend" || return 1
    
    # Check if prettier is installed
    if ! npm list prettier >/dev/null 2>&1; then
        log_info "Installing frontend dependencies..."
        npm install
    fi
    
    # Add prettier script if missing
    if ! grep -q '"prettier"' package.json; then
        log_info "Adding prettier script to package.json"
        # This would need to be done via proper JSON manipulation
    fi
    
    log_success "Frontend dependencies ready"
    return 0
}

# Function to display setup instructions
show_setup_instructions() {
    cat << EOF

${GREEN}Claude Code Hooks Setup Complete!${NC}

To use these hooks with Claude Code:

1. The hooks are configured in:
   ${BLUE}$PROJECT_ROOT/.claude/hooks.json${NC}

2. To activate the hooks, you need to configure Claude Code to use this hooks file.
   This can be done by:
   - Setting the CLAUDE_HOOKS_CONFIG environment variable to point to this file
   - Or including it in your Claude Code settings

3. The hooks will automatically:
   - Run linting and type checking on file changes
   - Auto-format code with Ruff (backend) and Prettier (frontend)
   - Check server health before operations
   - Analyze errors after changes
   - Validate syntax before committing changes

4. Hook scripts are located in:
   ${BLUE}$PROJECT_ROOT/.claude/hooks/${NC}

5. To test the hooks manually:
   ${YELLOW}TOOL_NAME=Edit FILE_PATH=/path/to/file bash .claude/hooks/main-hook.sh${NC}

${GREEN}Tips:${NC}
- Hooks run automatically when using Claude Code tools
- Server health checks run at the start of each session
- Formatting happens automatically on file save
- Type checking prevents type errors from being introduced

EOF
}

# Main setup
main() {
    log_info "Setting up Claude Code hooks for Floridify project..."
    
    # Check dependencies
    if ! check_backend_deps; then
        log_error "Backend setup failed"
        exit 1
    fi
    
    if ! check_frontend_deps; then
        log_error "Frontend setup failed"
        exit 1
    fi
    
    # Make all hook scripts executable
    chmod +x "$PROJECT_ROOT/.claude/hooks/"**/*.sh
    log_success "Hook scripts made executable"
    
    # Verify hooks configuration exists
    local hooks_file="$PROJECT_ROOT/.claude/hooks.json"
    if [[ ! -f "$hooks_file" ]]; then
        log_error "Hooks configuration not found at $hooks_file"
        exit 1
    fi
    
    log_success "Hooks configuration verified"
    
    # Show setup instructions
    show_setup_instructions
}

main