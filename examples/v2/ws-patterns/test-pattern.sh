#!/bin/bash
# Test WebSocket patterns

PATTERN=${1:-"01-subscribe-simple"}

echo "Testing pattern: $PATTERN"
echo "================================"

# Start dummy service
echo "Starting dummy WebSocket service..."
cd dummy-service && docker compose -p thesis up -d
cd ..

sleep 3

# Generate FDSL code
echo "Generating FDSL code for $PATTERN..."
../../../venv_WIN/Scripts/fdsl generate ${PATTERN}.fdsl --out generated-${PATTERN}

if [ $? -eq 0 ]; then
    echo "✓ Generation successful!"
    echo ""
    echo "To test:"
    echo "1. cd generated-${PATTERN}"
    echo "2. docker compose -p thesis up"
    echo "3. Connect WebSocket client to test endpoints"
else
    echo "✗ Generation failed!"
    exit 1
fi
