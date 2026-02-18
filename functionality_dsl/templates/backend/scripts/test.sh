#!/usr/bin/env bash

# Run tests with coverage
# Usage: bash scripts/test.sh

set -e
set -x

# Run pytest with coverage
coverage run -m pytest tests/ "$@"

# Generate reports
coverage report
coverage html --title "FDSL Test Coverage"

echo ""
echo "Tests completed! View HTML coverage report at: htmlcov/index.html"
