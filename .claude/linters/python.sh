#!/bin/bash
# Python linting - concise output

# === Configuration ===
FILE_EXTENSIONS="py|pyi"  # Python file extensions
MAX_ERRORS=5              # Max errors per file to display

# === Path Discovery ===
# Find Python project root with pyproject.toml
PYTHON_DIR=""
if [ -f "backend/pyproject.toml" ]; then
    PYTHON_DIR="backend"
elif [ -f "pyproject.toml" ]; then
    PYTHON_DIR="."
fi

# === Main Function ===
lint_python() {
    local files=("$@")
    local has_output=false
    
    # Early exit if no Python project found
    [ -z "$PYTHON_DIR" ] && return 0
    
    for file in "${files[@]}"; do
        # File filtering
        [[ ! "$file" =~ \.($FILE_EXTENSIONS)$ ]] && continue
        [ ! -f "$file" ] && continue
        
        # Get relative path from Python dir
        local rel_file="${file#$PYTHON_DIR/}"
        [ "$file" = "$rel_file" ] && rel_file="../$file"  # If not in PYTHON_DIR, use parent path
        
        # Ruff autofix (silent)
        (cd "$PYTHON_DIR" && uv run ruff check --fix "$rel_file" &>/dev/null)
        
        # MyPy error detection
        local errors=$(cd "$PYTHON_DIR" && uv run mypy "$rel_file" 2>&1 | grep -E "error:" | head -$MAX_ERRORS)
        
        # Output formatting
        if [ -n "$errors" ]; then
            [ "$has_output" = true ] && echo ""
            echo "Python ($file):"
            echo "$errors"
            has_output=true
        fi
    done
}