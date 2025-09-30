#!/bin/bash
# Comprehensive CLI/API isomorphism test script

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASSED=0
FAILED=0

# Function to extract JSON from CLI output and normalize
extract_cli_json() {
    local output="$1"
    echo "$output" | python3 <<'EOF'
import sys, json
text = sys.stdin.read()
start = text.find('{')
end = text.rfind('}')
if start == -1 or end == -1:
    print('{}')
    sys.exit(0)
json_str = text[start:end+1]
try:
    d = json.loads(json_str)
    # Remove timestamp and version for comparison
    d.pop('timestamp', None)
    d.pop('version', None)
    print(json.dumps(d, sort_keys=True))
except:
    print('{}')
EOF
}

# Function to normalize API JSON
normalize_api_json() {
    local json_text="$1"
    echo "$json_text" | python3 <<'EOF'
import sys, json
try:
    d = json.load(sys.stdin)
    d.pop('timestamp', None)
    d.pop('version', None)
    print(json.dumps(d, sort_keys=True))
except:
    print('{}')
EOF
}

# Test function
test_isomorphism() {
    local test_name="$1"
    local cli_cmd="$2"
    local api_url="$3"

    echo -n "Testing: $test_name... "

    # Get CLI output
    cli_output=$(eval "$cli_cmd" 2>/dev/null)
    cli_json=$(extract_cli_json "$cli_output")

    # Get API output
    api_output=$(curl -s "$api_url")
    api_json=$(normalize_api_json "$api_output")

    # Compare
    if [ "$cli_json" == "$api_json" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "  CLI: $(echo "$cli_json" | head -c 80)..."
        echo "  API: $(echo "$api_json" | head -c 80)..."
        ((FAILED++))
        return 1
    fi
}

echo "=== CLI/API Isomorphism Test Suite ==="
echo ""

# Test 1: Fuzzy search
test_isomorphism \
    "Search - fuzzy mode" \
    "floridify search word 'test' --mode fuzzy --min-score 0.7 --json" \
    "http://localhost:8000/api/v1/search?q=test&mode=fuzzy&min_score=0.7"

# Test 2: Exact search
test_isomorphism \
    "Search - exact mode" \
    "floridify search word 'test' --mode exact --json" \
    "http://localhost:8000/api/v1/search?q=test&mode=exact"

# Test 3: Smart search
test_isomorphism \
    "Search - smart mode" \
    "floridify search word 'test' --mode smart --json" \
    "http://localhost:8000/api/v1/search?q=test&mode=smart"

# Test 4: Semantic search
test_isomorphism \
    "Search - semantic mode" \
    "floridify search word 'test' --mode semantic --json" \
    "http://localhost:8000/api/v1/search?q=test&mode=semantic"

# Test 5: Max results
test_isomorphism \
    "Search - max results" \
    "floridify search word 'test' --max-results 5 --json" \
    "http://localhost:8000/api/v1/search?q=test&max_results=5"

# Test 6: Min score
test_isomorphism \
    "Search - min score 0.5" \
    "floridify search word 'test' --min-score 0.5 --json" \
    "http://localhost:8000/api/v1/search?q=test&min_score=0.5"

# Test 7: No results
test_isomorphism \
    "Search - no results" \
    "floridify search word 'xyzabc123' --json" \
    "http://localhost:8000/api/v1/search?q=xyzabc123"

echo ""
echo "=== Results ==="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
