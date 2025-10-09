#!/usr/bin/env bash

# Get absolute path to project root (parent of scripts/)
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
EXAMPLES_DIR="$BASE_DIR/../examples"

echo "[INFO] Starting validation of all demo_*.fdsl files..."
echo

# Find all demo_*.fdsl files (recursively)
mapfile -t FILES < <(find "$EXAMPLES_DIR" -type f -name "demo_*.fdsl" ! -name "*_DEPRECATED*")

TOTAL=${#FILES[@]}
PASSED=0
FAILED=0

for f in "${FILES[@]}"; do
    echo "──────────────────────────────────────────────"
    echo "[VALIDATING] $f"
    if fdsl validate "$f"; then
        printf "[\033[32mPASS\x1b[0m] %s\n" "$f"
        ((PASSED++))
    else
        printf "[\x1b[31mFAIL\x1b[0m] %s\n" "$f"
        ((FAILED++))
    fi
    echo
done

echo "──────────────────────────────────────────────"
echo "[SUMMARY] Total: $TOTAL | Passed: $PASSED | Failed: $FAILED"
if ((FAILED > 0)); then
    exit 1
fi