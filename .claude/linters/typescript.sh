#!/bin/bash
# TypeScript linting - concise output

# === Configuration ===
FILE_EXTENSIONS="ts|tsx|js|jsx|vue"  # TypeScript/JavaScript file extensions
MAX_ERRORS=5                          # Max errors per file to display

# === Path Discovery ===
# Find TypeScript project root with tsconfig.json
TS_DIR=""
if [ -f "frontend/tsconfig.json" ]; then
    TS_DIR="frontend"
elif [ -f "tsconfig.json" ]; then
    TS_DIR="."
fi

# === Main Function ===
lint_typescript() {
    local files=("$@")
    local has_output=false
    
    # Early exit if no TypeScript project found
    [ -z "$TS_DIR" ] && return 0
    
    for file in "${files[@]}"; do
        # File filtering
        [[ ! "$file" =~ \.($FILE_EXTENSIONS)$ ]] && continue
        [ ! -f "$file" ] && continue
        
        # Get relative path from TS dir
        local rel_file="${file#$TS_DIR/}"
        [ "$file" = "$rel_file" ] && rel_file="../$file"  # If not in TS_DIR, use parent path
        
        # TypeScript error detection using vue-tsc
        local errors=$(cd "$TS_DIR" && npx vue-tsc --noEmit "$rel_file" 2>&1 | grep -E "error TS" | head -$MAX_ERRORS)
        
        # Output formatting
        if [ -n "$errors" ]; then
            [ "$has_output" = true ] && echo ""
            echo "TypeScript ($file):"
            echo "$errors"
            has_output=true
        fi
    done
}