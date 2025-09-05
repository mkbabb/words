#!/bin/bash
# Claude stop hook - inject context and run linters

set -e
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

MAX_OUTPUT_LINES=20  # Maximum lines of linting output to show

# Source linters
source .claude/linters/python.sh
source .claude/linters/typescript.sh

# Get changed files
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null || echo "")
[ -z "$CHANGED_FILES" ] && exit 0

# Convert to array
IFS=$'\n' read -d '' -r -a FILES <<< "$CHANGED_FILES" || true

# Run linters and capture output
LINT_OUTPUT=""
PY_OUTPUT=$(lint_python "${FILES[@]}" 2>&1 || true)
TS_OUTPUT=$(lint_typescript "${FILES[@]}" 2>&1 || true)

[ -n "$PY_OUTPUT" ] && LINT_OUTPUT="$PY_OUTPUT"
[ -n "$TS_OUTPUT" ] && [ -n "$LINT_OUTPUT" ] && LINT_OUTPUT+="\n\n$TS_OUTPUT" || LINT_OUTPUT="$TS_OUTPUT"

# Output context
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat .claude/admonish.md

if [ -n "$LINT_OUTPUT" ]; then
    echo -e "\n## Linting Issues\n"
    echo -e "$LINT_OUTPUT" | head -$MAX_OUTPUT_LINES
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"