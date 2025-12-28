#!/bin/bash
# =============================================================================
# Test a single WebSocket pattern
# Usage: bash test-one-pattern.sh <pattern-name>
# Example: bash test-one-pattern.sh 01-subscribe-simple
# =============================================================================

set -e

# Configuration
PATTERN=${1:-"01-subscribe-simple"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../../.."

# Find wscat
if command -v wscat &> /dev/null; then
    WSCAT="wscat"
else
    echo "Error: wscat not found. Install with: npm install -g wscat"
    exit 1
fi

echo "========================================================================="
echo "Testing Pattern: $PATTERN"
echo "========================================================================="

# Step 1: Generate code
echo "[1/5] Generating code..."
cd "$SCRIPT_DIR"
make gen EXAMPLE="$PATTERN" OUTPUT="generated-$PATTERN"

# Step 2: Start generated FDSL service first (creates Docker network)
echo "[2/5] Starting generated FDSL service..."
cd "$SCRIPT_DIR/generated-$PATTERN"
docker compose -p thesis up -d
sleep 10

# Step 3: Start dummy WebSocket service
echo "[3/5] Starting dummy WebSocket service..."
cd "$SCRIPT_DIR/dummy-service"
docker compose -p thesis up -d
sleep 10

# Step 4: Test with wscat
echo "[4/5] Testing with wscat..."
echo ""
echo "Services are running!"
echo ""
echo "Dummy service: http://localhost:9200/health"
echo "FDSL API: http://localhost:8000/docs"
echo ""
echo "Manual WebSocket testing:"
echo "  wscat -c ws://localhost:8000/ws/<entity-name>"
echo ""
echo "Example for $PATTERN:"

case $PATTERN in
    "01-subscribe-simple")
        echo "  wscat -c ws://localhost:8000/ws/messagefromexternal"
        ;;
    "02-subscribe-transformed")
        echo "  wscat -c ws://localhost:8000/ws/processedmessage"
        ;;
    "03-publish-simple")
        echo "  echo '{\"command\":\"test\",\"value\":123}' | wscat -c ws://localhost:8000/ws/commandtoexternal"
        ;;
    "04-publish-transformed")
        echo "  echo '{\"action\":\"test\",\"value\":5}' | wscat -c ws://localhost:8000/ws/usercommand"
        ;;
    "05-bidirectional-simple")
        echo "  wscat -c ws://localhost:8000/ws/chatmessage"
        echo "  (Then send: {\"text\":\"hello\",\"user\":\"tester\"})"
        ;;
    "06-bidirectional-separate")
        echo "  Subscribe: wscat -c ws://localhost:8000/ws/processedtelemetry"
        echo "  Publish: echo '{\"action\":\"test\",\"value\":25}' | wscat -c ws://localhost:8000/ws/devicecommand"
        ;;
esac

echo ""
echo "[5/5] Press Ctrl+C to stop and cleanup, or test manually above"
echo ""

# Wait for user interrupt
trap "echo ''; echo 'Cleaning up...'; cd '$SCRIPT_DIR'; bash '$ROOT_DIR/scripts/docker_cleanup.sh'; rm -rf generated-*; echo 'Done!'; exit 0" INT TERM

# Keep script running
wait
